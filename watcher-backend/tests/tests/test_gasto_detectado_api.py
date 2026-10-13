"""Tests for GET /gasto/detectado (M8, epic:precio-mercado).

The endpoint reads the M8 columns that the backfill persists, so these tests
seed them directly: what is under test is the filtering, the aggregation and the
two-universe contract, not the rules-based classifier (that has its own module).

Run from watcher-backend/:
    .\\.venv\\Scripts\\python.exe -m pytest tests/tests/test_gasto_detectado_api.py -q
"""

from datetime import date

import httpx
import pytest
import pytest_asyncio


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
    from app.db.models import Analisis, Boletin, EjecucionPresupuestaria, PrecioMercadoAnalisis

    db.add(Boletin(id=1, filename="20260430_4_Secc.pdf", date="20260430", section="4",
                   status="completed", source_url="https://boletin.example/20260430"))
    db.add(Boletin(id=2, filename="20260531_5_Secc.pdf", date="20260531", section="5",
                   status="completed", source_url="https://boletin.example/20260531"))

    def acto(**kw):
        base = dict(boletin_id=1, monto_numerico=1000.0, tipo_gasto="licitacion",
                    nivel="provincial", is_gasto_publico=True, is_duplicate_gasto=0)
        base.update(kw)
        return Analisis(**base)

    db.add_all([
        acto(id=1, organismo="MINISTERIO A", descripcion="Licitación pública de insumos"),
        # Obra sin evidencia de etapa: está en el listado y NO en el ledger.
        acto(id=2, organismo="MINISTERIO B", descripcion="Obra de pavimento",
             monto_numerico=2000.0, tipo_gasto="obra_publica", is_gasto_publico=False),
        # Republicación de la 2: se lista, pero no suma.
        acto(id=3, organismo="MINISTERIO B", descripcion="Obra de pavimento",
             monto_numerico=2000.0, tipo_gasto="obra_publica", is_gasto_publico=False,
             is_duplicate_gasto=1),
        acto(id=4, boletin_id=2, organismo="MUNICIPALIDAD DE CARRILOBO",
             descripcion="Contrátase el servicio de limpieza", monto_numerico=500.0,
             tipo_gasto="servicio", nivel="municipal", municipio="Carrilobo",
             is_gasto_publico=False),
        # No es gasto: fuera del listado por defecto.
        acto(id=5, organismo="JUZGADO", descripcion="Remate de un inmueble",
             monto_numerico=9999.0, tipo_gasto="no_es_gasto", nivel="desconocido",
             is_gasto_publico=False),
        # Sin monto y sin clasificar: fuera del universo, pase lo que pase.
        acto(id=6, organismo="X", descripcion="Sin monto", monto_numerico=0.0),
        acto(id=7, organismo="Y", descripcion="Todavía sin clasificar", tipo_gasto=None),
    ])

    db.add(EjecucionPresupuestaria(id=1, boletin_id=1, analisis_id=1, monto=1000.0,
                                   fecha_boletin=date(2026, 4, 30), organismo="MINISTERIO A"))
    db.add(PrecioMercadoAnalisis(ejecucion_id=1, clasificacion="observable",
                                 resultado_json="{}"))
    await db.commit()


async def _client(session):
    from app.api.v1.endpoints import gasto
    from app.db.session import get_db
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(gasto.router, prefix="/gasto")

    async def _db():
        yield session

    app.dependency_overrides[get_db] = _db
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


@pytest.mark.asyncio
async def test_listado_por_defecto_y_dos_universos(session):
    async with await _client(session) as client:
        body = (await client.get("/gasto/detectado")).json()

    # 1, 2, 3 y 4: los que tienen figura de gasto.  5 (no_es_gasto), 6 (sin monto)
    # y 7 (sin clasificar) quedan afuera.
    assert body["total"] == 4
    # La suma descuenta la republicación, el total no: se muestran las dos cosas.
    assert body["suma"] == 3500.0
    assert body["republicaciones_excluidas"] == 2000.0

    por_id = {i["analisis_id"]: i for i in body["items"]}
    assert por_id[1]["en_ledger"] is True
    assert por_id[1]["ejecucion_id"] == 1
    assert por_id[1]["ultima_clasificacion"] == "observable"
    assert por_id[2]["en_ledger"] is False
    assert por_id[2]["ejecucion_id"] is None
    assert por_id[3]["is_duplicate_gasto"] is True
    assert por_id[2]["es_gasto_publico"] is True


@pytest.mark.asyncio
async def test_obras_y_servicios_aparecen(session):
    """El criterio de M8 que la heurística vieja no cumplía."""
    async with await _client(session) as client:
        obras = (await client.get("/gasto/detectado?tipo=obra_publica")).json()
        servicios = (await client.get("/gasto/detectado?tipo=servicio")).json()
    assert obras["total"] == 2
    assert servicios["total"] == 1


@pytest.mark.asyncio
async def test_solo_gasto_false_incluye_lo_que_no_es_gasto(session):
    async with await _client(session) as client:
        body = (await client.get("/gasto/detectado?solo_gasto=false")).json()
    assert body["total"] == 5
    assert body["suma"] == 3500.0 + 9999.0


@pytest.mark.asyncio
async def test_filtros(session):
    async with await _client(session) as client:
        assert (await client.get("/gasto/detectado?nivel=municipal")).json()["total"] == 1
        r = (await client.get("/gasto/detectado?nivel=municipal")).json()
        assert r["items"][0]["municipio"] == "Carrilobo"

        assert (await client.get("/gasto/detectado?organismo=CARRILOBO")).json()["total"] == 1
        assert (await client.get("/gasto/detectado?q=pavimento")).json()["total"] == 2
        assert (await client.get("/gasto/detectado?monto_min=1000&monto_max=2000")).json()["total"] == 3
        # `boletines.date` es 'YYYYMMDD' texto: si se comparara como fecha, esto
        # devolvería todo y el test no lo notaría.
        mayo = (await client.get("/gasto/detectado?fecha_desde=2026-05-01")).json()
        assert mayo["total"] == 1
        assert mayo["items"][0]["analisis_id"] == 4
        assert mayo["items"][0]["fecha"] == "2026-05-31"

        assert (await client.get("/gasto/detectado?tipo=nivel_inexistente")).json()["total"] == 0


@pytest.mark.asyncio
async def test_paginado(session):
    async with await _client(session) as client:
        # Orden: fecha desc, id desc → 4 (mayo), 3, 2, 1.
        primera = (await client.get("/gasto/detectado?limit=2")).json()
        segunda = (await client.get("/gasto/detectado?limit=2&offset=2")).json()
    assert [i["analisis_id"] for i in primera["items"]] == [4, 3]
    assert [i["analisis_id"] for i in segunda["items"]] == [2, 1]
    # La suma es del filtro entero, no de la página.
    assert primera["suma"] == segunda["suma"] == 3500.0
