"""MuniCompras connector, ingest and dedupe against the municipal bulletin (WMU1).

Fixtures only, no network: the client takes an injectable ``http_get`` and the
ingest takes a list of parsed procedures.
"""

import json
from datetime import date
from pathlib import Path

import httpx
import pytest
import pytest_asyncio

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "muni_compras"


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _payload(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _paged_client(tmp_path, calls=None):
    """Client whose two pages come from the fixtures; page 2 repeats id 397."""
    from app.scrapers.muni_compras import MuniComprasClient

    def fake_get(url, params):
        assert url.endswith("/apifg/compra/compra")
        if calls is not None:
            calls.append(params["pagina"])
        return _Resp(_payload("compras_page1.json" if params["pagina"] == 1 else "compras_page2.json"))

    return MuniComprasClient(cache_dir=tmp_path, delay=0, http_get=fake_get)


# --------------------------------------------------------------------------- #
# Parsing and paging
# --------------------------------------------------------------------------- #


def test_parse_compra_keeps_what_the_portal_publishes():
    from app.scrapers.muni_compras import parse_compras

    compras = parse_compras(_payload("compras_page1.json"))
    assert [c.id for c in compras] == [397, 398]

    c = compras[0]
    assert (c.titulo, c.tipo_codigo, c.estado_codigo) == ("2026/099", "CONCURSO", "FINALIZADA")
    assert c.expediente == "102-025180/2026"  # trailing blanks cleaned
    assert c.presupuesto == 42706162.88
    assert c.fecha == date(2026, 10, 27)
    assert c.objeto.startswith("SERVICIO DE REPARACION EDILICIA")
    assert c.acta and c.acta["id_cdd"] == "98a1b1ee-14c0-4945-b1a7-7df29b36a7e9"


def test_monto_cero_o_ausente_no_es_monto():
    from app.scrapers.muni_compras import parse_compra

    base = {"id": 1, "titulo": "2026/9", "objeto": "x"}
    assert parse_compra({**base, "presupuesto": 0.0}).presupuesto is None
    assert parse_compra({**base, "presupuesto": None}).presupuesto is None
    assert parse_compra({**base, "presupuesto": "1234.5"}).presupuesto == 1234.5


def test_iter_compras_recorre_paginas_y_no_repite_ids(tmp_path):

    calls = []
    client = _paged_client(tmp_path, calls)
    ids = [c.id for c in client.iter_compras(date(2026, 1, 1), date(2026, 12, 31))]
    assert ids == [397, 398, 399]  # 397 appears on both pages, once here
    assert calls == [1, 2]
    assert client.requests == 2


def test_cache_evita_pegarle_dos_veces_a_la_api(tmp_path):
    from app.scrapers.muni_compras import MuniComprasClient

    primero = _paged_client(tmp_path)
    list(primero.iter_compras(date(2026, 1, 1), date(2026, 12, 31)))
    assert primero.requests == 2

    def boom(url, params):  # pragma: no cover - must not be called
        raise AssertionError("la segunda corrida no debe pedir la API")

    segundo = MuniComprasClient(cache_dir=tmp_path, delay=0, http_get=boom)
    ids = [c.id for c in segundo.iter_compras(date(2026, 1, 1), date(2026, 12, 31))]
    assert ids == [397, 398, 399]
    assert (segundo.requests, segundo.cache_hits) == (0, 2)


# --------------------------------------------------------------------------- #
# Ingest
# --------------------------------------------------------------------------- #


@pytest_asyncio.fixture
async def session():
    from app.db.models import Analisis, Base, Boletin
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        db.add(Boletin(id=1, filename="20260430_4_Secc.pdf", date="20260430", section="4",
                       status="completed", fuente="provincial"))
        db.add(Analisis(boletin_id=1, monto_numerico=1000.0, tipo_gasto="licitacion",
                        nivel="provincial"))
        await db.commit()
        yield db
    await engine.dispose()


@pytest.mark.asyncio
async def test_ingest_persiste_con_fuente_nivel_y_municipio(session, tmp_path):
    from app.services.muni_compras_ingest import ingest_compras

    client = _paged_client(tmp_path)
    stats = await ingest_compras(session, client, date(2026, 1, 1), date(2026, 12, 31))

    assert (stats.compras, stats.compras_nuevas) == (3, 3)
    assert stats.compras_con_monto == 3
    assert stats.compras_gasto == 3 and stats.monto_gasto == pytest.approx(42706162.88 + 184800000.0 + 24319905.66)
    assert stats.por_tipo == {"concurso_precios": 1, "licitacion": 1, "subasta_electronica": 1}
    assert stats.publicaciones == 2  # 2026-03-20 and 2026-10-27

    from app.db.models import Analisis, Boletin
    from sqlalchemy import select

    row = (await session.execute(
        select(Analisis).where(Analisis.numero_acto == "2026/099")
    )).scalar_one()
    assert (row.nivel, row.municipio, row.jurisdiccion_gasto) == ("municipal", "Córdoba", "municipal")
    # `objeto` sale de las mismas reglas que el resto del corpus: "servicio de
    # reparación edilicia" no está en la lista de servicios reconocidos, así que
    # queda en `otro` (brecha del clasificador, no del conector).
    assert (row.tipo_gasto, row.objeto, row.etapa_gasto) == ("concurso_precios", "otro", "llamado")
    assert row.is_gasto_publico is True
    assert row.datos_extra["fuente"] == "municipal_compras"
    assert row.datos_extra["compra_id"] == 397
    assert row.datos_extra["expediente"] == "102-025180/2026"
    assert row.datos_extra["adjudicacion_publica"] is False
    assert "token" in row.datos_extra["adjudicacion_nota"]

    boletin = (await session.execute(select(Boletin).where(Boletin.id == row.boletin_id))).scalar_one()
    assert (boletin.fuente, boletin.section, boletin.date) == ("municipal_compras", "portal_compras", "20261027")
    assert "Portal de Compras" in boletin.seccion_nombre


@pytest.mark.asyncio
async def test_ingest_es_idempotente_por_id_de_compra(session, tmp_path):
    from app.db.models import Analisis, Boletin
    from app.services.muni_compras_ingest import ingest_compras
    from sqlalchemy import func, select

    client = _paged_client(tmp_path)
    await ingest_compras(session, client, date(2026, 1, 1), date(2026, 12, 31))
    stats = await ingest_compras(session, client, date(2026, 1, 1), date(2026, 12, 31))

    assert (stats.compras, stats.compras_nuevas) == (3, 0)
    n = (await session.execute(
        select(func.count()).select_from(Analisis).join(Boletin).where(Boletin.fuente == "municipal_compras")
    )).scalar()
    assert n == 3
    nb = (await session.execute(
        select(func.count()).select_from(Boletin).where(Boletin.fuente == "municipal_compras")
    )).scalar()
    assert nb == 2


@pytest.mark.asyncio
async def test_compra_que_cambia_de_fecha_se_mueve_de_boletin(session, tmp_path):
    """A draft gets its publication date later; it must move, not duplicate."""
    from dataclasses import replace

    from app.db.models import Analisis, Boletin
    from app.scrapers.muni_compras import parse_compras
    from app.services.muni_compras_ingest import ingest_compras
    from sqlalchemy import func, select

    borrador = parse_compras(_payload("compras_page2.json"))[0]
    await ingest_compras(session, None, date(2026, 1, 1), date(2026, 12, 31), compras=[borrador])

    publicado = replace(borrador, fecha_publicacion=date(2026, 11, 4))
    await ingest_compras(session, None, date(2026, 1, 1), date(2026, 12, 31), compras=[publicado])

    n = (await session.execute(
        select(func.count()).select_from(Analisis).join(Boletin).where(Boletin.fuente == "municipal_compras")
    )).scalar()
    assert n == 1
    fechas = (await session.execute(
        select(Boletin.date).join(Analisis, Analisis.boletin_id == Boletin.id)
        .where(Boletin.fuente == "municipal_compras")
    )).scalars().all()
    assert fechas == ["20261104"]
    # El día que quedó sin compras no se cuenta como edición publicada.
    nb = (await session.execute(
        select(func.count()).select_from(Boletin).where(Boletin.fuente == "municipal_compras")
    )).scalar()
    assert nb == 1


# --------------------------------------------------------------------------- #
# Dedupe against the municipal bulletin
# --------------------------------------------------------------------------- #


async def _boletin_municipal(session, descripcion: str, fragmento: str, monto: float, aid: int, boletin_id: int):
    from app.db.models import Analisis, Boletin

    session.add(Boletin(id=boletin_id, filename=f"municipal_cordoba_{boletin_id}.pdf",
                        date="20260320", section="municipal", status="completed",
                        fuente="municipal_capital"))
    session.add(Analisis(id=aid, boletin_id=boletin_id, descripcion=descripcion, fragmento=fragmento,
                         monto_numerico=monto, tipo_gasto="licitacion", nivel="municipal",
                         municipio="Córdoba"))
    await session.commit()


@pytest.mark.asyncio
async def test_dedupe_por_expediente_entre_portal_y_boletin(session, tmp_path):
    from app.db.models import Analisis
    from app.services.muni_compras_ingest import ingest_compras
    from sqlalchemy import select

    await _boletin_municipal(
        session,
        descripcion="LLAMA A LICITACIÓN PÚBLICA N° 01/26, PARA LA CONTRATACIÓN DEL SERVICIO DE LIMPIEZA",
        fragmento="VISTO: El Expediente N° 025522/26 mediante el cual se gestiona la contratación",
        monto=184800000.0,
        aid=50,
        boletin_id=2,
    )
    stats = await ingest_compras(session, _paged_client(tmp_path), date(2026, 1, 1), date(2026, 12, 31))

    assert stats.duplicadas_boletin == 1
    assert stats.compras_gasto == 2
    assert stats.monto_gasto == pytest.approx(42706162.88 + 24319905.66)

    dup = (await session.execute(
        select(Analisis).where(Analisis.numero_acto == "2026/001")
    )).scalar_one()
    assert dup.is_duplicate_gasto == 1
    assert dup.datos_extra["dedupe"]["analisis_id"] == 50
    assert "expediente" in dup.datos_extra["dedupe"]["motivo"]

    # El acto del boletín es el que cuenta: sigue sin marcar.
    original = (await session.execute(select(Analisis).where(Analisis.id == 50))).scalar_one()
    assert original.is_duplicate_gasto in (0, None)


@pytest.mark.asyncio
async def test_dedupe_por_llamado_y_monto(session, tmp_path):
    """Mismo número de llamado y mismo monto: la misma compra, sin expediente en común."""
    from app.db.models import Analisis
    from app.scrapers.muni_compras import parse_compra
    from app.services.muni_compras_ingest import ingest_compras
    from sqlalchemy import select

    await _boletin_municipal(
        session,
        descripcion="Se aprueban los Pliegos y llámase a Licitación Pública N° 001/2026 para el alquiler de contenedores",
        fragmento="VISTO: el Expediente N°822-018605/2026 mediante el cual se tramita el llamado",
        monto=84421200.0,
        aid=51,
        boletin_id=3,
    )
    compra = parse_compra({
        "id": 500, "titulo": "2026/001", "objeto": "ALQUILER DE CONTENEDORES Y BAÑOS QUIMICOS",
        "tipo": {"tipo_compra": "LICITACION", "nombre": "LICITACIÓN PÚBLICA"},
        "estado": {"estado_compra": "ADJUDICADA", "nombre": "Adjudicada"},
        "expediente": "999-000001/2026",  # otro expediente: el match tiene que venir por el número
        "presupuesto": 84421200.0, "fecha_publicacion": "2026-07-28 09:00:00",
    })
    stats = await ingest_compras(session, None, date(2026, 1, 1), date(2026, 12, 31), compras=[compra])

    assert stats.duplicadas_boletin == 1
    row = (await session.execute(select(Analisis).where(Analisis.numero_acto == "2026/001"))).scalar_one()
    assert row.is_duplicate_gasto == 1
    assert "llamado" in row.datos_extra["dedupe"]["motivo"]


@pytest.mark.asyncio
async def test_mismo_llamado_con_otro_monto_no_es_duplicado(session, tmp_path):
    """El número de llamado solo no alcanza: sin el monto, no se descuenta nada."""
    from app.db.models import Analisis
    from app.scrapers.muni_compras import parse_compra
    from app.services.muni_compras_ingest import ingest_compras
    from sqlalchemy import select

    await _boletin_municipal(
        session,
        descripcion="Licitación Pública N° 001/2026 para el alquiler de contenedores",
        fragmento="VISTO: el Expediente N°822-018605/2026",
        monto=84421200.0,
        aid=52,
        boletin_id=4,
    )
    compra = parse_compra({
        "id": 501, "titulo": "2026/002", "objeto": "OTRA COSA",
        "tipo": {"tipo_compra": "LICITACION", "nombre": "LICITACIÓN PÚBLICA"},
        "expediente": "999-000002/2026", "presupuesto": 500.0,
        "fecha_publicacion": "2026-07-28 09:00:00",
    })
    stats = await ingest_compras(session, None, date(2026, 1, 1), date(2026, 12, 31), compras=[compra])

    assert stats.duplicadas_boletin == 0
    row = (await session.execute(select(Analisis).where(Analisis.numero_acto == "2026/002"))).scalar_one()
    assert row.is_duplicate_gasto == 0
    assert "dedupe" not in row.datos_extra


# --------------------------------------------------------------------------- #
# Cobertura / banner
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_cobertura_suma_el_portal_y_su_detalle(session, tmp_path):
    from app.api.v1.endpoints import gasto
    from app.db.session import get_db
    from app.services.muni_compras_ingest import ingest_compras
    from fastapi import FastAPI

    await ingest_compras(session, _paged_client(tmp_path), date(2026, 1, 1), date(2026, 12, 31))

    app = FastAPI()
    app.include_router(gasto.router, prefix="/gasto")

    async def _db():
        yield session

    app.dependency_overrides[get_db] = _db
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        body = (await c.get("/gasto/cobertura")).json()

    fuentes = {f["fuente"]: f for f in body["fuentes"]}
    portal = fuentes["municipal_compras"]
    assert portal["tipo"] == "portal"
    assert (portal["nivel"], portal["municipio"]) == ("municipal", "Córdoba")
    assert portal["portal"] == "https://compras.cordoba.gob.ar"
    assert (portal["ediciones"], portal["actos"], portal["actos_gasto"]) == (2, 3, 3)
    assert (portal["desde"], portal["hasta"]) == ("2026-03-20", "2026-10-27")
    assert "adjudicado" in portal["detalle"] and "no son públicos" in portal["detalle"]
    assert fuentes["provincial"]["tipo"] == "boletin" and fuentes["provincial"]["detalle"] is None
    assert "Córdoba" in body["municipios_cubiertos"]
    assert "sección 5" in body["nota"] and "compras directas" in body["nota"]

    # Las compras del portal se filtran y se listan como cualquier acto municipal.
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        listado = (await c.get("/gasto/detectado", params={"municipio": "Córdoba", "nivel": "municipal"})).json()
    assert listado["total"] == 3
    assert {i["tipo_gasto"] for i in listado["items"]} == {"concurso_precios", "licitacion", "subasta_electronica"}
    assert all(i["organismo"].startswith("Municipalidad de Córdoba") for i in listado["items"])


def test_claves_de_expediente_normalizan_las_dos_grafias():
    from app.scrapers.muni_compras import clave_expediente

    assert clave_expediente("102-025180/2026") == "25180/26"
    assert clave_expediente("025522/26") == "25522/26"
    assert clave_expediente("822-018605/2026") == "18605/26"
    assert clave_expediente(None) is None
    assert clave_expediente("sin numero") is None
