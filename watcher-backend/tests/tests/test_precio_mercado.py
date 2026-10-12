"""Tests for epic:precio-mercado (detection, extraction, comparison, API).

Run from watcher-backend/:
    .venv/Scripts/python.exe -m pytest tests/tests/test_precio_mercado.py -v

No network: external sources are injected fakes and the LLM is a stub.
"""

from datetime import date

import httpx
import pytest
import pytest_asyncio
from app.services import precio_mercado_service as svc
from app.services.price_sources import MercadoLibreSource, PriceReference, SourceResult

TH = svc.Thresholds(observable=0.30, alerta=1.00, min_references=3)


@pytest.fixture(autouse=True)
def _no_compras_cba(monkeypatch):
    """These tests cover the core flow; ComprasCba has its own test module."""
    monkeypatch.setenv("PRECIO_MERCADO_COMPRAS_CBA", "0")


@pytest_asyncio.fixture
async def session():
    from app.db.models import Base
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        await _seed(db)
        yield db
    await engine.dispose()


async def _seed(db):
    from app.db.models import Analisis, Boletin, EjecucionPresupuestaria

    db.add(Boletin(id=1, filename="20260430_1_Secc.pdf", date="20260430", section="1",
                   status="completed", source_url="https://boletin.example/20260430"))
    db.add(Analisis(id=1, boletin_id=1, fragmento="la suma total estimada de pesos 186.031.008"))
    rows = [
        # The resmas case: no quantity anywhere in the text.
        dict(id=1, concepto="ADQUISICION DE RESMAS DE PAPEL Y LIBROS DE ACTAS CON DESTINO A LA DIVISION INTENDENCIA",
             monto=186_031_008.0, tipo_operacion="licitacion", organismo="MINISTERIO DE DESARROLLO SOCIAL",
             fecha_boletin=date(2026, 4, 30), analisis_id=1),
        # Acts with a quantity: unit price 10.000 each.
        dict(id=2, concepto="Adquisición de 1.000 resmas de papel A4", monto=10_000_000.0,
             tipo_operacion="licitacion", organismo="A", fecha_boletin=date(2026, 3, 1)),
        dict(id=3, concepto="Compra de 500 resmas de papel oficio", monto=5_500_000.0,
             tipo_operacion="compra", organismo="B", fecha_boletin=date(2026, 2, 1)),
        dict(id=4, concepto="Adquisición de 200 resmas de papel", monto=1_800_000.0,
             tipo_operacion="licitacion", organismo="C", fecha_boletin=date(2026, 1, 15)),
        dict(id=5, concepto="Adquisición de 100 resmas de papel", monto=3_000_000.0,
             tipo_operacion="licitacion", organismo="D", fecha_boletin=date(2026, 5, 2)),
        # Republication of act 5 on another day under another organismo: not a reference.
        dict(id=9, concepto="Adquisición de 100 resmas de papel", monto=3_000_000.0,
             tipo_operacion="licitacion", organismo="G", fecha_boletin=date(2026, 5, 4)),
        # Not observable: works, subsidies, duplicates.
        dict(id=6, concepto="Obra de construcción de escuela", monto=9e8, tipo_operacion="licitacion",
             organismo="E", fecha_boletin=date(2026, 4, 1)),
        dict(id=7, concepto="Subsidio a cooperativa", monto=1e6, tipo_operacion="subsidio",
             organismo="F", fecha_boletin=date(2026, 4, 1)),
        dict(id=8, concepto="Adquisición de 100 resmas de papel", monto=3_000_000.0,
             tipo_operacion="licitacion", organismo="D", fecha_boletin=date(2026, 5, 2), is_duplicate=1),
    ]
    for r in rows:
        r.setdefault("is_duplicate", 0)
        db.add(EjecucionPresupuestaria(boletin_id=1, **r))
    await db.commit()


class FakeLLM:
    provider_id = "fake"
    model_name = "stub"

    def __init__(self, reply: str):
        self.reply = reply

    async def generate_text(self, prompt, temperature=0.7, max_tokens=2000, system_prompt=None):
        return self.reply


class FakeSource:
    name = "fake"

    def __init__(self, result: SourceResult | Exception):
        self.result = result

    async def search(self, item, unit=None):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


# ----------------------------------------------------------------- detection


def test_detection_reason_accepts_goods_and_rejects_services():
    assert svc.detection_reason("Adquisición de aceite de soja", "licitacion")
    assert svc.detection_reason("Licitación para la adquisición de luminarias LED", "licitacion")
    assert svc.detection_reason("Obra de construcción de escuela", "licitacion") is None
    assert svc.detection_reason("Servicio de limpieza", "licitacion") is None
    assert svc.detection_reason("Subsidio a cooperativa", "subsidio") is None
    assert svc.detection_reason("Recompra de títulos de deuda", "decreto") is None


@pytest.mark.asyncio
async def test_list_observables_excludes_works_subsidies_and_duplicates(session):
    items, total = await svc.list_observables(session)
    ids = {i.id for i in items}
    assert ids == {1, 2, 3, 4, 5, 9}
    assert total == 6
    resmas = next(i for i in items if i.id == 1)
    assert resmas.boletin_url == "https://boletin.example/20260430"
    assert "resma" in resmas.motivo


@pytest.mark.asyncio
async def test_list_observables_filters_by_text_and_organismo(session):
    items, _ = await svc.list_observables(session, q="oficio")
    assert [i.id for i in items] == [3]
    items, _ = await svc.list_observables(session, organismo="desarrollo social")
    assert [i.id for i in items] == [1]


# ----------------------------------------------------------------- extraction


def test_regex_extract_quantities():
    assert svc.regex_extract("Adquisición de 1.000 resmas de papel") == (1000.0, "resmas")
    assert svc.regex_extract("Adquisición de dos (2) tráilers gastronómicos")[0] is None  # unit not in list
    assert svc.regex_extract("compra de dos (2) equipos") == (2.0, "equipos")
    assert svc.regex_extract("Adquisición de resmas de papel") == (None, None)


def test_item_from_concepto_drops_destination():
    item = svc.item_from_concepto("ADQUISICION DE RESMAS DE PAPEL Y LIBROS DE ACTAS CON DESTINO A LA DIVISION")
    assert item == "resmas de papel y libros de actas"


@pytest.mark.asyncio
async def test_llm_quantity_not_in_text_is_discarded(session):
    llm = FakeLLM('{"item": "resmas de papel", "cantidad": 5000, "unidad": "resmas", "monto_total": 186031008}')
    result = await svc.analyze(session, 1, provider=llm, external_sources=[], thresholds=TH)
    assert result.extraccion["metodo"] == "llm"
    assert result.extraccion["cantidad"] is None  # hallucinated: 5000 is not in the act
    assert result.precio_unitario is None
    assert result.comparacion["clasificacion"] == "sin_datos_suficientes"


@pytest.mark.asyncio
async def test_llm_failure_falls_back_to_regex(session):
    class Broken(FakeLLM):
        async def generate_text(self, *a, **k):
            raise RuntimeError("ollama down")

    result = await svc.analyze(session, 2, provider=Broken(""), external_sources=[], thresholds=TH)
    assert result.extraccion["metodo"] == "regex"
    assert result.extraccion["cantidad"] == 1000.0
    assert result.precio_unitario == pytest.approx(10_000.0)


# ----------------------------------------------------------------- comparison


def _refs(*prices):
    return [PriceReference("x", "d", p, "2026-01-01") for p in prices]


def test_classify_thresholds():
    assert svc.classify(100, _refs(100, 100, 100), TH)["clasificacion"] == "dentro_de_rango"
    assert svc.classify(140, _refs(100, 100, 100), TH)["clasificacion"] == "observable"
    assert svc.classify(250, _refs(100, 100, 100), TH)["clasificacion"] == "alerta"
    assert svc.classify(250, _refs(100, 100), TH)["clasificacion"] == "sin_datos_suficientes"
    assert svc.classify(None, _refs(100, 100, 100), TH)["clasificacion"] == "sin_datos_suficientes"


def test_thresholds_from_env(monkeypatch):
    monkeypatch.setenv("PRECIO_MERCADO_UMBRAL_OBSERVABLE", "0.5")
    monkeypatch.setenv("PRECIO_MERCADO_MIN_REFERENCIAS", "5")
    th = svc.Thresholds.from_env()
    assert th.observable == 0.5 and th.min_references == 5 and th.alerta == 1.0


@pytest.mark.asyncio
async def test_internal_references_and_classification(session):
    # Act 5: 30.000/u vs internal refs 10.000, 11.000, 9.000 -> median 10.000, +200% -> alerta.
    # Act 9 (same amount, other day/organismo) is a republication and must not count.
    result = await svc.analyze(session, 5, use_llm=False, external_sources=[], thresholds=TH)
    internos = [r for r in result.referencias if r["kind"] == "interna"]
    assert len(internos) == 3
    assert all(r["observed_on"] and r["source"].startswith("Boletín oficial") for r in internos)
    assert result.comparacion["mediana"] == pytest.approx(10_000.0)
    assert result.comparacion["clasificacion"] == "alerta"
    assert "No constituye dictamen" in result.aviso


@pytest.mark.asyncio
async def test_external_source_failure_degrades(session):
    sources = [FakeSource(RuntimeError("boom")), FakeSource(SourceResult("ml", False, reason="no disponible"))]
    result = await svc.analyze(session, 2, use_llm=False, external_sources=sources, thresholds=TH)
    estados = {f["fuente"]: f for f in result.fuentes}
    assert estados["corpus"]["disponible"] is True
    assert estados["ml"]["disponible"] is False
    assert result.comparacion["n_referencias"] == 3


# ----------------------------------------------------------------- Mercado Libre adapter


@pytest.mark.asyncio
async def test_mercadolibre_403_is_reported_as_unavailable(monkeypatch):
    for var in ("ML_ACCESS_TOKEN", "ML_CLIENT_ID", "ML_CLIENT_SECRET"):
        monkeypatch.delenv(var, raising=False)
    transport = httpx.MockTransport(lambda req: httpx.Response(403, json={"message": "forbidden"}))
    async with httpx.AsyncClient(transport=transport) as client:
        r = await MercadoLibreSource(client=client).search("resma a4")
    assert r.available is False and "credenciales" in r.reason


@pytest.mark.asyncio
async def test_mercadolibre_parses_results(monkeypatch):
    for var in ("ML_ACCESS_TOKEN", "ML_CLIENT_ID", "ML_CLIENT_SECRET"):
        monkeypatch.delenv(var, raising=False)
    payload = {"results": [{"title": "Resma A4 75g", "price": 9500, "permalink": "https://ml/1"},
                           {"title": "sin precio", "price": None}]}
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=payload))
    async with httpx.AsyncClient(transport=transport) as client:
        r = await MercadoLibreSource(client=client).search("resma a4")
    assert r.available and len(r.references) == 1
    assert r.references[0].url == "https://ml/1" and r.references[0].observed_on


# ----------------------------------------------------------------- API


@pytest.mark.asyncio
async def test_api_observables_and_analysis(session, monkeypatch):
    from app.api.v1.endpoints import precio_mercado
    from app.db.session import get_db
    from fastapi import FastAPI

    original = svc.analyze

    async def fake_analyze(db, ejecucion_id, **kw):
        return await original(db, ejecucion_id, use_llm=False, external_sources=[], thresholds=TH)

    monkeypatch.setattr(precio_mercado.svc, "analyze", fake_analyze)

    app = FastAPI()
    app.include_router(precio_mercado.router, prefix="/precio-mercado")

    async def _db():
        yield session

    app.dependency_overrides[get_db] = _db
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as client:
        r = await client.get("/precio-mercado/observables")
        assert r.status_code == 200 and r.json()["total"] == 6
        r = await client.post("/precio-mercado/analizar/5")
        assert r.status_code == 200 and r.json()["comparacion"]["clasificacion"] == "alerta"
        r = await client.get("/precio-mercado/analisis/5")
        assert r.status_code == 200 and r.json()["analizado_en"]
        r = await client.get("/precio-mercado/observables")
        assert next(i for i in r.json()["items"] if i["id"] == 5)["ultima_clasificacion"] == "alerta"
        assert (await client.post("/precio-mercado/analizar/999")).status_code == 404
        assert (await client.get("/precio-mercado/config")).json()["umbrales"]["min_references"] == 3
