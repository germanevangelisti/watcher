"""Tests for app/services/presupuesto_finalidades.py and its endpoint (Must MB).

The classifier and the fold are pure functions, so they are tested directly with
hand-built rows.  The query is tested against a real async SQLite session over
the project's declarative metadata (same idiom as `test_ejecucion_ledger.py`),
and the route is exercised through a minimal ASGI app carrying only this router —
that way the response_model serialization and the 404 are covered without
booting `app.main` (startup events, settings, data dirs).

Run from watcher-backend/:
    uv run pytest tests/tests/test_presupuesto_finalidades.py -v
"""

import httpx
import pytest
import pytest_asyncio
from app.api.v1.endpoints import presupuesto as presupuesto_endpoint
from app.db.models import Base, PresupuestoBase
from app.db.session import get_db
from app.services.presupuesto_finalidades import (
    FINALIDADES_DESTACADAS,
    NOTAS_ESTRUCTURALES,
    SIN_CLASIFICAR,
    SIN_PARTIDA,
    agregar_finalidades,
    clasificar_partida,
    fetch_finalidades,
)
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

EJERCICIO = 2026

# One row per bucket the real corpus has, 2026.  Amounts are in ARS; the
# endpoint serializes them in millions, so the unit tests below work in ARS.
SEED = [
    ("1.6.0", 100_000_000.0),
    ("1.2.0", 50_000_000.0),
    ("2.1.0", 30_000_000.0),
    ("3.1.2", 200_000_000.0),
    ("4.5.0", 400_000_000.0),  # finalidad real, va al bucket y sale en `detalle`
    ("5.0.0", 20_000_000.0),  # idem
    ("6.2.0", 5_000_000.0),  # no es finalidad del clasificador
    ("Recursos", 7_000_000.0),
    ("Cuentas", 3_000_000.0),
    ("", 9_000_000.0),
]
SEED_TOTAL = sum(monto for _, monto in SEED)  # 824_000_000


@pytest_asyncio.fixture
async def session():
    """Real async SQLite session over the project's declarative metadata."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        yield db

    await engine.dispose()


async def _seed(db, rows=SEED, ejercicio=EJERCICIO):
    for row in rows:
        # 2-tuples seed `monto_inicial == monto_vigente` (the real 2026 corpus);
        # 3-tuples let a test build a corte with a sancionado ≠ vigente gap.
        partida, inicial, vigente = (
            (row[0], row[1], row[1]) if len(row) == 2 else row
        )
        db.add(
            PresupuestoBase(
                ejercicio=ejercicio,
                organismo="ORGANISMO DE PRUEBA",
                programa="1 - PROGRAMA",
                partida_presupuestaria=partida,
                monto_inicial=inicial,
                monto_vigente=vigente,
            )
        )
    await db.flush()


class TestClasificarPartida:
    def test_toma_el_primer_componente(self):
        assert clasificar_partida("1.6.0") == "1"
        assert clasificar_partida("4.5.0") == "4"
        assert clasificar_partida("3.1.2") == "3"

    def test_tolera_espacios_y_componente_unico(self):
        assert clasificar_partida("  2.1.0 ") == "2"
        assert clasificar_partida("3") == "3"

    def test_no_confunde_las_palabras_del_anexo_con_finalidades(self):
        # El anexo imprime "Recursos"/"Cuentas" en la misma columna del fin_fun_det.
        assert clasificar_partida("Recursos") == "Recursos"
        assert clasificar_partida("Cuentas") == "Cuentas"

    def test_vacio_y_none_van_a_sin_partida(self):
        assert clasificar_partida("") == SIN_PARTIDA
        assert clasificar_partida("   ") == SIN_PARTIDA
        assert clasificar_partida(None) == SIN_PARTIDA


class TestAgregarFinalidades:
    def test_siempre_publica_las_tres_mas_el_bucket_en_orden(self):
        result = agregar_finalidades(
            [(p, m, m) for p, m in SEED], EJERCICIO
        )
        assert [item.clave for item in result.items] == [
            *FINALIDADES_DESTACADAS,
            SIN_CLASIFICAR,
        ]

    def test_las_filas_destacadas_salen_aunque_el_ejercicio_no_tenga_esa_finalidad(self):
        # Un ejercicio con sólo finalidad 3: 1 y 2 salen en $0, no desaparecen.
        result = agregar_finalidades([("3.1.2", 10.0, 10.0)], EJERCICIO)

        por_clave = {item.clave: item for item in result.items}
        assert por_clave["1"].monto_vigente == 0.0
        assert por_clave["1"].count == 0
        assert por_clave["2"].monto_vigente == 0.0
        assert por_clave["3"].monto_vigente == 10.0

    def test_agrupa_por_primer_digito(self):
        result = agregar_finalidades(
            [
                ("1.6.0", 100.0, 100.0),
                ("1.2.0", 50.0, 50.0),
                ("3.1.2", 200.0, 200.0),
            ],
            EJERCICIO,
        )
        por_clave = {item.clave: item for item in result.items}
        assert por_clave["1"].monto_inicial == 150.0
        assert por_clave["1"].count == 2
        assert por_clave["3"].monto_inicial == 200.0

    def test_el_bucket_expone_los_montos_de_finalidades_reales(self):
        result = agregar_finalidades([(p, m, m) for p, m in SEED], EJERCICIO)
        bucket = result.items[-1]

        detalle = {d.clave: d for d in bucket.detalle}
        # La finalidad 4 es una finalidad real y su monto tiene que verse.
        assert detalle["4"].label == "Servicios Económicos"
        assert detalle["4"].monto_vigente == 400_000_000.0
        assert detalle["5"].label == "Deuda Pública"
        assert detalle["5"].monto_vigente == 20_000_000.0

    def test_el_bucket_separa_el_ruido_de_parseo(self):
        result = agregar_finalidades([(p, m, m) for p, m in SEED], EJERCICIO)
        detalle = {d.clave: d for d in result.items[-1].detalle}

        assert detalle[SIN_PARTIDA].label == "Partida vacía"
        assert detalle[SIN_PARTIDA].monto_vigente == 9_000_000.0
        assert detalle["Recursos"].monto_vigente == 7_000_000.0
        assert detalle["Cuentas"].monto_vigente == 3_000_000.0
        # `6` no está en el clasificador: sin label, sale por `clave`.
        assert detalle["6"].label is None
        assert detalle["6"].monto_vigente == 5_000_000.0

    def test_el_detalle_va_de_mayor_a_menor(self):
        result = agregar_finalidades([(p, m, m) for p, m in SEED], EJERCICIO)
        montos = [d.monto_vigente for d in result.items[-1].detalle]
        assert montos == sorted(montos, reverse=True)
        assert [d.clave for d in result.items[-1].detalle] == [
            "4",
            "5",
            "sin_partida",
            "Recursos",
            "6",
            "Cuentas",
        ]

    def test_las_destacadas_no_tienen_detalle(self):
        result = agregar_finalidades([(p, m, m) for p, m in SEED], EJERCICIO)
        for item in result.items[:-1]:
            assert item.detalle == ()

    def test_los_montos_cierran_el_techo(self):
        result = agregar_finalidades([(p, m, m) for p, m in SEED], EJERCICIO)

        assert result.total_vigente == SEED_TOTAL
        assert result.total_inicial == SEED_TOTAL
        # Cierra exacto, no aproximado: es el techo del ciudadano.
        assert sum(item.monto_vigente for item in result.items) == SEED_TOTAL
        assert sum(item.monto_inicial for item in result.items) == SEED_TOTAL

    def test_el_detalle_suma_el_bucket(self):
        result = agregar_finalidades([(p, m, m) for p, m in SEED], EJERCICIO)
        bucket = result.items[-1]

        assert sum(d.monto_vigente for d in bucket.detalle) == bucket.monto_vigente
        assert sum(d.count for d in bucket.detalle) == bucket.count

    def test_participacion_es_del_techo_y_suma_cien(self):
        result = agregar_finalidades([(p, m, m) for p, m in SEED], EJERCICIO)
        por_clave = {item.clave: item for item in result.items}

        assert por_clave["3"].participacion_techo_pct == pytest.approx(
            100.0 * 200_000_000 / SEED_TOTAL, abs=0.01
        )
        assert sum(
            item.participacion_techo_pct for item in result.items
        ) == pytest.approx(100.0, abs=0.05)
        for d in por_clave[SIN_CLASIFICAR].detalle:
            assert 0.0 <= d.participacion_techo_pct <= 100.0

    def test_cuenta_las_filas(self):
        result = agregar_finalidades([(p, m, m) for p, m in SEED], EJERCICIO)
        assert result.total_registros == len(SEED)
        assert result.ejercicio == EJERCICIO

    def test_montos_nulos_cuentan_cero_y_no_rompen_el_cierre(self):
        result = agregar_finalidades(
            [("1.6.0", None, None), ("2.1.0", 100.0, 100.0)], EJERCICIO
        )
        por_clave = {item.clave: item for item in result.items}

        assert por_clave["1"].count == 1
        assert por_clave["1"].monto_vigente == 0.0
        assert result.total_vigente == 100.0
        assert sum(item.monto_vigente for item in result.items) == 100.0

    def test_ejercicio_vacio_da_cero_en_todo_sin_inventar_filas(self):
        result = agregar_finalidades([], EJERCICIO)

        assert result.total_registros == 0
        assert result.total_vigente == 0.0
        assert [item.clave for item in result.items] == [
            *FINALIDADES_DESTACADAS,
            SIN_CLASIFICAR,
        ]
        # Sin techo no se afirma participación: 0, no una división por cero.
        assert all(item.participacion_techo_pct == 0.0 for item in result.items)


class TestHonestidad:
    """El corte dice qué es y qué no es.  El copy sigue al dato, no al revés."""

    @staticmethod
    def _a_tres(rows):
        # 2-tuples valen inicial == vigente; 3-tuples traen el par explícito.
        return [(r[0], r[1], r[1]) if len(r) == 2 else r for r in rows]

    @classmethod
    def _agregar(cls, rows=SEED):
        return agregar_finalidades(cls._a_tres(rows), EJERCICIO).honestidad

    def test_declara_las_tres_cosas_que_el_corte_no_es(self):
        honestidad = self._agregar()

        assert honestidad.es_techo is True
        assert honestidad.es_credito_modificado is False
        assert honestidad.incluye_devengado_cge is False

    def test_inicial_es_vigente_sale_de_medir_las_filas(self):
        # El corpus 2026 real: 480/480 con el mismo monto en ambos campos.
        honestidad = self._agregar()

        assert honestidad.inicial_es_vigente is True
        assert honestidad.filas_inicial_distinto_vigente == 0

    def test_el_copy_nombra_lo_que_la_respuesta_no_es(self):
        notas = " ".join(self._agregar().notas)

        assert "crédito modificado" in notas
        assert "CGE" in notas
        assert "techo" in notas

    def test_el_copy_deja_de_decir_cero_cuando_el_corte_tiene_variacion(self):
        # El test que importa: si el copy estuviera hardcodeado, la API seguiría
        # afirmando "inicial = vigente" sobre un corte que ya tiene variación.
        honestidad = self._agregar(
            [("1.6.0", 100.0, 150.0), ("2.1.0", 30.0, 30.0)]
        )

        assert honestidad.inicial_es_vigente is False
        assert honestidad.filas_inicial_distinto_vigente == 1
        notas = " ".join(honestidad.notas)
        assert "NO es 0" in notas
        assert "por construcción" not in notas

    def test_cuenta_todas_las_filas_con_variacion(self):
        honestidad = self._agregar(
            [
                ("1.6.0", 100.0, 150.0),
                ("2.1.0", 30.0, 10.0),
                ("3.1.2", 5.0, 5.0),
            ]
        )

        assert honestidad.filas_inicial_distinto_vigente == 2
        assert "2 de 3 filas" in " ".join(honestidad.notas)

    def test_un_corte_vacio_no_afirma_inicial_es_vigente(self):
        # Sin filas no hay corte: `inicial == vigente` es una propiedad del corte,
        # y afirmarla en vacío sería exactamente el tipo de copy que no queremos.
        honestidad = self._agregar([])

        assert honestidad.inicial_es_vigente is False
        assert "no se afirma nada" in " ".join(honestidad.notas)

    def test_las_notas_estructurales_van_siempre(self):
        # La parte que no depende de ninguna medición no puede desaparecer por un
        # corte raro: es la que dice que los montos son techo y no caja CGE.
        for honestidad in (self._agregar(), self._agregar([]), self._agregar([("1.6.0", 1.0, 2.0)])):
            assert honestidad.notas[: len(NOTAS_ESTRUCTURALES)] == NOTAS_ESTRUCTURALES


class TestFetchFinalidades:
    @pytest.mark.asyncio
    async def test_agrupa_las_filas_del_ejercicio(self, session):
        await _seed(session)

        result = await fetch_finalidades(session, EJERCICIO)

        assert result is not None
        assert result.total_registros == len(SEED)
        assert result.total_vigente == SEED_TOTAL

    @pytest.mark.asyncio
    async def test_ignora_los_otros_ejercicios(self, session):
        await _seed(session)
        await _seed(session, [("1.6.0", 999_000_000.0)], ejercicio=2025)

        result = await fetch_finalidades(session, EJERCICIO)

        assert result is not None
        assert result.total_vigente == SEED_TOTAL

    @pytest.mark.asyncio
    async def test_ejercicio_sin_ley_devuelve_none(self, session):
        await _seed(session)

        # No es techo $0: es un hueco, y el llamador tiene que poder declararlo.
        assert await fetch_finalidades(session, 2027) is None


@pytest_asyncio.fixture
async def client(session):
    """ASGI client over this router alone, with `get_db` pointed at the session."""
    app = FastAPI()
    app.include_router(presupuesto_endpoint.router, prefix="/presupuesto")

    async def _override():
        yield session

    app.dependency_overrides[get_db] = _override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestFinalidadesEndpoint:
    @pytest.mark.asyncio
    async def test_responde_el_slice_3_mas_1(self, session, client):
        await _seed(session)

        response = await client.get("/presupuesto/finalidades/", params={"ejercicio": EJERCICIO})

        assert response.status_code == 200
        body = response.json()
        assert [item["clave"] for item in body["items"]] == ["1", "2", "3", "sin_clasificar"]
        assert [item["label"] for item in body["items"]] == [
            "Administración Gubernamental",
            "Servicios de Defensa y Seguridad",
            "Servicios Sociales",
            "Sin clasificar",
        ]
        assert body["total_registros"] == len(SEED)

    @pytest.mark.asyncio
    async def test_los_montos_salen_en_millones(self, session, client):
        await _seed(session)

        response = await client.get("/presupuesto/finalidades/", params={"ejercicio": EJERCICIO})

        body = response.json()
        # El serializer del proyecto emite millones: el techo de 824.000.000 ARS
        # viaja como 824.0 y el frontend lo multiplica de vuelta.
        assert body["total_vigente"] == pytest.approx(824.0)
        por_clave = {item["clave"]: item for item in body["items"]}
        assert por_clave["3"]["monto_vigente"] == pytest.approx(200.0)

    @pytest.mark.asyncio
    async def test_el_bucket_trae_su_detalle_por_la_ruta(self, session, client):
        await _seed(session)

        response = await client.get("/presupuesto/finalidades/", params={"ejercicio": EJERCICIO})

        bucket = response.json()["items"][-1]
        detalle = {d["clave"]: d for d in bucket["detalle"]}
        # Nadie puede leer "sin_clasificar 53,9%" sin ver que 400 de esos
        # millones son Servicios Económicos.
        assert detalle["4"]["label"] == "Servicios Económicos"
        assert detalle["4"]["monto_vigente"] == pytest.approx(400.0)

    @pytest.mark.asyncio
    async def test_no_expone_porcentaje_de_ejecucion(self, session, client):
        await _seed(session)

        response = await client.get("/presupuesto/finalidades/", params={"ejercicio": EJERCICIO})

        body = response.json()
        assert "pct_ejecucion" not in str(body)
        assert "pct_compromiso" not in str(body)

    @pytest.mark.asyncio
    async def test_ejercicio_sin_ley_es_404_y_lo_dice(self, session, client):
        await _seed(session)

        response = await client.get("/presupuesto/finalidades/", params={"ejercicio": 2027})

        assert response.status_code == 404
        assert "hueco" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_la_ruta_expone_los_campos_de_honestidad(self, session, client):
        await _seed(session)

        response = await client.get("/presupuesto/finalidades/", params={"ejercicio": EJERCICIO})

        honestidad = response.json()["honestidad"]
        assert honestidad["es_techo"] is True
        assert honestidad["inicial_es_vigente"] is True
        assert honestidad["filas_inicial_distinto_vigente"] == 0
        assert honestidad["es_credito_modificado"] is False
        assert honestidad["incluye_devengado_cge"] is False

    @pytest.mark.asyncio
    async def test_la_ruta_lleva_el_copy_de_honestidad(self, session, client):
        await _seed(session)

        response = await client.get("/presupuesto/finalidades/", params={"ejercicio": EJERCICIO})

        # El copy viaja en la respuesta: la UI no lo inventa ni lo recuerda.
        notas = " ".join(response.json()["honestidad"]["notas"])
        assert "crédito modificado" in notas
        assert "CGE" in notas
        assert "techo" in notas

    @pytest.mark.asyncio
    async def test_la_honestidad_no_se_despega_del_dato_por_la_ruta(self, session, client):
        # Corte con brecha sancionado ≠ vigente: la respuesta entera — flags y
        # copy — tiene que dejar de afirmar que inicial == vigente.
        await _seed(session, [("1.6.0", 100_000_000.0, 150_000_000.0)], ejercicio=EJERCICIO)

        response = await client.get("/presupuesto/finalidades/", params={"ejercicio": EJERCICIO})

        honestidad = response.json()["honestidad"]
        assert honestidad["inicial_es_vigente"] is False
        assert honestidad["filas_inicial_distinto_vigente"] == 1
        assert "NO es 0" in " ".join(honestidad["notas"])
