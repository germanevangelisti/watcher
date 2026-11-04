"""Cordoba municipal bulletin connector (pm-municipal-cobertura).

No network: the API responses and the act text are fixtures captured from
boletinmunicipal.cordoba.gob.ar (edition 4506, 2026-10-14), trimmed.
"""

import json
from datetime import date
from pathlib import Path

import pytest
from app.scrapers.pds_muni import (
    CordobaMunicipalClient,
    extract_monto,
    parse_dias,
    parse_ediciones,
)
from app.services.municipal_ingest import (
    build_analisis_fields,
    clave_republicacion,
    motivo_no_gasto_municipal,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "muni_cordoba"


def _json(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class _Resp:
    def __init__(self, payload=None, content=b""):
        self._payload, self.content = payload, content

    def json(self):
        return self._payload


def test_parse_dias():
    dias = parse_dias(_json("dias_publicacion.json"))
    assert dias == [date(2026, 10, 29), date(2026, 10, 30), date(2026, 11, 2)]


def test_parse_ediciones_segments_acts():
    [(edicion, actos)] = parse_ediciones(_json("boletin_fecha.json"))
    assert edicion.numero == 4506
    assert edicion.fecha == date(2026, 10, 14)
    assert edicion.pdf_url.startswith("https://static01.cordoba.gob.ar/boe/boletines/")
    assert [a.publicacion_id for a in actos] == [5247, 5248, 5288]
    lic = actos[-1]
    assert lic.tipo_acto == "resolucion"
    assert "LICITACIÓN PÚBLICA" in lic.asunto
    assert lic.pdf_url.endswith("pub_2026_00005288_vistaprevia.pdf")


@pytest.mark.parametrize(
    "text, expected",
    [
        ("suma de pesos ($84.421.200,00.-) ... asciende a ($84.421.200,00.-)", 84421200.0),
        ("presupuesto oficial ($184.800.000,00) ... ($184.800.000.00) seguro minimo ($1.000.000,00)", 184800000.0),
        ("Valor de la U.E.M. ($13.536)", 13536.0),
        ("sin montos", None),
        ("", None),
    ],
)
def test_extract_monto(text, expected):
    assert extract_monto(text) == expected


def test_extract_monto_from_real_act_text():
    text = (FIXTURES / "pub_5288.txt").read_text(encoding="utf-8")
    assert extract_monto(text) == 184800000.0


def test_build_analisis_fields_licitacion_is_municipal_gasto():
    [(_, actos)] = parse_ediciones(_json("boletin_fecha.json"))
    text = (FIXTURES / "pub_5288.txt").read_text(encoding="utf-8")
    fields = build_analisis_fields(actos[-1], text)
    assert fields["nivel"] == "municipal"
    assert fields["municipio"] == "Córdoba"
    assert fields["monto_numerico"] == 184800000.0
    assert fields["tipo_gasto"] == "licitacion"
    assert fields["datos_extra"]["publicacion_id"] == 5288


def test_build_analisis_fields_without_text_has_no_monto():
    [(_, actos)] = parse_ediciones(_json("boletin_fecha.json"))
    fields = build_analisis_fields(actos[0], "")
    assert fields["monto_numerico"] is None
    assert fields["fragmento"].startswith("FALLOS ABSOLUTORIOS")
    assert fields["nivel"] == "municipal"


def test_client_iterates_and_dedups_editions(tmp_path):
    calls = []

    def fake_get(url, params):
        calls.append((url, params))
        if url.endswith("/dias-publicacion"):
            return _Resp(_json("dias_publicacion.json"))
        return _Resp(_json("boletin_fecha.json"))  # same edition every day

    client = CordobaMunicipalClient(output_dir=tmp_path, delay=0, http_get=fake_get)
    eds = list(client.iter_ediciones(date(2026, 10, 1), date(2026, 10, 30)))
    # Nov 2 is outside the range; the repeated edition is yielded once.
    assert len(eds) == 1
    assert [p["fecha"] for _, p in calls[1:]] == ["2026-10-29", "2026-10-30"]
    # Server-side upper bound is exclusive: the request asks for one extra day.
    assert calls[0][1]["fechaHasta"] == "Sat Oct 31 2026"


def test_client_download_is_cached(tmp_path):
    hits = []

    def fake_get(url, params):
        hits.append(url)
        return _Resp(content=b"%PDF-1.4 fake")

    client = CordobaMunicipalClient(output_dir=tmp_path, delay=0, http_get=fake_get)
    dest = tmp_path / "a" / "x.pdf"
    client.download("https://static01.cordoba.gob.ar/x.pdf", dest)
    client.download("https://static01.cordoba.gob.ar/x.pdf", dest)
    assert dest.read_bytes() == b"%PDF-1.4 fake"
    assert len(hits) == 1


@pytest.mark.parametrize(
    "asunto, motivo",
    [
        ('Se dispone la emisi\u00f3n de la Serie LIII de Letras del Tesoro por un Valor Nominal de Pesos ($50.000.000.000).', "deuda"),
        ("Adecuaci\u00f3n tarifaria del Sistema de Transporte Urbano de Pasajeros.", "tarifa"),
        ("ESTABLECE EL COSTO DE LA INSCRIPCI\u00d3N PARA LA MARAT\u00d3N CIUDAD DE C\u00d3RDOBA.", "tarifa"),
        ("Nuevo valor de la Unidad Econ\u00f3mica Municipal (U.E.M).", "tarifa"),
        ("FALLOS ABSOLUTORIOS DEL TRIBUNAL DE CUENTAS MUNICIPAL.", "Tribunal de Cuentas"),
        ('LLAMA A LICITACI\u00d3N P\u00daBLICA N\u00b0 01/26, PARA LA CONTRATACI\u00d3N DEL "SERVICIO DE LIMPIEZA"', None),
    ],
)
def test_motivo_no_gasto_municipal(asunto, motivo):
    got = motivo_no_gasto_municipal(asunto)
    assert (got is None) if motivo is None else (motivo in got)


def test_letras_del_tesoro_is_not_gasto():
    [(_, actos)] = parse_ediciones(_json("boletin_fecha.json"))
    from dataclasses import replace

    letras = replace(actos[-1], asunto="Se dispone la emisi\u00f3n de Letras del Tesoro ($50.000.000.000).")
    fields = build_analisis_fields(letras, "Valor Nominal de Pesos ($50.000.000.000)")
    assert fields["monto_numerico"] == 50_000_000_000.0
    assert fields["tipo_gasto"] == "no_es_gasto"
    assert fields["is_gasto_publico"] is False
    assert "deuda" in fields["gasto_motivo"]


def test_clave_republicacion_ignores_punctuation_and_accents():
    a = clave_republicacion('LLAMA A LICITACI\u00d3N P\u00daBLICA N\u00b0 01/26, PARA LA CONTRATACI\u00d3N', 184800000.0)
    b = clave_republicacion('LLAMA A LICITACION PUBLICA N\u00b0 01/26 PARA LA CONTRATACION', 184800000.0)
    assert a == b
    assert clave_republicacion("x", None) is None
