"""Tests de memoria de turnos en el path de chat (`story-watcher-chat-turn-memory`).

El bug que fija esta suite es asimétrico y silencioso: `answer_query` escribía
`conversation_history`, pero `query_with_data` —el **único** path que usa el chat
del FE— no. Como `_generate_ai_response` sí lee los últimos turnos, el historial
del servidor quedaba vacío en la práctica: el agente nunca recordaba nada.

Lo que se ejercita acá es el agente real contra un SQLite en memoria (sesión
inyectada por el nombre que usa el módulo, mismo idioma que
`test_chat_presupuesto.py`), más el endpoint `POST /agents/chat/clear` montado en
una app mínima — sin bootear `app.main`, que traería startup events y settings.

Run from watcher-backend/:
    .venv/Scripts/python.exe -m pytest tests/tests/test_chat_turn_memory.py -v
"""

import sys
from datetime import date
from pathlib import Path

import httpx
import pytest
import pytest_asyncio

# `agents.*` vive en la raíz del backend, que pytest no agrega solo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

EJERCICIO = 2026

# Query real del chip (b): enruta a `organismos`, que es un intent de presupuesto.
PREGUNTA_1 = "¿Qué organismos concentran mayor gasto?"
# Referencia al turno anterior: sin memoria, esto no se puede resolver.
PREGUNTA_2 = "¿y el mes anterior?"


# --------------------------------------------------------------------- fixtures


class _SessionCtx:
    """Sesión inyectada donde el módulo espera `AsyncSessionLocal`."""

    def __init__(self, db):
        self._db = db

    async def __aenter__(self):
        return self._db

    async def __aexit__(self, *exc):
        return False


class _SessionRota:
    """Igual, pero explota al entrar: fuerza el camino de error del agente."""

    async def __aenter__(self):
        raise RuntimeError("DB caída")

    async def __aexit__(self, *exc):
        return False


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


def _apariciones(mensajes, texto):
    """Cuenta el texto dentro de los mensajes (substring, no igualdad exacta).

    El último mensaje lleva el contexto de datos concatenado a la query, así que
    comparar por igualdad daría 0 para la query del turno actual.
    """
    return sum(m["content"].count(texto) for m in mensajes)


def _capturar_mensajes(agente, capturado, respuesta="ok"):
    """Espía el prompt real del turno: guarda lo que `_build_messages` arma.

    Hace falta un `provider` truthy: con `provider=None` el agente ni siquiera
    llama a `_generate_ai_response` (cae al fallback sin IA), y el espía no
    vería nada.

    Devuelve `(texto, del_modelo)` como el original: el segundo valor es el que
    permite declarar en la burbuja quién escribió la respuesta, y un espía que
    devolviera sólo el texto haría fallar el desempaquetado en `query_with_data`.
    """
    agente.provider = object()

    async def _capturar(query, context=None, system_block=None, provider=None):
        capturado["mensajes"] = agente._build_messages(query, context, system_block)
        return respuesta, True

    agente._generate_ai_response = _capturar


async def _seed(db):
    from app.db.models import EjecucionPresupuestaria, PresupuestoBase

    db.add(PresupuestoBase(
        id=1, ejercicio=EJERCICIO, organismo="MINISTERIO DE SALUD",
        partida_presupuestaria="3.1.2", monto_inicial=1_000_000_000.0,
        monto_vigente=1_000_000_000.0,
    ))
    db.add(EjecucionPresupuestaria(
        presupuesto_base_id=1, organismo="MINISTERIO DE SALUD",
        fecha_boletin=date(2026, 9, 3), etapa_gasto="adjudicacion",
        monto=100_000_000.0, is_duplicate=0,
    ))
    await db.commit()


@pytest.fixture
def agent_module():
    import agents.insight_reporting.agent as mod

    return mod


@pytest.fixture
def wired_agent(monkeypatch, session, agent_module):
    """Agente real con la sesión sembrada detrás de `AsyncSessionLocal`.

    Se corta la búsqueda sobre el corpus: si no, el agente arma el
    `RetrievalService` real y el test termina leyendo el ChromaDB **de la máquina**
    (`~/.watcher/chromadb`).  Acá se mide la memoria de turnos, no la recuperación.
    """
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


# ------------------------------------------------------------------ memoria BE


async def test_query_with_data_recuerda_el_turno(session, wired_agent):
    """El turno se cierra con user + assistant, en ese orden."""
    await _seed(session)

    out = await wired_agent.query_with_data(PREGUNTA_1)

    assert out["success"] is True
    assert [m["role"] for m in wired_agent.conversation_history] == ["user", "assistant"]
    assert wired_agent.conversation_history[0]["content"] == PREGUNTA_1
    assert wired_agent.conversation_history[1]["content"] == out["response"]


async def test_el_segundo_turno_ve_el_primero(session, wired_agent):
    """El criterio de la historia: "y el mes anterior" viaja con el turno previo."""
    await _seed(session)
    primero = await wired_agent.query_with_data(PREGUNTA_1)

    capturado = {}
    _capturar_mensajes(wired_agent, capturado, "respuesta del segundo turno")
    await wired_agent.query_with_data(PREGUNTA_2)

    mensajes = capturado["mensajes"]
    # Los dos roles del turno anterior llegaron al modelo, verbatim...
    assert {"role": "user", "content": PREGUNTA_1} in mensajes
    assert {"role": "assistant", "content": primero["response"]} in mensajes
    # ...y el turno actual sigue siendo el último mensaje. El contexto de datos
    # viaja concatenado a la query, así que el mensaje *empieza* con ella.
    assert mensajes[-1]["role"] == "user"
    assert mensajes[-1]["content"].startswith(PREGUNTA_2)
    assert _apariciones(mensajes, PREGUNTA_2) == 1


async def test_la_query_actual_no_se_duplica_en_el_prompt(session, wired_agent):
    """Se appendea después de generar: en el turno 1 el historial va vacío al modelo."""
    await _seed(session)

    capturado = {}
    _capturar_mensajes(wired_agent, capturado)

    await wired_agent.query_with_data(PREGUNTA_1)

    assert _apariciones(capturado["mensajes"], PREGUNTA_1) == 1


async def test_el_historial_se_recorta_a_max_conversation_history(session, wired_agent):
    """El límite se cuenta en turnos (pares): lo viejo se va, lo reciente queda."""
    await _seed(session)
    wired_agent.config.max_conversation_history = 2

    for _ in range(3):
        await wired_agent.query_with_data(PREGUNTA_1)

    assert len(wired_agent.conversation_history) == 4  # 2 turnos
    assert [m["role"] for m in wired_agent.conversation_history] == [
        "user", "assistant", "user", "assistant",
    ]
    # El primer turno se recortó: lo que sobrevive son los dos últimos.
    assert wired_agent.conversation_history[0]["role"] == "user"


async def test_una_query_fallida_no_deja_un_turno_a_medias(monkeypatch, agent_module):
    """Sin respuesta no hay turno: nunca un user colgado en el historial."""
    monkeypatch.setattr(agent_module, "AsyncSessionLocal", lambda: _SessionRota())
    agente = agent_module.InsightReportingAgent()
    agente.provider = None

    out = await agente.query_with_data(PREGUNTA_1)

    assert out["success"] is False
    assert agente.conversation_history == []


# ----------------------------------------------------------------- clear (BE)


async def test_clear_borra_el_historial_y_es_idempotente(session, wired_agent):
    await _seed(session)
    await wired_agent.query_with_data(PREGUNTA_1)

    assert wired_agent.clear_conversation() == 2
    assert wired_agent.conversation_history == []
    # Sobre un historial ya vacío no falla: es un no-op con contrato.
    assert wired_agent.clear_conversation() == 0


async def test_clear_corta_la_memoria_del_turno_siguiente(session, wired_agent):
    """Después del clear, el turno siguiente no arrastra el anterior."""
    await _seed(session)
    await wired_agent.query_with_data(PREGUNTA_1)
    wired_agent.clear_conversation()

    capturado = {}
    _capturar_mensajes(wired_agent, capturado)

    await wired_agent.query_with_data(PREGUNTA_2)

    assert _apariciones(capturado["mensajes"], PREGUNTA_1) == 0


# ------------------------------------------------------------------- endpoint


@pytest_asyncio.fixture
async def client():
    """App mínima con sólo el router de agentes (sin `app.main`)."""
    from app.api.v1.endpoints import agents as agents_endpoint
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(agents_endpoint.router, prefix="/agents")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c, agents_endpoint.insight_agent


async def test_endpoint_clear_responde_y_reporta_cuantos_borro(client):
    c, agente = client
    agente.conversation_history = [
        {"role": "user", "content": "a"},
        {"role": "assistant", "content": "b"},
    ]

    r = await c.post("/agents/chat/clear")

    assert r.status_code == 200
    assert r.json()["cleared"] == 2
    assert agente.conversation_history == []


async def test_endpoint_clear_es_idempotente(client):
    c, agente = client
    agente.conversation_history = []

    primera = await c.post("/agents/chat/clear")
    segunda = await c.post("/agents/chat/clear")

    assert primera.status_code == segunda.status_code == 200
    assert primera.json()["cleared"] == segunda.json()["cleared"] == 0
