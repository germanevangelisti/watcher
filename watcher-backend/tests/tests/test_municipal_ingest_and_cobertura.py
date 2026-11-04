"""Municipal ingest into the DB and GET /gasto/cobertura (pm-municipal-cobertura).

In-memory SQLite, fixtures only, no network.
"""

import json
from datetime import date
from pathlib import Path

import httpx
import pytest
import pytest_asyncio

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "muni_cordoba"


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _fake_client(tmp_path):
    from app.scrapers.pds_muni import CordobaMunicipalClient

    def fake_get(url, params):
        name = "dias_publicacion.json" if url.endswith("/dias-publicacion") else "boletin_fecha.json"
        return _Resp(json.loads((FIXTURES / name).read_text(encoding="utf-8")))

    return CordobaMunicipalClient(output_dir=tmp_path, delay=0, http_get=fake_get)


def _text(acto):
    if acto.publicacion_id == 5288:
        return (FIXTURES / "pub_5288.txt").read_text(encoding="utf-8")
    return ""


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
async def test_ingest_persists_municipal_acts_idempotently(session, tmp_path):
    from app.db.models import Analisis, Boletin
    from app.services.municipal_ingest import ingest_cordoba
    from sqlalchemy import func, select

    client = _fake_client(tmp_path)
    stats = await ingest_cordoba(session, client, date(2026, 10, 1), date(2026, 11, 3), get_text=_text)
    assert stats.ediciones == 1
    assert stats.actos == 3
    assert stats.actos_gasto == 1
    assert stats.monto_gasto == 184800000.0

    # Second run updates in place.
    stats2 = await ingest_cordoba(session, client, date(2026, 10, 1), date(2026, 11, 3), get_text=_text)
    assert stats2.actos_nuevos == 0
    n = (await session.execute(select(func.count()).select_from(Analisis)
                               .join(Boletin).where(Boletin.fuente == "municipal_capital"))).scalar()
    assert n == 3

    lic = (await session.execute(select(Analisis).where(Analisis.monto_numerico == 184800000.0))).scalar_one()
    assert lic.is_duplicate_gasto == 0
    assert (lic.nivel, lic.municipio, lic.tipo_gasto) == ("municipal", "Córdoba", "licitacion")
    bol = (await session.execute(select(Boletin).where(Boletin.id == lic.boletin_id))).scalar_one()
    assert (bol.date, bol.fuente) == ("20261014", "municipal_capital")


@pytest.mark.asyncio
async def test_cobertura_endpoint(session, tmp_path):
    from app.api.v1.endpoints import gasto
    from app.db.session import get_db
    from app.services.municipal_ingest import ingest_cordoba
    from fastapi import FastAPI

    await ingest_cordoba(session, _fake_client(tmp_path), date(2026, 10, 1), date(2026, 11, 3), get_text=_text)

    app = FastAPI()
    app.include_router(gasto.router, prefix="/gasto")

    async def _db():
        yield session

    app.dependency_overrides[get_db] = _db
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        body = (await c.get("/gasto/cobertura")).json()

    assert body["municipios_cubiertos"] == ["Córdoba"]
    assert "sección 5" in body["nota"]
    prov, muni = body["fuentes"]
    assert prov["fuente"] == "provincial" and prov["actos_gasto"] == 1
    assert muni["fuente"] == "municipal_capital"
    assert muni["municipio"] == "Córdoba"
    assert (muni["ediciones"], muni["actos"], muni["actos_gasto"]) == (1, 3, 1)
    assert muni["desde"] == muni["hasta"] == "2026-10-14"
    assert muni["monto_gasto"] == 184800000.0

    # The municipal acts are reachable through the listing filter.
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        listado = (await c.get("/gasto/detectado", params={"municipio": "Córdoba"})).json()
    assert listado["total"] == 1


@pytest.mark.asyncio
async def test_republicacion_is_listed_but_not_summed(session, tmp_path):
    """The same tender call published in two editions counts once."""
    from app.services.municipal_ingest import ingest_cordoba

    payload = json.loads((FIXTURES / "boletin_fecha.json").read_text(encoding="utf-8"))
    segunda = json.loads(json.dumps(payload))
    ed = segunda["Object"][0]
    ed["Numero"], ed["Fecha"] = 4507, "2026-10-15T10:00:00"
    for t in ed["TiposPublicacion"]:
        for n in t["TiposNormas"]:
            for p in n["Publicaciones"]:
                p["Id"] += 1000

    from app.scrapers.pds_muni import CordobaMunicipalClient

    def fake_get(url, params):
        if url.endswith("/dias-publicacion"):
            return _Resp({"Object": [{"Fecha": "2026-10-14T00:00:00"}, {"Fecha": "2026-10-15T00:00:00"}]})
        return _Resp(payload if params["fecha"] == "2026-10-14" else segunda)

    def text(acto):
        if acto.publicacion_id in (5288, 6288):
            return (FIXTURES / "pub_5288.txt").read_text(encoding="utf-8")
        return ""

    client = CordobaMunicipalClient(output_dir=tmp_path, delay=0, http_get=fake_get)
    stats = await ingest_cordoba(session, client, date(2026, 10, 1), date(2026, 10, 31), get_text=text)
    assert stats.ediciones == 2
    assert stats.actos_gasto == 1
    assert stats.republicaciones == 1
    assert stats.monto_gasto == 184800000.0


def test_debt_named_only_in_body_header_is_not_gasto():
    from app.services.municipal_ingest import motivo_no_gasto_municipal
    asunto = "Se modifica en parte el Articulo 1 de la Resolucion Serie A N 0883"
    texto = "VISTO: La Resolucion 0883 mediante la cual se dispuso la Emision de las Letras del Tesoro Serie A"
    assert motivo_no_gasto_municipal(asunto) is None
    assert motivo_no_gasto_municipal(asunto, texto) is not None
