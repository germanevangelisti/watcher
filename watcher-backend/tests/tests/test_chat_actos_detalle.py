"""Tests del drill-down a los actos individuales (`story-watcher-chat-actos-detalle`).

El chat sabía agregar (top-5, desglose por organismo y por mes) pero no bajar a
**la fila**: preguntado *"desglosá los 2 actos de abril"* contestaba que no tenía el
detalle.  Lo que se fija acá:

- El organismo se resuelve por **canónica**, no con el `ilike %x%` del endpoint.
  Medido sobre el corpus, el filtro crudo deja afuera `CÁMINOS DE LAS SIERRAS S.A.`
  (4 actos / 675,79 M): es el bug de agrupación un piso más abajo.
- Tope con `total_actos` / `hay_mas` declarados: el contexto va entero al prompt y
  el organismo más grande del corpus tiene 187 filas.
- Cada acto cita su boletín (`source_url`) por join server-side — cero cambio de
  shape de API, que es la frontera con Ampliación B.

Se corre contra un SQLite en memoria con las filas armadas a mano.  Los montos son
ficticios y chicos: el sistema no hardcodea cifras del corpus.

Run from watcher-backend/:
    .venv/Scripts/python.exe -m pytest tests/tests/test_chat_actos_detalle.py -v
"""

import sys
from datetime import date
from pathlib import Path

import pytest
import pytest_asyncio

# `agents.*` vive en la raíz del backend, que pytest no agrega solo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.tools.presupuesto_tools import (  # noqa: E402
    INTENT_ACTOS_DETALLE,
    INTENT_ORGANISMO_DETALLE,
    PresupuestoTools,
    build_actos_system_block,
    detect_presupuesto_intents,
)

EJERCICIO = 2026

# Las tres grafías del mismo organismo que están en el corpus.  La del medio es la
# que el `ilike` naive deja afuera: la tilde no matchea `%CAMINOS%`.
CAMINOS = "CAMINOS DE LAS SIERRAS S.A."
CAMINOS_ALT = "CÁMINOS DE LAS SIERRAS S.A."
CAMINOS_MIN = "Caminos de las Sierras S.A."

# Cómo lo nombra una consulta que sí resuelve.  "Caminos" a secas NO alcanza — ver
# `test_un_nombre_de_una_sola_palabra_no_resuelve`.
CONSULTA = "desglosá los actos de Caminos de las Sierras"

URL_ABRIL = "https://boletin.cordoba.gob.ar/2026/20260410"
URL_AGOSTO = "https://boletin.cordoba.gob.ar/2026/20260805"


@pytest_asyncio.fixture
async def session():
    from app.db.models import Base
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        yield db
    await engine.dispose()


async def _seed(db):
    """Un organismo con tres grafías, actos en dos meses, un duplicado y un boletín sin URL."""
    from app.db.models import Boletin, EjecucionPresupuestaria, PresupuestoBase

    db.add(PresupuestoBase(
        id=1, ejercicio=EJERCICIO, organismo=CAMINOS,
        partida_presupuestaria="3.1.2", monto_inicial=5_000_000_000.0,
        monto_vigente=5_000_000_000.0,
    ))
    db.add_all([
        Boletin(id=10, filename="20260410_4_Secc.pdf", date="20260410",
                section="4", status="completed", source_url=URL_ABRIL),
        # Segundo boletín de abril, sin URL cargada: el acto queda sin cita.
        Boletin(id=11, filename="20260418_4_Secc.pdf", date="20260418",
                section="4", status="completed", source_url=None),
        Boletin(id=12, filename="20260805_4_Secc.pdf", date="20260805",
                section="4", status="completed", source_url=URL_AGOSTO),
    ])
    db.add_all([
        # Abril: los 3 actos que el ciudadano pregunta. Uno por grafía.
        EjecucionPresupuestaria(
            boletin_id=10, presupuesto_base_id=1, organismo=CAMINOS,
            fecha_boletin=date(2026, 4, 10), etapa_gasto="llamado",
            monto=40_770_000.0, concepto='ZONA "G".', tipo_operacion="obra",
            riesgo_watcher="medio", beneficiario="No especificado", is_duplicate=0,
        ),
        EjecucionPresupuestaria(
            boletin_id=11, presupuesto_base_id=1, organismo=CAMINOS_ALT,
            fecha_boletin=date(2026, 4, 18), etapa_gasto="adjudicacion",
            monto=30_000_000.0, concepto="Mejoramiento de caminos de montaña",
            # Único beneficiario REAL del seed: tiene que salir.
            beneficiario="EMPRESA CONSTRUCTORA DEL NORTE S.A.", is_duplicate=0,
        ),
        EjecucionPresupuestaria(
            boletin_id=10, presupuesto_base_id=1, organismo=CAMINOS_MIN,
            fecha_boletin=date(2026, 4, 25), etapa_gasto="llamado",
            monto=20_000_000.0, concepto="Bacheo Ruta 28", is_duplicate=0,
        ),
        # Agosto: el mismo organismo, otro mes. Sin `mes` entra; con `mes`, no.
        EjecucionPresupuestaria(
            boletin_id=12, presupuesto_base_id=1, organismo=CAMINOS,
            fecha_boletin=date(2026, 8, 5), etapa_gasto="pago",
            monto=675_790_000.0, concepto="Certificado de obra N° 7", is_duplicate=0,
        ),
        # Republicación del mismo acto de abril: NO puede entrar (hallazgo 2 de la nota).
        EjecucionPresupuestaria(
            boletin_id=10, presupuesto_base_id=1, organismo=CAMINOS,
            fecha_boletin=date(2026, 4, 10), etapa_gasto="llamado",
            monto=999_000_000.0, concepto='ZONA "G".', is_duplicate=1,
        ),
    ])
    await db.commit()


# ------------------------------------------------------------------- routing


ACTOS = [
    "desglosá los actos de Caminos de las Sierras",
    "mostrame los actos de EPEC de abril",
    "cuáles son los actos de la Dirección de Vialidad",
    "listá los actos publicados por el Ministerio de Salud",
    # El caso original, el que fallaba: nombra el mes, no el organismo, y no trae
    # ninguna palabra de gasto — "los actos" no estaba en `_GASTO_WORDS`.
    "desglosa los 2 actos de abril",
]


@pytest.mark.parametrize("frase", ACTOS)
def test_pedido_de_actos_enruta(frase):
    assert INTENT_ACTOS_DETALLE in detect_presupuesto_intents(frase)


def test_la_palabra_actos_no_se_esconde_en_otra_palabra():
    """"contacto" contiene "acto": el match es por token, no por substring."""
    assert INTENT_ACTOS_DETALLE not in detect_presupuesto_intents(
        "quiero el contacto del organismo de vialidad"
    )


def test_los_chips_no_se_ponen_en_modo_actos():
    chips = [
        "¿Qué porcentaje del presupuesto vigente se ha ejecutado?",
        "¿Qué organismos concentran mayor gasto?",
        "¿Qué finalidades presentan mayor desvío?",
    ]
    for frase in chips:
        assert INTENT_ACTOS_DETALLE not in detect_presupuesto_intents(frase)


def test_el_desglose_agregado_no_se_pone_en_modo_actos():
    """Sin regresión de (d): pedir etapas no es pedir las filas."""
    intents = detect_presupuesto_intents("desglosá los gastos del Ministerio de Salud")

    assert INTENT_ORGANISMO_DETALLE in intents
    assert INTENT_ACTOS_DETALLE not in intents


def test_una_query_de_transparencia_no_trae_actos():
    assert INTENT_ACTOS_DETALLE not in detect_presupuesto_intents(
        "mostrame los boletines con red flags de agosto"
    )


# ------------------------------------------------------------------ resolver


async def test_los_actos_unen_las_grafias_del_organismo(session):
    """Las tres grafías entran: 4 actos, no los 2 de la grafía mayoritaria."""
    await _seed(session)

    r = await PresupuestoTools.get_actos(session, CONSULTA)

    assert r is not None
    assert r["total_actos"] == 4  # 3 de abril + 1 de agosto
    assert set(r["grafias_unificadas"]) == {CAMINOS, CAMINOS_ALT, CAMINOS_MIN}
    assert r["monto_total"] == 766.56  # 40,77 + 30 + 20 + 675,79 — sin el duplicado de 999
    assert r["ejercicio"] == EJERCICIO


async def test_resuelve_por_canonica_y_no_por_ilike(session):
    """El corte de la historia, medido: el `ilike %x%` ve 3 filas, la canónica ve 4.

    La que se escapa del LIKE es la grafía con tilde — `LIKE` no ignora acentos, así
    que `'%CAMINOS DE LAS SIERRAS%'` no matchea `'CÁMINOS DE LAS SIERRAS S.A.'`.
    """
    from app.db.models import EjecucionPresupuestaria
    from sqlalchemy import func, select

    await _seed(session)

    naive = (await session.execute(
        select(func.count()).select_from(EjecucionPresupuestaria).where(
            EjecucionPresupuestaria.organismo.ilike("%CAMINOS DE LAS SIERRAS%"),
            EjecucionPresupuestaria.is_duplicate == 0,
        )
    )).scalar_one()

    r = await PresupuestoTools.get_actos(session, CONSULTA)

    assert naive == 3  # la grafía con tilde se escapa del LIKE
    assert r["total_actos"] == 4


async def test_sin_organismo_en_la_consulta_devuelve_none(session):
    """Nunca un dict vacío: el prompt tiene que poder declarar el hueco."""
    await _seed(session)

    assert await PresupuestoTools.get_actos(session, "desglosá los actos de abril") is None


async def test_un_nombre_de_una_sola_palabra_no_resuelve(session):
    """Limitación medida y declarada, no relajada.

    "Caminos" a secas no alcanza: `CAMINOS DE SIERRAS S.A.` tiene dos tokens
    identificatorios y el resolver exige ≥2 (o una sigla).  Se deja así a propósito —
    una regla laxa de "token único" haría que "municipio" resolviera a
    `MUNICIPIO DE RIO CEBALLOS`, el único del ledger, y el chat afirmaría con
    seguridad que ésos son los actos de los municipios.  Es un problema del matcher,
    con su propio seed de falsos positivos, no de este tool.
    """
    await _seed(session)

    assert await PresupuestoTools.get_actos(session, "desglosá los actos de Caminos de abril") is None


async def test_el_organismo_sin_actos_en_el_mes_pedido_devuelve_ceros(session):
    """Un cero verificado no es un hueco: es información que el agente puede afirmar."""
    await _seed(session)

    r = await PresupuestoTools.get_actos(session, f"{CONSULTA} en septiembre")

    assert r is not None
    assert r["total_actos"] == 0
    assert r["actos"] == []
    assert r["hay_mas"] is False
    # El organismo se reconoció igual: la respuesta dice de quién está hablando.
    # Sin filas en el mes no hay grafías crudas que mostrar, así que cae al canónico.
    assert r["organismo"] == "CAMINOS DE SIERRAS S.A."
    assert r["grafias_unificadas"] == ["CAMINOS DE SIERRAS S.A."]


# --------------------------------------------------------------------- mes


async def test_el_mes_sale_de_la_consulta(session):
    """Sin esto, "los actos de abril" listaría el ejercicio y el tope recortaría mal."""
    await _seed(session)

    r = await PresupuestoTools.get_actos(session, f"{CONSULTA} de abril")

    assert r["mes"] == "2026-04"
    assert r["total_actos"] == 3
    assert {a["fecha"][:7] for a in r["actos"]} == {"2026-04"}


async def test_el_mes_admite_el_anio_explicito(session):
    await _seed(session)

    r = await PresupuestoTools.get_actos(session, "desglosá los actos de Caminos de las Sierras de abril de 2026")

    assert r["mes"] == "2026-04"
    assert r["total_actos"] == 3


async def test_sin_mes_el_mes_lo_pone_el_llamador(session):
    """El parámetro explícito gana: es lo que va a usar la resolución de referencias (T3)."""
    await _seed(session)

    r = await PresupuestoTools.get_actos(session, CONSULTA, mes="2026-08")

    assert r["mes"] == "2026-08"
    assert r["total_actos"] == 1
    assert r["actos"][0]["etapa"] == "pago"


async def test_sin_mes_ni_referencia_cubre_el_ejercicio(session):
    await _seed(session)

    r = await PresupuestoTools.get_actos(session, CONSULTA)

    assert r["mes"] is None
    assert r["total_actos"] == 4


# -------------------------------------------------------------------- filas


async def test_devuelve_las_filas_con_su_fecha_concepto_monto_y_etapa(session):
    await _seed(session)

    r = await PresupuestoTools.get_actos(session, f"{CONSULTA} de abril")

    # Más recientes primero.
    assert [a["fecha"] for a in r["actos"]] == ["2026-04-25", "2026-04-18", "2026-04-10"]
    primero = r["actos"][0]
    assert primero["concepto"] == "Bacheo Ruta 28"
    assert primero["monto"] == 20.0
    assert primero["etapa"] == "llamado"


async def test_cada_acto_cita_su_boletin_por_join_server_side(session):
    """T5: la cita no pasa por ningún endpoint — sale del join dentro del tool."""
    await _seed(session)

    r = await PresupuestoTools.get_actos(session, f"{CONSULTA} de abril")
    por_fecha = {a["fecha"]: a for a in r["actos"]}

    assert por_fecha["2026-04-10"]["source_url"] == URL_ABRIL
    assert por_fecha["2026-04-10"]["boletin"] == "20260410_4_Secc.pdf"
    assert por_fecha["2026-04-10"]["boletin_id"] == 10
    # El boletín sin URL cargada no inventa una: queda sin `source_url` y se cuenta.
    assert "source_url" not in por_fecha["2026-04-18"]
    assert por_fecha["2026-04-18"]["boletin"] == "20260418_4_Secc.pdf"
    assert r["sin_cita"] == 1


async def test_el_beneficiario_centinela_no_se_presenta_como_dato(session):
    """En el corpus es "No especificado" en 964/972 filas; el real es el 0,8%."""
    await _seed(session)

    r = await PresupuestoTools.get_actos(session, f"{CONSULTA} de abril")
    por_fecha = {a["fecha"]: a for a in r["actos"]}

    assert "beneficiario" not in por_fecha["2026-04-10"]
    assert "beneficiario" not in por_fecha["2026-04-25"]
    assert por_fecha["2026-04-18"]["beneficiario"] == "EMPRESA CONSTRUCTORA DEL NORTE S.A."


async def test_los_duplicados_quedan_afuera(session):
    """La republicación de 999 no entra, por grande que sea."""
    await _seed(session)

    r = await PresupuestoTools.get_actos(session, f"{CONSULTA} de abril")

    assert all(a["monto"] != 999.0 for a in r["actos"])
    assert r["total_actos"] == 3


# --------------------------------------------------------------------- tope


async def _seed_muchos(db, cantidad: int = 25):
    """Un organismo con N actos en el mismo mes, para medir el tope."""
    from app.db.models import Boletin, EjecucionPresupuestaria, PresupuestoBase

    db.add(PresupuestoBase(
        id=1, ejercicio=EJERCICIO, organismo=CAMINOS,
        monto_inicial=5_000_000_000.0, monto_vigente=5_000_000_000.0,
    ))
    db.add(Boletin(id=10, filename="20260410_4_Secc.pdf", date="20260410",
                   section="4", status="completed", source_url=URL_ABRIL))
    db.add_all([
        EjecucionPresupuestaria(
            boletin_id=10, presupuesto_base_id=1, organismo=CAMINOS,
            fecha_boletin=date(2026, 4, min(i, 28)), etapa_gasto="llamado",
            monto=float(i) * 1_000_000.0, concepto=f"Obra {i}", is_duplicate=0,
        )
        for i in range(1, cantidad + 1)
    ])
    await db.commit()


async def test_el_tope_recorta_y_lo_declara(session):
    """Sin tope, el peor organismo del corpus mete ~15k tokens al prompt sin avisar."""
    await _seed_muchos(session)

    r = await PresupuestoTools.get_actos(session, CONSULTA, tope=5)

    assert r["actos_listados"] == 5
    assert r["total_actos"] == 25
    assert r["hay_mas"] is True
    assert "quedan 20 sin listar" in r["nota"]
    # Lo que queda es lo de mayor monto del día más reciente, no un corte arbitrario.
    assert [a["monto"] for a in r["actos"]] == [25.0, 24.0, 23.0, 22.0, 21.0]
    # El monto total es de los 25, no de los 5 listados: el agregado no se recorta.
    assert r["monto_total"] == 325.0


async def test_sin_recorte_el_tope_no_ensucia_la_respuesta(session):
    await _seed_muchos(session, cantidad=3)

    r = await PresupuestoTools.get_actos(session, CONSULTA)

    assert r["hay_mas"] is False
    assert r["actos_listados"] == r["total_actos"] == 3
    assert "sin recortes" in r["nota"]


async def test_el_tope_por_defecto_es_20(session):
    await _seed_muchos(session, cantidad=25)

    r = await PresupuestoTools.get_actos(session, CONSULTA)

    assert r["actos_listados"] == 20
    assert r["hay_mas"] is True


# -------------------------------------------------------- contrato del chat


class _SessionCtx:
    def __init__(self, db):
        self._db = db

    async def __aenter__(self):
        return self._db

    async def __aexit__(self, *exc):
        return False


@pytest.fixture
def wired_agent(monkeypatch, session):
    """Agente con la sesión sembrada detrás de `AsyncSessionLocal`.

    Se corta la búsqueda sobre el corpus: si no, el agente arma el
    `RetrievalService` real y el test termina leyendo el ChromaDB **de la máquina**
    (`~/.watcher/chromadb`), así que `data_used` cambiaría según lo que cada
    desarrollador tenga indexado.  Acá se mide el contrato de `get_actos`, no la
    recuperación vectorial.
    """
    from agents.insight_reporting import agent as agent_module

    monkeypatch.setattr(agent_module, "AsyncSessionLocal", lambda: _SessionCtx(session))
    agente = agent_module.InsightReportingAgent()
    # Se corta la búsqueda sobre el corpus: el agente arma su propio
    # `RetrievalService` (con sesión) y el test terminaría leyendo el ChromaDB
    # **de la máquina** (`~/.watcher/chromadb`), así que `data_used` cambiaría
    # según lo que cada desarrollador tenga indexado.
    async def _sin_corpus(*_args, **_kwargs):
        return []

    monkeypatch.setattr(agent_module.InsightReportingAgent, "_buscar_en_corpus", _sin_corpus)
    agente.provider = None  # sin provider: cae al fallback, y alcanza
    return agente


async def test_query_with_data_cita_los_actos(session, wired_agent):
    """La key `actos` entra sola: el intent no arrastra otro contexto de presupuesto."""
    await _seed(session)

    out = await wired_agent.query_with_data("desglosá los actos de Caminos de las Sierras de abril")

    assert out["success"] is True
    assert out["data_used"] == ["actos"]


async def test_query_with_data_sin_organismo_no_afirma_actos(session, wired_agent):
    """Sin organismo reconocido no se inyecta una key vacía: el prompt declara el hueco."""
    await _seed(session)

    out = await wired_agent.query_with_data("desglosá los actos de abril")

    assert out["success"] is True
    assert "actos" not in out["data_used"]


# ------------------------------------------------------- citación en el prompt


async def test_el_prompt_le_pide_al_modelo_citar_el_boletin(session, wired_agent):
    """T5 sin esto no llega: el tool devuelve `source_url`, pero nadie lo escribía.

    El link del parser FE existe para la cita; si el modelo no está instruido para
    emitirla, el drill-down a la fila llega sin su fuente oficial y el `source_url`
    del contexto no sirve para nada.
    """
    await _seed(session)
    r = await PresupuestoTools.get_actos(session, f"{CONSULTA} de abril")

    system = wired_agent._build_messages("desglosá los actos", {"actos": r})[0]["content"]

    assert "ACTOS INDIVIDUALES EN EL CONTEXTO" in system
    assert "Markdown" in system
    assert "Nunca inventes ni armes una URL" in system
    assert "nota" in system  # el recorte declarado tiene que decirlo


async def test_el_prompt_no_se_ensucia_sin_actos(wired_agent):
    """El resto del chat no cambia de comportamiento: la regla es condicional."""
    system = wired_agent._build_messages("¿cuánto se ejecutó?", {"ejecucion_resumen": {}})[0]["content"]

    assert "ACTOS INDIVIDUALES EN EL CONTEXTO" not in system


def test_el_bloque_de_actos_es_vacio_sin_actos():
    assert build_actos_system_block(None) == ""
    assert build_actos_system_block({}) == ""
