"""Tests de GET /gasto/por-jurisdiccion y del filtro por código (WMA1).

El mapa necesita tres cosas que el listado no daba: todas las jurisdicciones
—también las que no tienen actos—, el gasto per cápita con población del Censo
2022 y una clave que una las grafías del mismo gobierno local.  Lo que se testea
es eso: la agregación, la normalización de nombres y la honestidad de "sin datos"
(no es gasto cero).

Run from watcher-backend/:
    .\\.venv\\Scripts\\python.exe -m pytest tests/tests/test_gasto_por_jurisdiccion_api.py -q
"""

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
    from app.db.models import Analisis, Boletin

    db.add(Boletin(id=1, filename="20260430_5_Secc.pdf", date="20260430", section="5",
                   status="completed", source_url="https://boletin.example/1"))

    def acto(**kw):
        base = dict(boletin_id=1, monto_numerico=1000.0, tipo_gasto="licitacion",
                    nivel="municipal", is_gasto_publico=True, is_duplicate_gasto=0)
        base.update(kw)
        return Analisis(**base)

    db.add_all([
        # El mismo gobierno local con tres grafías: una sola jurisdicción.
        acto(id=1, municipio="Rio Ceballos", descripcion="Licitación de insumos", monto_numerico=1000.0),
        acto(id=2, municipio="Río Ceballos", descripcion="Obra de cordón cuneta", monto_numerico=2000.0),
        # Republicación de la 2: se declara, no suma.
        acto(id=3, municipio="La Ciudad De Río Ceballos", descripcion="Obra de cordón cuneta",
             monto_numerico=2000.0, is_duplicate_gasto=1),
        # Otra jurisdicción, con la errata de la fuente.
        acto(id=4, municipio="Carrillobo", descripcion="Compra de luminarias",
             monto_numerico=500.0, nivel="comunal"),
        # Gasto municipal que no dice a qué municipio pertenece.
        acto(id=5, municipio=None, descripcion="Transferencia a instituciones",
             monto_numerico=400.0),
        # El gasto provincial no se reparte entre municipios.
        acto(id=6, nivel="provincial", municipio=None, descripcion="Licitación provincial",
             monto_numerico=9999.0),
        # Fuera del universo: no es gasto o no tiene monto.
        acto(id=7, tipo_gasto="no_es_gasto", descripcion="Remate", monto_numerico=777.0),
        acto(id=8, municipio="Río Ceballos", descripcion="Sin monto", monto_numerico=0.0),
    ])
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
async def test_devuelve_todas_las_jurisdicciones_del_catalogo(session):
    async with await _client(session) as client:
        body = (await client.get("/gasto/por-jurisdiccion")).json()

    # El mapa pinta gris lo que no tiene datos: si sólo vinieran las que tienen
    # actos, el gris no existiría y un hueco se leería como gasto cero.
    assert len(body["jurisdicciones"]) == 427
    assert body["totales"]["jurisdicciones"] == 427
    assert body["totales"]["con_cobertura"] == 2
    assert body["fuente"]["poblacion"].startswith("Censo Nacional de Población")


@pytest.mark.asyncio
async def test_agrupa_las_grafias_del_mismo_gobierno_local(session):
    async with await _client(session) as client:
        body = (await client.get("/gasto/por-jurisdiccion")).json()

    rio = next(j for j in body["jurisdicciones"] if j["codigo"] == "140147")
    assert rio["nombre"] == "Río Ceballos"
    assert rio["tipo"] == "municipio"
    assert rio["nivel"] == "municipal"
    # Actos canónicos: la republicación (id 3) no cuenta dos veces.
    assert rio["actos"] == 2
    assert rio["republicaciones"] == 1
    assert rio["gasto"] == 3000.0
    assert rio["poblacion_2022"] == 27136
    assert rio["gasto_per_capita"] == round(3000.0 / 27136, 2)
    assert rio["cobertura"] is True

    # "Carrillobo" es la errata de Carrilobo en la fuente.
    carrilobo = next(j for j in body["jurisdicciones"] if j["codigo"] == "140994")
    assert carrilobo["actos"] == 1
    assert carrilobo["gasto"] == 500.0


@pytest.mark.asyncio
async def test_sin_datos_no_es_gasto_cero(session):
    async with await _client(session) as client:
        body = (await client.get("/gasto/por-jurisdiccion")).json()

    capital = next(j for j in body["jurisdicciones"] if j["codigo"] == "140077")
    assert capital["nombre"] == "Córdoba"
    assert capital["cobertura"] is False
    assert capital["actos"] == 0
    assert capital["gasto"] == 0.0
    # Sin actos no hay per cápita que informar: `None`, no 0.
    assert capital["gasto_per_capita"] is None


@pytest.mark.asyncio
async def test_provincial_y_sin_jurisdiccion_no_se_reparten(session):
    async with await _client(session) as client:
        body = (await client.get("/gasto/por-jurisdiccion")).json()

    niveles = {n["nivel"]: n for n in body["por_nivel"]}
    assert niveles["provincial"]["gasto"] == 9999.0
    assert niveles["provincial"]["actos"] == 1
    # Los 3 actos municipales/comunales canónicos (1, 2 y 4) y el que no dice
    # municipio (5) están en su nivel: el mapa no los inventa en un área.
    assert niveles["municipal"]["actos"] == 3
    assert niveles["comunal"]["actos"] == 1

    sin = body["sin_jurisdiccion"]
    assert sin["actos"] == 1
    assert sin["gasto"] == 400.0
    assert sin["niveles"] == ["municipal"]

    # 1, 2, 4 asignados + 5 sin jurisdicción. La republicación (3) y lo que está
    # fuera del universo (7, 8) no suman.
    assert body["totales"]["actos"] == 4
    assert body["totales"]["gasto"] == 3900.0


@pytest.mark.asyncio
async def test_filtro_detectado_por_codigo_une_las_grafias(session):
    async with await _client(session) as client:
        por_codigo = (await client.get("/gasto/detectado?municipio_codigo=140147")).json()
        inexistente = (await client.get("/gasto/detectado?municipio_codigo=999999")).json()

    # El listado sí muestra la republicación; el filtro une las tres grafías.
    assert por_codigo["total"] == 3
    assert {i["municipio"] for i in por_codigo["items"]} == {
        "Rio Ceballos", "Río Ceballos", "La Ciudad De Río Ceballos",
    }
    assert inexistente["total"] == 0
    assert inexistente["items"] == []


def test_normalizacion_de_nombres():
    from app.services.jurisdicciones import resolver

    assert resolver("Río Ceballos")["codigo"] == "140147"
    assert resolver("Rio Ceballos")["codigo"] == "140147"
    assert resolver("La Ciudad De Río Ceballos")["codigo"] == "140147"
    assert resolver("MUNICIPALIDAD DE CARRILOBO")["codigo"] == "140994"
    assert resolver("Carrillobo")["codigo"] == "140994"
    # "Los Zorros" aparece como "Zorros" en los actos.
    assert resolver("Zorros")["nombre"] == "Los Zorros"
    # Dos gobiernos locales comparten nombre: no se elige uno al azar.
    assert resolver("Los Chañaritos") is None
    assert resolver("") is None
    assert resolver("Ciudad Inventada") is None
