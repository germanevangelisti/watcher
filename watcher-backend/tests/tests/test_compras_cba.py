"""Tests for the ComprasCba adapter, the Mercado Libre OAuth and their use in
the precio-mercado analysis. No network: the portal fetcher is a fake that
serves saved fixtures, and HTTP calls go through ``httpx.MockTransport``.

Run from watcher-backend/:
    .venv/Scripts/python.exe -m pytest tests/tests/test_compras_cba.py -v
"""

from datetime import date
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from app.services import compras_cba as cc
from app.services import precio_mercado_service as svc
from app.services.price_sources import (
    ComprasCbaReferenceSource,
    MercadoLibreAuth,
    MercadoLibreSource,
)

FIXTURES = Path(__file__).parent / "fixtures"
TH = svc.Thresholds(observable=0.30, alerta=1.00, min_references=3)

# Two rows as the portal renders them: a presencial process (object + budget,
# quantities only in the pliego) and an electronic one (renglones in the grid).
GRID = """
<table id="gv">
<tr class="Renglon">
  <td>1/2026</td><td>Licitaci&#243;n Presencial</td><td>199 - Policia De La Provincia</td>
  <td title="ADQUISICION DE RESMAS DE PAPEL Y LIBROS DE ACTAS CON DESTINO A LA DIVISION INTENDENCIA">ADQUISICION DE RESMAS...</td>
  <td>&nbsp;</td><td>13/05/2026 10:00:00</td><td>ADJUDICADA</td><td>NO</td><td>
  <input type="image" name="gv$ctl58$btnVerDetalles" id="gv_btnVerDetalles_56" />
  <table class="Grid" id="gv_btnItems_56_gv"><tr><th scope="col">Objeto de Contrat./Cotiz.</th><th scope="col">Presupuesto Oficial</th></tr>
  <tr><td>ADQUISICION DE RESMAS DE PAPEL Y LIBROS DE ACTAS</td><td>$ 186.031.008,0000</td></tr></table>
  </td>
</tr>
<tr class="RenglonAlternativo">
  <td>2026/000038.01</td><td>Subasta Electr&#243;nica Inversa</td><td>35 - Servicio Penitenciario</td>
  <td title="Adquisici&#243;n de COLCHONES DE ESPUMA DE POLIURETANO">Adquisici&#243;n de COLCHO...</td>
  <td>14/05/2026 08:00:00</td><td>14/05/2026 12:00:00</td><td>ADJUDICADA</td><td>NO</td><td>
  <input type="image" name="gv$ctl59$btnVerDetalles" id="gv_btnVerDetalles_57" />
  <table class="Grid" id="gv_btnItems_57_gv"><tr><th scope="col">Rengl&#243;n</th><th scope="col">Cantidad</th><th scope="col">Precio de Referencia</th><th scope="col">Presupuesto Oficial</th></tr>
  <tr><td>COLCHONES IGNIFUGOS</td><td align="right">4000</td><td align="right">$ 73.000,<small>0000<small/></td><td align="right">$ 292.000.000,<small>0000<small/></td></tr></table>
  </td>
</tr>
<tr class="Renglon">
  <td>2026/000096</td><td>Subasta Electr&#243;nica Inversa</td><td>228 - Secretar&#237;a General De Salud</td>
  <td title="Adquisici&#243;n de RESMAS DE HOJAS A4">Adquisici&#243;n de RESMAS...</td>
  <td>10/05/2026 08:00:00</td><td>10/05/2026 12:00:00</td><td>ADJUDICADA</td><td>NO</td><td>
  <table class="Grid" id="gv_btnItems_58_gv"><tr><th scope="col">Rengl&#243;n</th><th scope="col">Cantidad</th><th scope="col">Precio de Referencia</th><th scope="col">Presupuesto Oficial</th></tr>
  <tr><td>RESMA DE PAPEL A4</td><td align="right">4000</td><td align="right">$ 7.000,<small>0000<small/></td><td align="right">$ 28.000.000,<small>0000<small/></td></tr></table>
  </td>
</tr>
</table>
"""


class FakeFetcher:
    def __init__(self, grid=GRID, pliego=b"%PDF-fake", fail=False):
        self.grid, self.pliego_bytes, self.fail = grid, pliego, fail
        self.searches = 0
        self.pliegos = 0

    async def search(self, desde, hasta, finalizadas):
        self.searches += 1
        if self.fail:
            raise httpx.ConnectError("portal down")
        return self.grid if finalizadas else ""

    async def pliego(self, proceso, desde, hasta):
        self.pliegos += 1
        return "3. PROYECTO DE PLIEGO.pdf", self.pliego_bytes


@pytest.fixture(autouse=True)
def _pliego_text(monkeypatch):
    text = (FIXTURES / "pliego_resmas.txt").read_text("utf-8")
    monkeypatch.setattr(cc, "pdf_text", lambda content: text)


# ----------------------------------------------------------------- parsing


def test_parse_grid_rows_and_renglones():
    procesos = cc.parse_grid(GRID)
    assert [p.nro for p in procesos] == ["1/2026", "2026/000038.01", "2026/000096"]
    presencial, subasta = procesos[0], procesos[1]
    assert presencial.presupuesto_total == 186_031_008.0 and presencial.renglones == []
    assert presencial.row_control == "gv$ctl58"
    assert subasta.renglones[0].cantidad == 4000 and subasta.renglones[0].precio_referencia == 73_000.0


def test_parse_pliego_renglones():
    renglones = cc.parse_pliego_renglones((FIXTURES / "pliego_resmas.txt").read_text("utf-8"))
    assert [(r.numero, r.descripcion, r.cantidad) for r in renglones] == [
        (1, "Resmas de papel A4", 12000.0),
        (2, "Resmas de papel oficio", 1200.0),
        (3, "Libros de actas", 5880.0),
    ]


def test_parse_money_and_qty():
    assert cc.parse_money("$ 186.031.008,0000") == 186_031_008.0
    assert cc.parse_qty("12.000") == 12000.0 and cc.parse_qty("4000") == 4000.0


def test_match_by_amount_then_quantity_never_by_one_word():
    procesos = cc.parse_grid(GRID)
    assert cc.match_proceso(procesos, 186_031_008.0, "resmas").nro == "1/2026"
    assert cc.match_proceso(procesos, 400_000_000.0, "adquisición de cuatro mil (4.000) colchones", 4000).nro == "2026/000038.01"
    # Same quantity, unrelated object: the resmas process (4000) must not match colchones-like acts.
    assert cc.match_proceso(procesos, 1.0, "colchones", None) is None


# ----------------------------------------------------------------- source


@pytest.mark.asyncio
async def test_find_uses_pliego_when_grid_has_no_renglones():
    fetcher = FakeFetcher()
    match = await cc.ComprasCbaSource(fetcher).find(date(2026, 4, 30), 186_031_008.0, "RESMAS DE PAPEL Y LIBROS DE ACTAS")
    assert match.found and match.renglones_origen == "pliego"
    assert [r.cantidad for r in match.proceso.renglones] == [12000.0, 1200.0, 5880.0]
    assert fetcher.pliegos == 1


@pytest.mark.asyncio
async def test_find_degrades_when_portal_is_down():
    match = await cc.ComprasCbaSource(FakeFetcher(fail=True)).find(date(2026, 4, 30), 1.0, "x")
    assert match.found is False and "portal no disponible" in match.reason


# ----------------------------------------------------------------- analysis integration


@pytest_asyncio.fixture
async def session():
    from app.db.models import Base, Boletin, EjecucionPresupuestaria
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        db.add(Boletin(id=1, filename="b.pdf", date="20260430", section="1", status="completed"))
        db.add_all([
            EjecucionPresupuestaria(id=1, boletin_id=1, concepto="ADQUISICION DE RESMAS DE PAPEL Y LIBROS DE ACTAS",
                                    monto=186_031_008.0, tipo_operacion="licitacion", organismo="DESARROLLO SOCIAL",
                                    fecha_boletin=date(2026, 4, 30), is_duplicate=0),
            EjecucionPresupuestaria(id=2, boletin_id=1, concepto="Adquisición de colchones ignífugos",
                                    monto=292_000_000.0, tipo_operacion="licitacion", organismo="SERVICIO PENITENCIARIO",
                                    fecha_boletin=date(2026, 5, 20), is_duplicate=0),
        ])
        await db.commit()
        yield db
    await engine.dispose()


@pytest.mark.asyncio
async def test_multi_renglon_act_shows_quantities_without_inventing_a_unit_price(session):
    fetcher = FakeFetcher()
    result = await svc.analyze(session, 1, use_llm=False, external_sources=[], thresholds=TH,
                               compras=cc.ComprasCbaSource(fetcher))
    ext = result.extraccion
    assert len(ext["renglones"]) == 3 and ext["proceso"]["nro"] == "1/2026"
    assert ext["cantidad"] is None and result.precio_unitario is None
    assert "3 renglones" in result.comparacion["motivo"]
    assert any(f["fuente"] == "compras_cba" and f["disponible"] for f in result.fuentes)


@pytest.mark.asyncio
async def test_single_renglon_gives_quantity_and_cache_avoids_a_second_fetch(session):
    fetcher = FakeFetcher()
    source = cc.ComprasCbaSource(fetcher)
    result = await svc.analyze(session, 2, use_llm=False, external_sources=[], thresholds=TH, compras=source)
    assert result.extraccion["cantidad"] == 4000 and result.extraccion["fuente_cantidad"] == "compras_cba_grilla"
    assert result.precio_unitario == pytest.approx(73_000.0)
    searches = fetcher.searches
    await svc.analyze(session, 2, use_llm=False, external_sources=[], thresholds=TH, compras=source)
    assert fetcher.searches == searches  # served from fuente_externa_cache


@pytest.mark.asyncio
async def test_portal_outage_is_not_cached(session):
    down = FakeFetcher(fail=True)
    result = await svc.analyze(session, 2, use_llm=False, external_sources=[], thresholds=TH,
                               compras=cc.ComprasCbaSource(down))
    assert result.extraccion["cantidad"] is None
    assert any(f["fuente"] == "compras_cba" and not f["disponible"] for f in result.fuentes)
    up = FakeFetcher()
    result = await svc.analyze(session, 2, use_llm=False, external_sources=[], thresholds=TH,
                               compras=cc.ComprasCbaSource(up))
    assert result.extraccion["cantidad"] == 4000


@pytest.mark.asyncio
async def test_official_reference_prices_exclude_the_acts_own_process():
    procesos = cc.parse_grid(GRID)

    async def loader():
        return procesos

    res = await ComprasCbaReferenceSource(loader).search("resmas de papel")
    assert res.available and [r.process_id for r in res.references] == ["2026/000096"]
    ref = res.references[0]
    assert ref.kind == "oficial" and ref.unit_price == 7000.0 and ref.observed_on == "2026-05-10"


# ----------------------------------------------------------------- Mercado Libre OAuth


def _ml_env(monkeypatch, **env):
    for var in ("ML_ACCESS_TOKEN", "ML_CLIENT_ID", "ML_CLIENT_SECRET", "ML_REFRESH_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)


@pytest.mark.asyncio
async def test_ml_client_credentials_then_cached(monkeypatch, tmp_path):
    _ml_env(monkeypatch, ML_CLIENT_ID="id", ML_CLIENT_SECRET="secret")
    calls = []

    def handler(req):
        calls.append(req.content.decode())
        return httpx.Response(200, json={"access_token": "T1", "expires_in": 21600})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        auth = MercadoLibreAuth(cache_path=tmp_path / "t.json", client=client, clock=lambda: 1000.0)
        assert await auth.token() == "T1"
        assert await auth.token() == "T1"
    assert len(calls) == 1 and "grant_type=client_credentials" in calls[0]


@pytest.mark.asyncio
async def test_ml_refresh_token_rotates_and_is_persisted(monkeypatch, tmp_path):
    _ml_env(monkeypatch, ML_CLIENT_ID="id", ML_CLIENT_SECRET="secret", ML_REFRESH_TOKEN="R0")
    now = [1000.0]
    seen = []

    def handler(req):
        body = req.content.decode()
        seen.append(body)
        n = len(seen)
        return httpx.Response(200, json={"access_token": f"T{n}", "refresh_token": f"R{n}", "expires_in": 100})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        auth = MercadoLibreAuth(cache_path=tmp_path / "t.json", client=client, clock=lambda: now[0])
        assert await auth.token() == "T1"
        now[0] += 500  # expired
        assert await auth.token() == "T2"
    assert "refresh_token=R0" in seen[0] and "refresh_token=R1" in seen[1]
    assert '"R2"' in (tmp_path / "t.json").read_text()


@pytest.mark.asyncio
async def test_ml_search_retries_once_after_401(monkeypatch, tmp_path):
    _ml_env(monkeypatch, ML_CLIENT_ID="id", ML_CLIENT_SECRET="secret")
    tokens = iter(["OLD", "NEW"])

    def handler(req):
        if req.url.path == "/oauth/token":
            return httpx.Response(200, json={"access_token": next(tokens), "expires_in": 21600})
        if req.headers.get("authorization") == "Bearer OLD":
            return httpx.Response(401, json={})
        return httpx.Response(200, json={"results": [{"title": "Resma A4", "price": 9000, "permalink": "u"}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        auth = MercadoLibreAuth(cache_path=tmp_path / "t.json", client=client)
        res = await MercadoLibreSource(client=client, auth=auth).search("resma")
    assert res.available and res.references[0].unit_price == 9000


@pytest.mark.asyncio
async def test_ml_without_credentials_says_what_is_missing(monkeypatch, tmp_path):
    _ml_env(monkeypatch)
    transport = httpx.MockTransport(lambda req: httpx.Response(403, json={}))
    async with httpx.AsyncClient(transport=transport) as client:
        res = await MercadoLibreSource(client=client, auth=MercadoLibreAuth(cache_path=tmp_path / "t.json")).search("x")
    assert not res.available and "ML_CLIENT_ID" in res.reason


def test_amount_match_requires_a_related_object():
    procesos = cc.parse_grid(GRID)
    # Same amount as the resmas process, unrelated object (an upstream mis-parse).
    assert cc.match_proceso(procesos, 186_031_008.0, "Adquisición de uniformes", None) is None


@pytest.mark.asyncio
async def test_official_references_need_every_key_word():
    procesos = cc.parse_grid(GRID)

    async def loader():
        return procesos

    res = await ComprasCbaReferenceSource(loader).search("resmas de cartulina")
    assert res.references == []
