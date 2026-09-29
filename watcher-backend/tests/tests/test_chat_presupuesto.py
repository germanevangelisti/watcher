"""Tests del cableado chat → presupuesto (chips ejecutivos + system prompt).

Historias del pack P0: `chat-presupuesto-keywords` y `chat-prompt-resumen`.

Se fija acá lo que es puro y barato: el enrutado de keywords (las 3 frases
literales de los chips del FE + sinónimos), el builder del bloque de system
prompt, y el armado de mensajes del agente.  No bootea `app.main` ni toca la
DB: el resumen se ejercita con dicts armados a mano, que es lo que el prompt
consume.

Los montos del resumen son ficticios y chicos a propósito: el sistema no
hardcodea cifras del corpus, las lee de la DB en runtime.

Run from watcher-backend/:
    .venv/bin/python -m pytest tests/tests/test_chat_presupuesto.py -v
"""

import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
import pytest_asyncio

# `agents.*` vive en la raíz del backend, que pytest no agrega solo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.tools.presupuesto_tools import (  # noqa: E402
    INTENT_FINALIDADES,
    INTENT_ORGANISMO_DETALLE,
    INTENT_ORGANISMOS,
    INTENT_RESUMEN,
    PresupuestoTools,
    build_presupuesto_system_block,
    detect_presupuesto_intents,
    public_resumen,
    resolver_familia_organismo,
)
from app.services.presupuesto_matching import canonical_organismo_name  # noqa: E402

# Copy literal de los chips del empty state del chat (agents-dashboard.tsx).
CHIPS = [
    ("¿Qué porcentaje del presupuesto vigente se ha ejecutado?", INTENT_RESUMEN),
    ("¿Qué organismos concentran mayor gasto?", INTENT_ORGANISMOS),
    ("¿Qué finalidades presentan mayor desvío?", INTENT_FINALIDADES),
]

SINONIMOS = [
    ("¿cuánto se gastó del presupuesto 2026?", INTENT_RESUMEN),
    ("qué porcentaje se ejecutó", INTENT_RESUMEN),
    ("qué ministerios gastan más plata", INTENT_ORGANISMOS),
    ("cuánta plata gasta cada repartición", INTENT_ORGANISMOS),
    ("qué funciones tienen mayor sobreejecución", INTENT_FINALIDADES),
    ("cuáles son las finalidades con más brecha", INTENT_FINALIDADES),
]

# El path de transparencia no se toca: ninguna de estas debe matchear presupuesto.
TRANSPARENCIA = [
    "mostrame los boletines con red flags",
    # `organismo` sin señal de gasto: sigue siendo la query de entidades.
    "qué organismos aparecen en los boletines de agosto",
    "cuántos documentos hay",
    "tendencias de transparencia 2025",
    "qué beneficiarios aparecen",
]


@pytest.mark.parametrize("frase,intent", CHIPS, ids=["chip-a", "chip-b", "chip-c"])
def test_chip_frase_literal_enruta_al_intent(frase, intent):
    assert detect_presupuesto_intents(frase) == {intent}


@pytest.mark.parametrize("frase,intent", SINONIMOS)
def test_sinonimo_enruta_al_intent(frase, intent):
    assert intent in detect_presupuesto_intents(frase)


@pytest.mark.parametrize("frase", TRANSPARENCIA)
def test_query_de_transparencia_no_matchea_presupuesto(frase):
    assert detect_presupuesto_intents(frase) == set()


def _resumen(**over):
    """Resumen con la forma que devuelve `PresupuestoTools.get_ejecucion_resumen`."""
    base = {
        "ejercicio": 2026,
        "unidad": "millones de ARS",
        "monto_vigente_total": 100.0,
        "monto_publicado_total": 40.0,
        "monto_compromiso": 30.0,
        "monto_ejecucion_pagos": 10.0,
        "pct_ejecucion_sobre_vigente": 10.0,
        "pct_compromiso_sobre_vigente": 30.0,
        "actos_publicados": 7,
        "organismos_sobre_compromiso": 0,
        "periodo": {
            "mes_desde": "feb",
            "mes_hasta": "sep",
            "meses_cubiertos": 8,
            "meses_del_ejercicio": 12,
            "meses_vencidos_sin_ingesta": ["ene"],
        },
        "pct_publicado_sin_denominador": 12.5,
        "honestidad": ["El numerador es lo PUBLICADO en el Boletín Oficial."],
        "_por_organismo": [],
    }
    base.update(over)
    return base


# ---------------------------------------------------------------- system block


def test_bloque_sin_datos_declara_el_hueco_y_prohibe_inventar():
    bloque = build_presupuesto_system_block(None)

    assert "sin datos de ejecución" in bloque
    assert "NO inventes" in bloque
    # Un hueco declarado no puede traer cifras.
    assert not any(c.isdigit() for c in bloque)


def test_bloque_con_resumen_lleva_los_montos_de_la_fuente():
    bloque = build_presupuesto_system_block(_resumen())

    assert "ejercicio 2026" in bloque
    assert "100.0" in bloque  # vigente
    assert "40.0" in bloque  # publicado
    assert "10.0" in bloque  # ejecución
    assert "feb a sep" in bloque and "8 de 12" in bloque
    assert "enero" not in bloque  # el mes sin ingesta se declara, no se dramatiza


def test_bloque_con_resumen_arrastra_la_disciplina_de_honestidad():
    bloque = build_presupuesto_system_block(_resumen())

    assert "El numerador es lo PUBLICADO en el Boletín Oficial." in bloque
    # Hereda la disciplina MB: el proxy BO no se etiqueta Devengado.
    assert "Devengado" in bloque
    assert "proxy BO" in bloque


def test_bloque_declara_los_meses_vencidos_sin_ingesta():
    bloque = build_presupuesto_system_block(_resumen())

    assert "meses vencidos sin ingesta" in bloque
    assert "ene" in bloque


def test_bloque_con_periodo_vacio_no_explota():
    bloque = build_presupuesto_system_block(_resumen(periodo={}))

    assert "RESUMEN DE EJECUCIÓN PRESUPUESTARIA" in bloque


# ------------------------------------------------------------------ data_context


def test_public_resumen_esconde_los_internos():
    publico = public_resumen(_resumen())

    assert "_por_organismo" not in publico
    assert publico["monto_vigente_total"] == 100.0


def test_top_organismos_ordena_desc_y_limita():
    def org(nombre, total, count):
        return SimpleNamespace(
            organismo=nombre, monto_total=total, monto_compromiso=total / 10,
            monto_ejecucion=total / 100, monto_vigente=total * 2,
            pct_ejecucion=0.5, pct_compromiso=5.0, count=count,
        )

    orgs = [org("B", 50_000_000.0, 2), org("A", 900_000_000.0, 4), org("C", 1_000_000.0, 1)]
    top = PresupuestoTools.top_organismos({"por_organismo": None, "_por_organismo": orgs}, limit=2)

    assert [o["organismo"] for o in top] == ["A", "B"]
    # ARS → millones, que es la unidad de la UI.
    assert top[0]["monto_publicado"] == 900.0
    assert top[0]["actos"] == 4


def test_top_organismos_convierte_a_millones():
    org = SimpleNamespace(
        organismo="A", monto_total=3_000_000_000.0, monto_compromiso=0.0,
        monto_ejecucion=0.0, monto_vigente=0.0, pct_ejecucion=None,
        pct_compromiso=None, count=1,
    )
    top = PresupuestoTools.top_organismos({"por_organismo": None, "_por_organismo": [org]})

    assert top[0]["monto_publicado"] == 3000.0


def test_top_organismos_tolera_resumen_vacio():
    assert PresupuestoTools.top_organismos({"por_organismo": None}) == []


# ---------------------------------------------------------------- mensajes IA


@pytest.fixture
def agent():
    from agents.insight_reporting.agent import InsightReportingAgent

    return InsightReportingAgent()


def test_mensajes_ponen_el_bloque_en_system_no_en_el_user(agent):
    bloque = build_presupuesto_system_block(_resumen())
    mensajes = agent._build_messages("¿cuánto se ejecutó?", {"statistics": {}}, system_block=bloque)

    system = next(m for m in mensajes if m["role"] == "system")
    user = mensajes[-1]

    assert "RESUMEN DE EJECUCIÓN PRESUPUESTARIA" in system["content"]
    # El resumen es contexto estable: no viaja concatenado a la query.
    assert "RESUMEN DE EJECUCIÓN PRESUPUESTARIA" not in user["content"]
    assert "Contexto adicional" in user["content"]


def test_mensajes_sin_bloque_conservan_el_rol_de_transparencia(agent):
    mensajes = agent._build_messages("mostrame red flags", None)

    system = mensajes[0]
    assert system["role"] == "system"
    assert "transparencia" in system["content"]


def test_mensajes_sin_bloque_no_inyectan_resumen(agent):
    mensajes = agent._build_messages("hola", None)

    assert "RESUMEN DE EJECUCIÓN" not in mensajes[0]["content"]


def test_mensajes_piden_formato_de_burbuja_no_de_documento(agent):
    """La respuesta se lee en una burbuja angosta: sin encabezados ni citas."""
    mensajes = agent._build_messages("¿cuánto se ejecutó?", None)

    system = next(m for m in mensajes if m["role"] == "system")["content"]
    assert "burbuja de chat" in system
    assert "encabezados" in system
    assert "bloques de cita" in system


def test_mensajes_incluyen_el_historial(agent):
    agent.conversation_history = [
        {"role": "user", "content": "anterior"},
        {"role": "assistant", "content": "respuesta"},
    ]
    mensajes = agent._build_messages("nueva", None)

    assert mensajes[1]["content"] == "anterior"
    assert mensajes[-1]["content"] == "nueva"


# ------------------------------------------------- integración con la DB real
#
# El wrapper lee de las mismas tablas que el endpoint, así que se ejercita
# contra un SQLite en memoria y no con mocks: lo que puede romperse en
# producción es el join / el nombre de un campo, no la aritmética.

EJERCICIO = 2026


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
    """Dos organismos con Ley, tres actos canónicos y un duplicado."""
    from app.db.models import Boletin, EjecucionPresupuestaria, PresupuestoBase

    db.add_all([
        PresupuestoBase(
            id=1, ejercicio=EJERCICIO, organismo="MINISTERIO DE SALUD",
            partida_presupuestaria="3.1.2", monto_inicial=1_000_000_000.0,
            monto_vigente=1_000_000_000.0,
        ),
        PresupuestoBase(
            id=2, ejercicio=EJERCICIO, organismo="MINISTERIO DE EDUCACION",
            partida_presupuestaria="3.1.2", monto_inicial=500_000_000.0,
            monto_vigente=500_000_000.0,
        ),
    ])
    db.add_all([
        EjecucionPresupuestaria(
            presupuesto_base_id=1, organismo="MINISTERIO DE SALUD",
            fecha_boletin=date(2026, 9, 3), etapa_gasto="adjudicacion",
            monto=100_000_000.0, is_duplicate=0,
        ),
        EjecucionPresupuestaria(
            presupuesto_base_id=1, organismo="MINISTERIO DE SALUD",
            fecha_boletin=date(2026, 9, 10), etapa_gasto="pago",
            monto=20_000_000.0, is_duplicate=0,
        ),
        EjecucionPresupuestaria(
            presupuesto_base_id=2, organismo="MINISTERIO DE EDUCACION",
            fecha_boletin=date(2026, 9, 5), etapa_gasto="llamado",
            monto=30_000_000.0, is_duplicate=0,
        ),
        # Republicación del mismo acto: no puede entrar en el canónico.
        EjecucionPresupuestaria(
            presupuesto_base_id=1, organismo="MINISTERIO DE SALUD",
            fecha_boletin=date(2026, 9, 3), etapa_gasto="adjudicacion",
            monto=999_000_000.0, is_duplicate=1,
        ),
    ])
    db.add_all([
        Boletin(id=i, filename=f"2026090{i}_4_Secc.pdf", date=f"2026090{i}",
                section="4", status="completed")
        for i in (3, 5)
    ])
    await db.commit()


async def test_resumen_lee_los_montos_y_excluye_duplicados(session):
    await _seed(session)

    resumen = await PresupuestoTools.get_ejecucion_resumen(session, ejercicio=EJERCICIO)

    assert resumen is not None
    assert resumen["unidad"] == "millones de ARS"
    assert resumen["monto_vigente_total"] == 1500.0
    # 100 + 20 + 30, sin la republicación de 999.
    assert resumen["monto_publicado_total"] == 150.0
    assert resumen["monto_ejecucion_pagos"] == 20.0
    assert resumen["actos_publicados"] == 3
    assert resumen["pct_ejecucion_sobre_vigente"] == 1.33
    assert resumen["periodo"]["mes_desde"] == "2026-09"
    assert resumen["periodo"]["mes_hasta"] == "2026-09"


async def test_resumen_alimenta_los_chips(session):
    await _seed(session)

    resumen = await PresupuestoTools.get_ejecucion_resumen(session, ejercicio=EJERCICIO)

    # (b) organismos: el mayor gasto publicado primero.
    top = PresupuestoTools.top_organismos(resumen, limit=5)
    assert top[0]["organismo"] == "MINISTERIO DE SALUD"
    assert top[0]["monto_publicado"] == 120.0

    # (a) resumen: el bloque del prompt sale con los montos de la fuente.
    publico = public_resumen(resumen)
    assert "_por_organismo" not in publico
    bloque = build_presupuesto_system_block(resumen)
    assert "1500.0" in bloque and "150.0" in bloque


async def test_resumen_sin_ley_ni_ejecucion_devuelve_none(session):
    """Sin datos, el wrapper devuelve None: el prompt declara el hueco."""
    assert await PresupuestoTools.get_ejecucion_resumen(session, ejercicio=EJERCICIO) is None
    # Y con None el bloque no inventa cifras.
    assert "NO inventes" in build_presupuesto_system_block(None)


async def test_top_organismos_no_inventa_denominador(session):
    """Un organismo que publicó pero no está en la Ley no recibe un % falso."""
    await _seed(session)

    resumen = await PresupuestoTools.get_ejecucion_resumen(session, ejercicio=EJERCICIO)
    educacion = next(
        o for o in PresupuestoTools.top_organismos(resumen, limit=5)
        if o["organismo"] == "MINISTERIO DE EDUCACION"
    )
    assert educacion["monto_publicado"] == 30.0
    assert educacion["monto_vigente"] == 500.0
    assert educacion["pct_ejecucion"] == 0.0


async def test_finalidades_chip_c(session):
    """(c) finalidades: techo de la Ley contra lo publicado, con su unidad."""
    await _seed(session)

    finalidades = await PresupuestoTools.get_finalidades_desvio(session, ejercicio=EJERCICIO)

    assert finalidades is not None
    assert finalidades["unidad"] == "millones de ARS"
    # El techo de los dos organismos cae en la finalidad 3.1.2 (Servicios Sociales).
    con_techo = [f for f in finalidades["finalidades"] if f["monto_techo"]]
    assert sum(f["monto_techo"] for f in con_techo) == 1500.0
    # Y lo publicado del ledger queda contrastado contra ese techo.
    publicado = sum(f["monto_publicado_bo"] or 0.0 for f in finalidades["finalidades"])
    assert publicado == 150.0


async def test_finalidades_sin_ley_devuelve_none(session):
    assert await PresupuestoTools.get_finalidades_desvio(session, ejercicio=EJERCICIO) is None


# ------------------------------------------------- query_with_data (el contrato)
#
# Lo que la historia pide es el JSON de `query_with_data`: que `data_used` refleje
# las keys de presupuesto.  Se corre el método real contra el SQLite en memoria,
# inyectando la sesión por el mismo nombre que usa el módulo.


class _SessionCtx:
    def __init__(self, db):
        self._db = db

    async def __aenter__(self):
        return self._db

    async def __aexit__(self, *exc):
        return False


@pytest.fixture
def wired_agent(monkeypatch, session):
    """Agente con la sesión sembrada detrás de `AsyncSessionLocal`."""
    from agents.insight_reporting import agent as agent_module

    monkeypatch.setattr(agent_module, "AsyncSessionLocal", lambda: _SessionCtx(session))
    agente = agent_module.InsightReportingAgent()
    agente.model = None  # sin genai instalado: cae al fallback, y alcanza
    return agente


async def test_query_with_data_chip_a(session, wired_agent):
    await _seed(session)

    out = await wired_agent.query_with_data("¿Qué porcentaje del presupuesto vigente se ha ejecutado?")

    assert out["success"] is True
    assert "ejecucion_resumen" in out["data_used"]
    assert out["data_used"] == ["ejecucion_resumen"]


async def test_query_with_data_chip_b_no_pide_beneficiarios(session, wired_agent):
    await _seed(session)

    out = await wired_agent.query_with_data("¿Qué organismos concentran mayor gasto?")

    assert out["data_used"] == ["organismos"]
    # El conflicto de la nota: `organismo` ya no trae el análisis de entidades.
    assert "entities" not in out["data_used"]


async def test_query_with_data_chip_c(session, wired_agent):
    await _seed(session)

    out = await wired_agent.query_with_data("¿Qué finalidades presentan mayor desvío?")

    assert out["data_used"] == ["finalidades"]


async def test_query_with_data_transparencia_no_toca_presupuesto(session, wired_agent):
    await _seed(session)

    out = await wired_agent.query_with_data("mostrame los boletines con red flags")

    assert out["success"] is True
    assert not {"ejecucion_resumen", "organismos", "finalidades"} & set(out["data_used"])


async def test_query_with_data_sin_presupuesto_no_afirma_datos(session, wired_agent):
    """DB sin Ley ni ejecución: el JSON no lista una key de presupuesto vacía."""
    out = await wired_agent.query_with_data("¿Qué porcentaje del presupuesto vigente se ha ejecutado?")

    assert out["success"] is True
    assert "ejecucion_resumen" not in out["data_used"]


# ------------------------------------------------- (d) desglose por organismo
#
# La cuarta pregunta, la que faltaba.  El caso real: "desglosa los gastos de
# caminos de las sierras s.a." — un organismo sin fila en la Ley, al que las tres
# preguntas agregadas no pueden llegar.  Sin contexto, el agente afirmaba
# "0 documentos encontrados" sobre una empresa que sí tenía 55 millones publicados.


DETALLE = [
    "desglosa los gastos de caminos de las sierras s.a.",
    "desglosá los gastos de EPEC",
    "cómo se compone el gasto de la Secretaría de Infraestructura Hídrica",
    "detallame por etapa lo que gastó la ACIF",
]


@pytest.mark.parametrize("frase", DETALLE)
def test_pedido_de_desglose_enruta(frase):
    assert INTENT_ORGANISMO_DETALLE in detect_presupuesto_intents(frase)


def test_desglose_sin_senal_de_gasto_no_enruta():
    """El verbo solo no basta: "desglosá la metodología" no es una pregunta de plata."""
    assert detect_presupuesto_intents("desglosá la metodología del cálculo") == set()


@pytest.mark.parametrize("frase,_intent", CHIPS)
def test_los_chips_no_se_ponen_en_modo_desglose(frase, _intent):
    assert INTENT_ORGANISMO_DETALLE not in detect_presupuesto_intents(frase)


def test_el_desglose_no_arrastra_el_agregado():
    """"...del ministerio de salud" trae "ministerio"+"gastos": la firma de (b)."""
    intents = detect_presupuesto_intents("desglosá los gastos del Ministerio de Salud")

    assert intents == {INTENT_ORGANISMO_DETALLE}


def test_resolver_une_la_sigla_con_el_nombre_completo():
    """Sin esto, el desglose de EPEC mostraría una fracción de su gasto."""
    canones = [
        canonical_organismo_name("EMPRESA PROVINCIAL DE ENERGIA DE CORDOBA S.A.U"),
        canonical_organismo_name("EPEC"),
    ]

    familia = resolver_familia_organismo("desglosá los gastos de EPEC", canones)

    assert familia == set(canones)


def test_resolver_une_las_grafias_de_un_mismo_organismo():
    canones = {
        canonical_organismo_name(g)
        for g in ("Caminos de las Sierras S.A.", "CAMINOS DE LAS SIERRAS S.A.", "CÁMINOS DE LAS SIERRAS S.A.")
    }

    familia = resolver_familia_organismo("desglosa los gastos de caminos de las sierras s.a.", canones)

    assert familia == canones


def test_resolver_acepta_un_nombre_parcial():
    """En el corpus es "Hídrica y Gasífera"; la gente pregunta "Hídrica"."""
    canon = canonical_organismo_name("SECRETARIA DE INFRAESTRUCTURA HIDRICA Y GASIFERA")

    familia = resolver_familia_organismo(
        "cómo se compone el gasto de la Secretaría de Infraestructura Hídrica", [canon]
    )

    assert familia == {canon}


def test_resolver_no_inventa_un_organismo():
    canon = canonical_organismo_name("MINISTERIO DE SALUD")

    assert resolver_familia_organismo("cuánto se ejecutó del presupuesto", [canon]) is None


def test_el_prompt_prohibe_afirmar_ausencias_que_no_consulto(agent):
    system = agent._build_messages("hola", None)[0]["content"]

    assert "Nunca afirmes que no hay datos" in system
    assert "pedí el nombre del organismo" in system


async def test_desglose_une_grafias_y_deja_afuera_los_duplicados(session):
    await _seed(session)
    # La misma organismo, escrita distinto: tiene que caer en el mismo desglose.
    from app.db.models import EjecucionPresupuestaria

    session.add(EjecucionPresupuestaria(
        presupuesto_base_id=1, organismo="Ministerio de Salud",
        fecha_boletin=date(2026, 9, 20), etapa_gasto="pago",
        monto=5_000_000.0, is_duplicate=0,
    ))
    await session.commit()

    d = await PresupuestoTools.get_organismo_desglose(
        session, "desglosá los gastos del Ministerio de Salud", ejercicio=EJERCICIO
    )

    assert d is not None
    assert d["organismo"] == "MINISTERIO DE SALUD"
    # 100 adjudicación + 20 pago + 5 de la otra grafía; la republicación de 999 no.
    assert d["monto_publicado"] == 125.0
    assert d["actos"] == 3
    assert "Ministerio de Salud" in d["grafias_unificadas"]
    assert {e["etapa"]: e["monto"] for e in d["por_etapa"]} == {"adjudicacion": 100.0, "pago": 25.0}
    assert d["monto_ejecucion_pagos"] == 25.0
    assert d["monto_vigente"] == 1000.0
    assert d["por_mes"] == [{"mes": "2026-09", "monto": 125.0, "actos": 3}]


async def test_desglose_devuelve_none_si_la_consulta_no_nombra_organismo(session):
    await _seed(session)

    assert await PresupuestoTools.get_organismo_desglose(
        session, "desglosá los gastos de la empresa esa que no figura", ejercicio=EJERCICIO
    ) is None


async def test_desglose_no_depende_de_la_ley(session):
    """Caminos de las Sierras no tiene fila en la Ley: el ledger alcanza igual."""
    await _seed(session)

    d = await PresupuestoTools.get_organismo_desglose(
        session, "desglosá los gastos del Ministerio de Educacion", ejercicio=EJERCICIO
    )

    assert d is not None
    assert d["monto_publicado"] == 30.0
    # Publicó contra un vigente que sí existe en la Ley.
    assert d["monto_vigente"] == 500.0


async def test_query_with_data_desglose(session, wired_agent):
    await _seed(session)

    out = await wired_agent.query_with_data("desglosá los gastos del Ministerio de Salud")

    assert out["data_used"] == ["organismo_desglose"]


async def test_query_with_data_desglose_sin_match_no_afirma_datos(session, wired_agent):
    """Sin organismo reconocido no se inyecta una key vacía: el prompt declara el hueco."""
    await _seed(session)

    out = await wired_agent.query_with_data("desglosá los gastos de la empresa esa que no figura")

    assert out["success"] is True
    assert "organismo_desglose" not in out["data_used"]
