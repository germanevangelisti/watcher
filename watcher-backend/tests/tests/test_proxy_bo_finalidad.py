"""Tests for app/services/proxy_bo_finalidad.py and its endpoint (Should MB).

El proxy BO existe para responder "cuánto publicó el BO de cada finalidad, contra
el techo de esa finalidad" sin convertirse en una ejecución que no es.  Estos
tests clavan las dos invariantes que lo harían deshonesto:

1. **El numerador es publicación, no caja.**  En toda la respuesta, la única clave
   que puede contener "devengado" es `honestidad.es_devengado` /
   `honestidad.es_devengado_cge`, y las dos tienen que ser `False`.  La etiqueta
   del numerador (`etiqueta_numerador`) viaja en la respuesta para que la UI la
   **lea** en vez de elegirla.
2. **Lo publicado sin programa no se reparte.**  Viaja en
   `cobertura.monto_sin_programa` con su conteo de actos.  Por eso el test de
   cierre compara la suma de las filas contra `monto_con_programa` y **no** contra
   `monto_total`: esa diferencia es el dato, no un redondeo.

Igual que en `test_presupuesto_finalidades.py`, el doblado se testea con tuplas
armadas a mano y la query contra una sesión async SQLite real.

Run from watcher-backend/:
    uv run pytest tests/tests/test_proxy_bo_finalidad.py -v
"""

from datetime import date

import httpx
import pytest
import pytest_asyncio
from app.api.v1.endpoints import presupuesto as presupuesto_endpoint
from app.db.models import Base, EjecucionPresupuestaria, PresupuestoBase
from app.db.session import get_db
from app.services.gasto_classifier import (
    ETAPA_ADJUDICACION,
    ETAPA_CONTRATO,
    ETAPA_LLAMADO,
    ETAPA_MODIFICACION,
    ETAPA_PAGO,
)
from app.services.presupuesto_finalidades import (
    FINALIDADES_DESTACADAS,
    SIN_CLASIFICAR,
    SIN_PARTIDA,
    agregar_finalidades,
)
from app.services.proxy_bo_finalidad import (
    ES_DEVENGADO,
    ES_DEVENGADO_CGE,
    ES_PROXY_BO,
    ETAPA_BUCKET_COMPROMISO,
    ETAPA_BUCKET_EJECUCION,
    ETAPA_BUCKET_LLAMADO,
    ETAPA_BUCKET_OTRO,
    ETIQUETA_NUMERADOR,
    NOTAS_HONESTIDAD,
    _etapa_bucket,
    agregar_proxy_bo,
    fetch_proxy_bo,
)
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

EJERCICIO = 2026

# Same shape as the 2026 corpus: one partida per bucket the anexo has.
SEED_TECHO = [
    ("1.6.0", 100_000_000.0),
    ("2.1.0", 50_000_000.0),
    ("3.1.2", 200_000_000.0),
    ("4.5.0", 400_000_000.0),
    ("5.0.0", 20_000_000.0),
    ("6.2.0", 5_000_000.0),
    ("Recursos", 7_000_000.0),
    ("Cuentas", 3_000_000.0),
    ("", 9_000_000.0),
]
TECHO_TOTAL = sum(monto for _, monto in SEED_TECHO)  # 794_000_000
TECHO_BUCKET = 400_000_000.0 + 20_000_000.0 + 5_000_000.0 + 7_000_000.0 + 3_000_000.0 + 9_000_000.0

# Ledger rows as `(programa_id, partida, etapa_gasto, monto, count)`.  `None` en
# `programa_id` es "no matcheó programa": es la cobertura que no se reparte.
FILAS = [
    (1, "1.6.0", ETAPA_LLAMADO, 120_000_000.0, 3),
    (2, "2.1.0", ETAPA_ADJUDICACION, 40_000_000.0, 1),
    (3, "3.1.2", ETAPA_PAGO, 10_000_000.0, 2),
    (4, "4.5.0", ETAPA_CONTRATO, 30_000_000.0, 1),
    (5, "Recursos", ETAPA_LLAMADO, 8_000_000.0, 1),
    (None, None, ETAPA_PAGO, 50_000_000.0, 7),
    (None, None, None, 2_000_000.0, 1),
]
FILAS_TOTAL = 260_000_000.0
FILAS_CON_PROGRAMA = 208_000_000.0
FILAS_SIN_PROGRAMA = 52_000_000.0
FILAS_SIN_PROGRAMA_COUNT = 8

FECHAS = [date(2026, 2, 1), date(2026, 5, 15), date(2026, 9, 30)]


def _techo(rows=SEED_TECHO, ejercicio=EJERCICIO):
    """Techo por finalidad armado con el mismo doblado puro que usa la API."""
    return agregar_finalidades([(p, m, m) for p, m in rows], ejercicio)


def _por_clave(proxy):
    return {item.clave: item for item in proxy.items}


def _claves_con(payload, aguja, path=""):
    """Todas las `(ruta, valor)` de claves que contienen `aguja`, a cualquier nivel."""
    encontradas = []
    if isinstance(payload, dict):
        for clave, valor in payload.items():
            ruta = f"{path}.{clave}"
            if aguja in clave.lower():
                encontradas.append((ruta, valor))
            encontradas.extend(_claves_con(valor, aguja, ruta))
    elif isinstance(payload, list):
        for i, valor in enumerate(payload):
            encontradas.extend(_claves_con(valor, aguja, f"{path}[{i}]"))
    return encontradas


def _valores_string(payload):
    """Todos los strings del payload aplanados.  Las claves se chequean aparte
    (`_claves_con`): un label es un valor, y `es_devengado` es una clave."""
    salida = []
    if isinstance(payload, dict):
        for valor in payload.values():
            salida.extend(_valores_string(valor))
    elif isinstance(payload, list):
        for valor in payload:
            salida.extend(_valores_string(valor))
    elif isinstance(payload, str):
        salida.append(payload)
    return salida


class TestEtapaBucket:
    """El llamado no se mezcla con el compromiso asumido (lección de V.3.3)."""

    def test_el_llamado_tiene_su_propia_clave(self):
        assert _etapa_bucket(ETAPA_LLAMADO) == ETAPA_BUCKET_LLAMADO

    def test_adjudicacion_y_contrato_son_compromiso_asumido(self):
        assert _etapa_bucket(ETAPA_ADJUDICACION) == ETAPA_BUCKET_COMPROMISO
        assert _etapa_bucket(ETAPA_CONTRATO) == ETAPA_BUCKET_COMPROMISO

    def test_el_pago_es_ejecucion(self):
        assert _etapa_bucket(ETAPA_PAGO) == ETAPA_BUCKET_EJECUCION

    def test_lo_desconocido_no_se_adivina(self):
        assert _etapa_bucket(ETAPA_MODIFICACION) == ETAPA_BUCKET_OTRO
        assert _etapa_bucket(None) == ETAPA_BUCKET_OTRO


class TestAgregarProxyBo:
    def test_siempre_publica_las_tres_mas_el_bucket_en_orden(self):
        proxy = agregar_proxy_bo(_techo(), FILAS, EJERCICIO)

        assert [item.clave for item in proxy.items] == [
            *FINALIDADES_DESTACADAS,
            SIN_CLASIFICAR,
        ]

    def test_las_destacadas_salen_en_cero_aunque_no_hayan_publicado(self):
        # "$0 publicado en Defensa" es información: su ausencia sería un agujero.
        proxy = agregar_proxy_bo(_techo(), [(1, "1.6.0", ETAPA_LLAMADO, 5.0, 1)], EJERCICIO)

        por_clave = _por_clave(proxy)
        assert por_clave["2"].monto_publicado == 0.0
        assert por_clave["2"].count == 0
        assert por_clave["3"].monto_publicado == 0.0

    def test_el_publicado_se_atribuye_por_el_primer_componente_de_la_partida(self):
        proxy = agregar_proxy_bo(_techo(), FILAS, EJERCICIO)

        por_clave = _por_clave(proxy)
        assert por_clave["1"].monto_publicado == 120_000_000.0
        assert por_clave["1"].count == 3
        assert por_clave["2"].monto_publicado == 40_000_000.0
        assert por_clave["3"].monto_publicado == 10_000_000.0

    def test_el_porcentaje_es_contra_el_techo_de_esa_finalidad(self):
        proxy = agregar_proxy_bo(_techo(), FILAS, EJERCICIO)

        por_clave = _por_clave(proxy)
        assert por_clave["1"].pct_publicado_techo == 120.0  # 120 de 100
        assert por_clave["2"].pct_publicado_techo == 80.0
        assert por_clave["3"].pct_publicado_techo == 5.0

    def test_un_porcentaje_sobre_cien_se_publica_y_no_se_recorta(self):
        # La doctrina del proyecto: una alerta >100% es visible, no se silencia.
        proxy = agregar_proxy_bo(_techo(), FILAS, EJERCICIO)

        assert _por_clave(proxy)["1"].pct_publicado_techo > 100.0

    def test_sin_techo_no_hay_porcentaje(self):
        # Una finalidad que publicó pero no está en la Ley cargada: 0% afirmaría
        # una medición que no existe.
        techo = _techo([("1.6.0", 100_000_000.0)])
        proxy = agregar_proxy_bo(techo, FILAS, EJERCICIO)

        por_clave = _por_clave(proxy)
        assert por_clave["1"].pct_publicado_techo == 120.0
        assert por_clave["3"].monto_techo == 0.0
        assert por_clave["3"].pct_publicado_techo is None

    def test_sin_filas_no_se_inventa_publicacion(self):
        proxy = agregar_proxy_bo(_techo(), [], EJERCICIO)

        assert [item.clave for item in proxy.items] == [
            *FINALIDADES_DESTACADAS,
            SIN_CLASIFICAR,
        ]
        assert all(item.monto_publicado == 0.0 for item in proxy.items)
        assert all(item.count == 0 for item in proxy.items)
        # El techo sigue estando: $0 publicado contra techo conocido es un dato.
        assert _por_clave(proxy)["3"].monto_techo == 200_000_000.0
        assert proxy.cobertura.pct_sin_programa == 0.0


class TestCobertura:
    """Lo que no tiene programa se declara.  El test que importa es el de cierre."""

    def test_lo_sin_programa_no_entra_en_ninguna_finalidad(self):
        proxy = agregar_proxy_bo(_techo(), FILAS, EJERCICIO)
        publicado_en_filas = sum(item.monto_publicado for item in proxy.items)

        # Cierra contra lo atribuido, no contra el total: la diferencia ES el dato.
        assert publicado_en_filas == FILAS_CON_PROGRAMA
        assert publicado_en_filas == proxy.cobertura.monto_con_programa
        assert proxy.cobertura.monto_sin_programa == FILAS_SIN_PROGRAMA
        assert publicado_en_filas != proxy.cobertura.monto_total

    def test_declara_el_conteo_de_actos_sin_programa(self):
        proxy = agregar_proxy_bo(_techo(), FILAS, EJERCICIO)

        assert proxy.cobertura.count_sin_programa == FILAS_SIN_PROGRAMA_COUNT

    def test_la_cobertura_cierra_el_total(self):
        proxy = agregar_proxy_bo(_techo(), FILAS, EJERCICIO)

        assert proxy.cobertura.monto_total == FILAS_TOTAL
        assert (
            proxy.cobertura.monto_con_programa + proxy.cobertura.monto_sin_programa
            == proxy.cobertura.monto_total
        )
        assert proxy.cobertura.pct_sin_programa == pytest.approx(
            100.0 * FILAS_SIN_PROGRAMA / FILAS_TOTAL
        )

    def test_separa_lo_no_clasificado_de_lo_atribuido(self):
        # `Recursos` no es finalidad del clasificador: es ruido de parseo del
        # anexo, y no es lo mismo que un agujero de cobertura.
        proxy = agregar_proxy_bo(_techo(), FILAS, EJERCICIO)

        assert proxy.cobertura.monto_atribuido_finalidad == 200_000_000.0
        assert proxy.cobertura.monto_no_clasificado == 8_000_000.0
        assert (
            proxy.cobertura.monto_atribuido_finalidad
            + proxy.cobertura.monto_no_clasificado
            == proxy.cobertura.monto_con_programa
        )

    def test_un_programa_con_partida_vacia_no_es_cobertura_perdida(self):
        # Matcheó programa, pero el clasificador no le puede poner finalidad.  Si
        # esto cayera en `sin_programa`, el banner culparía al matching cuando el
        # problema es el parseo de la partida.
        proxy = agregar_proxy_bo(_techo(), [(1, "", ETAPA_PAGO, 4_000_000.0, 1)], EJERCICIO)

        assert proxy.cobertura.monto_sin_programa == 0.0
        assert proxy.cobertura.count_sin_programa == 0
        assert proxy.cobertura.monto_no_clasificado == 4_000_000.0
        detalle = {d.clave: d for d in _por_clave(proxy)[SIN_CLASIFICAR].detalle}
        assert detalle[SIN_PARTIDA].monto_publicado == 4_000_000.0

    def test_declara_el_span_del_numerador_y_que_el_denominador_es_anual(self):
        # El % es contra la Ley completa: sin el span, un 30% se lee como poco
        # gasto cuando puede ser pocos meses publicados.
        proxy = agregar_proxy_bo(
            _techo(), FILAS, EJERCICIO, fecha_desde=FECHAS[0], fecha_hasta=FECHAS[2]
        )

        assert proxy.cobertura.fecha_desde == FECHAS[0]
        assert proxy.cobertura.fecha_hasta == FECHAS[2]
        assert proxy.cobertura.denominador_es_anual is True


class TestDetalleDelBucket:
    def test_el_detalle_trae_lo_publicado_y_lo_que_solo_tiene_techo(self):
        proxy = agregar_proxy_bo(_techo(), FILAS, EJERCICIO)
        detalle = {d.clave: d for d in _por_clave(proxy)[SIN_CLASIFICAR].detalle}

        # Publicó y tiene techo.
        assert detalle["4"].monto_publicado == 30_000_000.0
        assert detalle["4"].monto_techo == 400_000_000.0
        # Sólo techo: no publicó nada, y por eso mismo tiene que verse.
        assert detalle["5"].monto_publicado == 0.0
        assert detalle["5"].monto_techo == 20_000_000.0
        assert detalle["5"].pct_publicado_techo == 0.0

    def test_el_detalle_va_de_mas_publicado_a_menos_y_despues_por_techo(self):
        proxy = agregar_proxy_bo(_techo(), FILAS, EJERCICIO)
        detalle = _por_clave(proxy)[SIN_CLASIFICAR].detalle

        assert [d.clave for d in detalle] == [
            "4",  # 30M publicado
            "Recursos",  # 8M publicado
            "5",  # 0 publicado, 20M de techo
            SIN_PARTIDA,  # 0, 9M
            "6",  # 0, 5M
            "Cuentas",  # 0, 3M
        ]

    def test_el_detalle_suma_el_bucket(self):
        proxy = agregar_proxy_bo(_techo(), FILAS, EJERCICIO)
        bucket = _por_clave(proxy)[SIN_CLASIFICAR]

        assert sum(d.monto_publicado for d in bucket.detalle) == bucket.monto_publicado
        assert sum(d.count for d in bucket.detalle) == bucket.count
        assert bucket.monto_techo == TECHO_BUCKET

    def test_el_ruido_de_parseo_conserva_su_label_y_el_seis_no_lo_tiene(self):
        proxy = agregar_proxy_bo(_techo(), FILAS, EJERCICIO)
        detalle = {d.clave: d for d in _por_clave(proxy)[SIN_CLASIFICAR].detalle}

        assert detalle["Recursos"].label == "Recursos"
        assert detalle[SIN_PARTIDA].label == "Partida vacía"
        # `6` no está en el clasificador: el consumidor muestra la clave.
        assert detalle["6"].label is None

    def test_las_destacadas_no_tienen_detalle(self):
        proxy = agregar_proxy_bo(_techo(), FILAS, EJERCICIO)

        for item in proxy.items[:-1]:
            assert item.detalle == ()


class TestEtapas:
    """La composición se informa, no se resta."""

    def test_separa_llamado_de_compromiso_asumido_y_de_pago(self):
        proxy = agregar_proxy_bo(_techo(), FILAS, EJERCICIO)
        etapas = {e.clave: e.monto for e in proxy.etapas}

        assert etapas[ETAPA_BUCKET_LLAMADO] == 128_000_000.0  # 120 + 8
        assert etapas[ETAPA_BUCKET_COMPROMISO] == 70_000_000.0  # 40 + 30
        assert etapas[ETAPA_BUCKET_EJECUCION] == 60_000_000.0  # 10 + 50
        assert etapas[ETAPA_BUCKET_OTRO] == 2_000_000.0

    def test_las_etapas_cierran_el_total_y_no_lo_mueven(self):
        # Restar el llamado de la barra de compromiso es lo que V.3.3 arregló:
        # acá se informa aparte y el total queda intacto.
        proxy = agregar_proxy_bo(_techo(), FILAS, EJERCICIO)

        assert sum(e.monto for e in proxy.etapas) == proxy.cobertura.monto_total
        assert sum(e.monto for e in proxy.etapas) == FILAS_TOTAL

    def test_las_cuatro_etapas_salen_siempre_con_su_label(self):
        proxy = agregar_proxy_bo(_techo(), [], EJERCICIO)

        assert [e.clave for e in proxy.etapas] == [
            ETAPA_BUCKET_LLAMADO,
            ETAPA_BUCKET_COMPROMISO,
            ETAPA_BUCKET_EJECUCION,
            ETAPA_BUCKET_OTRO,
        ]
        assert all(e.label for e in proxy.etapas)
        assert all(e.monto == 0.0 for e in proxy.etapas)


class TestHonestidad:
    def test_lo_publicado_no_es_devengado(self):
        proxy = agregar_proxy_bo(_techo(), FILAS, EJERCICIO)

        assert proxy.honestidad.es_proxy_bo is True
        assert proxy.honestidad.es_devengado is False
        assert proxy.honestidad.es_devengado_cge is False
        assert (ES_PROXY_BO, ES_DEVENGADO, ES_DEVENGADO_CGE) == (True, False, False)

    def test_la_etiqueta_del_numerador_viaja_en_la_respuesta(self):
        proxy = agregar_proxy_bo(_techo(), FILAS, EJERCICIO)

        assert proxy.honestidad.etiqueta_numerador == ETIQUETA_NUMERADOR
        assert "publicado" in proxy.honestidad.etiqueta_numerador.lower()

    def test_el_copy_nombra_lo_que_la_respuesta_no_es(self):
        proxy = agregar_proxy_bo(_techo(), FILAS, EJERCICIO)
        notas = " ".join(proxy.honestidad.notas)

        assert "no son ejecución presupuestaria" in notas
        assert "Devengado CGE" in notas
        assert "no se reparte" in notas

    def test_el_copy_no_afirma_devengado_en_ningun_lado(self):
        # Ni una nota, ni un label, ni una clave puede afirmar devengado: la
        # única nota que lo nombra es la que lo niega.
        proxy = agregar_proxy_bo(_techo(), FILAS, EJERCICIO)

        for texto in (
            [e.label for e in proxy.etapas]
            + [i.label for i in proxy.items]
            + [d.label or d.clave for i in proxy.items for d in i.detalle]
        ):
            assert "devengado" not in texto.lower()

        assert proxy.honestidad.notas == NOTAS_HONESTIDAD
        con_devengado = [n for n in proxy.honestidad.notas if "devengado" in n.lower()]
        assert len(con_devengado) == 1
        assert con_devengado[0] == "No es Devengado CGE: no hay caja devengada en esta respuesta."


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


async def _seed_techo(db, rows=SEED_TECHO, ejercicio=EJERCICIO):
    """Inserta el techo y devuelve `partida -> presupuesto_base.id`."""
    ids: dict[str, int] = {}
    for partida, monto in rows:
        row = PresupuestoBase(
            ejercicio=ejercicio,
            organismo="ORGANISMO DE PRUEBA",
            programa="1 - PROGRAMA",
            partida_presupuestaria=partida,
            monto_inicial=monto,
            monto_vigente=monto,
            descripcion="PROGRAMA DE PRUEBA",
            fecha_aprobacion=date(ejercicio, 1, 1),
        )
        db.add(row)
        await db.flush()
        ids[partida] = row.id
    return ids


async def _seed_ledger(db, rows, ids, fechas=None):
    """`rows` son `(partida_techo|None, etapa, monto, is_duplicate)`.

    `partida_techo` se resuelve contra el techo ya insertado; `None` deja la fila
    sin `presupuesto_base_id`, que es el caso "no matcheó programa".
    """
    for i, (partida, etapa, monto, dup) in enumerate(rows):
        db.add(
            EjecucionPresupuestaria(
                presupuesto_base_id=ids.get(partida) if partida is not None else None,
                fecha_boletin=(fechas or FECHAS)[i % len(fechas or FECHAS)],
                organismo="ORGANISMO DE PRUEBA",
                concepto="ACTO DE PRUEBA",
                monto=monto,
                etapa_gasto=etapa,
                is_duplicate=1 if dup else 0,
            )
        )
    await db.flush()


LEDGER = [
    ("1.6.0", ETAPA_LLAMADO, 120_000_000.0, False),
    ("3.1.2", ETAPA_PAGO, 10_000_000.0, False),
    (None, ETAPA_PAGO, 50_000_000.0, False),
]
LEDGER_TOTAL = 180_000_000.0


class TestFetchProxyBo:
    @pytest.mark.asyncio
    async def test_dobla_el_ledger_contra_el_techo_del_ejercicio(self, session):
        ids = await _seed_techo(session)
        await _seed_ledger(session, LEDGER, ids)

        proxy = await fetch_proxy_bo(session, EJERCICIO)

        assert proxy is not None
        assert proxy.ejercicio == EJERCICIO
        assert [item.clave for item in proxy.items] == ["1", "2", "3", SIN_CLASIFICAR]
        por_clave = _por_clave(proxy)
        assert por_clave["1"].monto_publicado == 120_000_000.0
        assert por_clave["3"].monto_publicado == 10_000_000.0

    @pytest.mark.asyncio
    async def test_una_fila_sin_programa_se_declara_y_no_desaparece(self, session):
        ids = await _seed_techo(session)
        await _seed_ledger(session, LEDGER, ids)

        proxy = await fetch_proxy_bo(session, EJERCICIO)

        # El outer join es la diferencia entre declarar $50M y perderlos.
        assert proxy.cobertura.monto_sin_programa == 50_000_000.0
        assert proxy.cobertura.count_sin_programa == 1
        assert proxy.cobertura.monto_total == LEDGER_TOTAL

    @pytest.mark.asyncio
    async def test_una_fila_de_otro_ejercicio_cae_como_sin_programa(self, session):
        # El filtro de ejercicio vive en el ON del join, no en el WHERE: si
        # estuviera en el WHERE, esta fila desaparecería del total en vez de
        # declararse como no atribuible.
        ids = await _seed_techo(session)
        otros = await _seed_techo(session, [("1.6.0", 1.0)], ejercicio=2025)
        await _seed_ledger(
            session, [("1.6.0", ETAPA_LLAMADO, 33_000_000.0, False)], otros
        )

        proxy = await fetch_proxy_bo(session, EJERCICIO)

        assert proxy.cobertura.monto_sin_programa == 33_000_000.0
        assert proxy.cobertura.monto_con_programa == 0.0
        assert _por_clave(proxy)["1"].monto_publicado == 0.0
        del ids  # el techo 2026 sólo existe para que haya una Ley que leer

    @pytest.mark.asyncio
    async def test_ignora_las_filas_duplicadas(self, session):
        ids = await _seed_techo(session)
        await _seed_ledger(
            session,
            [
                ("1.6.0", ETAPA_LLAMADO, 120_000_000.0, False),
                ("1.6.0", ETAPA_LLAMADO, 120_000_000.0, True),
            ],
            ids,
        )

        proxy = await fetch_proxy_bo(session, EJERCICIO)

        assert _por_clave(proxy)["1"].monto_publicado == 120_000_000.0
        assert proxy.cobertura.monto_total == 120_000_000.0

    @pytest.mark.asyncio
    async def test_publica_el_span_real_del_ledger(self, session):
        ids = await _seed_techo(session)
        # 4 filas sobre 3 fechas: el span es min/max, no la primera y la última.
        await _seed_ledger(
            session,
            [
                ("1.6.0", ETAPA_LLAMADO, 1.0, False),
                ("1.6.0", ETAPA_LLAMADO, 1.0, False),
                ("2.1.0", ETAPA_LLAMADO, 1.0, False),
                ("3.1.2", ETAPA_PAGO, 1.0, False),
            ],
            ids,
        )

        proxy = await fetch_proxy_bo(session, EJERCICIO)

        assert proxy.cobertura.fecha_desde == FECHAS[0]
        assert proxy.cobertura.fecha_hasta == FECHAS[2]

    @pytest.mark.asyncio
    async def test_ejercicio_sin_ley_devuelve_none(self, session):
        await _seed_techo(session)
        await _seed_ledger(session, LEDGER, {"1.6.0": 1})

        # Mismo hueco que `fetch_finalidades`: sin techo no hay contra qué
        # contrastar, y devolver ceros afirmaría que no se publicó nada.
        assert await fetch_proxy_bo(session, 2027) is None

    @pytest.mark.asyncio
    async def test_ejercicio_con_ley_y_sin_ledger_es_un_cero_medido(self, session):
        await _seed_techo(session)

        proxy = await fetch_proxy_bo(session, EJERCICIO)

        assert proxy is not None
        assert proxy.cobertura.monto_total == 0.0
        assert proxy.cobertura.fecha_desde is None
        assert _por_clave(proxy)["3"].monto_techo == 200_000_000.0


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


RUTA = "/presupuesto/finalidades/proxy-bo/"


class TestProxyBoEndpoint:
    @pytest.mark.asyncio
    async def test_responde_el_slice_3_mas_1(self, session, client):
        ids = await _seed_techo(session)
        await _seed_ledger(session, LEDGER, ids)

        response = await client.get(RUTA, params={"ejercicio": EJERCICIO})

        assert response.status_code == 200
        body = response.json()
        assert [item["clave"] for item in body["items"]] == [
            "1",
            "2",
            "3",
            "sin_clasificar",
        ]
        assert [item["label"] for item in body["items"]] == [
            "Administración Gubernamental",
            "Servicios de Defensa y Seguridad",
            "Servicios Sociales",
            "Sin clasificar",
        ]

    @pytest.mark.asyncio
    async def test_los_montos_salen_en_millones(self, session, client):
        ids = await _seed_techo(session)
        await _seed_ledger(session, LEDGER, ids)

        response = await client.get(RUTA, params={"ejercicio": EJERCICIO})

        body = response.json()
        # El serializer del proyecto emite millones: 120.000.000 ARS viaja como 120.0.
        por_clave = {item["clave"]: item for item in body["items"]}
        assert por_clave["1"]["monto_publicado"] == pytest.approx(120.0)
        assert por_clave["1"]["monto_techo"] == pytest.approx(100.0)
        assert body["cobertura"]["monto_total"] == pytest.approx(180.0)

    @pytest.mark.asyncio
    async def test_la_ruta_expone_la_cobertura(self, session, client):
        ids = await _seed_techo(session)
        await _seed_ledger(session, LEDGER, ids)

        response = await client.get(RUTA, params={"ejercicio": EJERCICIO})

        cobertura = response.json()["cobertura"]
        assert cobertura["monto_sin_programa"] == pytest.approx(50.0)
        assert cobertura["count_sin_programa"] == 1
        assert cobertura["pct_sin_programa"] == pytest.approx(
            round(100.0 * 50_000_000 / LEDGER_TOTAL, 2)
        )
        assert cobertura["denominador_es_anual"] is True
        assert cobertura["fecha_desde"] == FECHAS[0].isoformat()
        assert cobertura["fecha_hasta"] == FECHAS[2].isoformat()

    @pytest.mark.asyncio
    async def test_la_ruta_expone_la_composicion_por_etapa(self, session, client):
        ids = await _seed_techo(session)
        await _seed_ledger(session, LEDGER, ids)

        response = await client.get(RUTA, params={"ejercicio": EJERCICIO})

        etapas = {e["clave"]: e for e in response.json()["etapas"]}
        assert sorted(etapas) == [
            "compromiso_asumido",
            "llamado",
            "pago",
            "sin_etapa",
        ]
        assert etapas["llamado"]["monto"] == pytest.approx(120.0)
        assert etapas["compromiso_asumido"]["monto"] == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_la_ruta_lleva_la_etiqueta_y_los_flags_de_honestidad(self, session, client):
        ids = await _seed_techo(session)
        await _seed_ledger(session, LEDGER, ids)

        response = await client.get(RUTA, params={"ejercicio": EJERCICIO})

        honestidad = response.json()["honestidad"]
        assert honestidad["es_proxy_bo"] is True
        assert honestidad["es_devengado"] is False
        assert honestidad["es_devengado_cge"] is False
        assert honestidad["etiqueta_numerador"] == ETIQUETA_NUMERADOR

    @pytest.mark.asyncio
    async def test_la_unica_clave_devengado_es_la_que_lo_niega(self, session, client):
        # El test que justifica la historia: si alguien agrega un
        # `monto_devengado` o rotula el numerador como devengado, esto falla.
        ids = await _seed_techo(session)
        await _seed_ledger(session, LEDGER, ids)

        response = await client.get(RUTA, params={"ejercicio": EJERCICIO})

        claves = _claves_con(response.json(), "devengado")
        assert claves == [
            (".honestidad.es_devengado", False),
            (".honestidad.es_devengado_cge", False),
        ]

    @pytest.mark.asyncio
    async def test_ningun_texto_de_la_respuesta_afirma_devengado(self, session, client):
        ids = await _seed_techo(session)
        await _seed_ledger(session, LEDGER, ids)

        response = await client.get(RUTA, params={"ejercicio": EJERCICIO})

        # El único texto con la palabra es la nota que la niega.  Ningún label,
        # ningún `etiqueta_numerador` y ninguna nota la afirma.
        con_devengado = [
            s for s in _valores_string(response.json()) if "devengado" in s.lower()
        ]
        assert len(con_devengado) == 1
        assert "no hay caja devengada" in con_devengado[0]

    @pytest.mark.asyncio
    async def test_ejercicio_sin_ley_es_404_y_lo_dice(self, session, client):
        await _seed_techo(session)
        await _seed_ledger(session, LEDGER, {"1.6.0": 1})

        response = await client.get(RUTA, params={"ejercicio": 2027})

        assert response.status_code == 404
        assert "hueco" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_el_bucket_trae_su_detalle_por_la_ruta(self, session, client):
        ids = await _seed_techo(session)
        await _seed_ledger(session, LEDGER, ids)

        response = await client.get(RUTA, params={"ejercicio": EJERCICIO})

        bucket = response.json()["items"][-1]
        detalle = {d["clave"]: d for d in bucket["detalle"]}
        # Nadie puede leer "sin_clasificar" del proxy sin ver que 400 de esos
        # millones de techo son Servicios Económicos.
        assert detalle["4"]["monto_techo"] == pytest.approx(400.0)
        assert detalle["5"]["monto_publicado"] == pytest.approx(0.0)
        assert detalle["5"]["pct_publicado_techo"] == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_la_ruta_no_expone_ejecucion_cge(self, session, client):
        ids = await _seed_techo(session)
        await _seed_ledger(session, LEDGER, ids)

        response = await client.get(RUTA, params={"ejercicio": EJERCICIO})

        body = response.json()
        # Tampoco hay barras de compromiso/ejecución acá: eso es el contraste del
        # BO sobre organismos, no este slice por finalidad.
        assert "pct_ejecucion" not in str(body)
        assert "pct_compromiso" not in str(body)
