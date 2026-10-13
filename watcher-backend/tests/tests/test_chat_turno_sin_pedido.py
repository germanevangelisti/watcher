"""El turno que no pide nada: no consulta, no cita y no llama al modelo.

El 2026-10-01, después de *"desglosá los actos de Caminos de las Sierras de abril de
2026"*, el usuario escribió **"gracias"** y el chat volvió a contestar la pregunta
anterior: *"No encontré información específica sobre actos de Caminos de las Sierras
S.A. en abril de 2026…"*, con `Fuentes: Búsqueda semántica`.

No fue el modelo. Fue el pipeline:

- `agent.py` buscaba en el corpus **siempre**, y `search_bm25("gracias")` devuelve
  boletines que contienen esa palabra: `fragmentos` quedaba lleno, el bloque de
  ausencia de F4 —que existe justamente para este caso— **no** se emitía, y al
  modelo le llegaban ~2,9 KB de fragmentos que no eran de nada.
- con los últimos 3 turnos en el prompt, la pregunta anterior seguía ahí, así que el
  modelo la contestó con un contexto que no la cubría.

Acá se fija el corte: un turno de cortesía se contesta **antes** de abrir la base, no
consulta ninguna fuente (`data_used` vacío, sin burbuja de fuentes) y no despierta al
modelo.  Y se fija lo que **no** puede cortar: el vocabulario es cerrado, así que un
seguimiento real (*"gracias, ¿y el total?"*) sigue el camino normal.

Run from watcher-backend/:
    .venv/Scripts/python.exe -m pytest tests/tests/test_chat_turno_sin_pedido.py -v
"""

import sys
from pathlib import Path

import pytest

# `agents.*` vive en la raíz del backend, que pytest no agrega solo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.insight_reporting import agent as agent_module  # noqa: E402
from agents.insight_reporting.agent import (  # noqa: E402
    _RESPUESTA_CORTESIA,
    _RESPUESTA_SALUDO,
    respuesta_si_es_turno_sin_pedido,
)

# El turno exacto del bug.
GRACIAS = "gracias"
# El turno anterior, que el chat volvió a contestar.
PREGUNTA_ANTERIOR = "desglosá los actos de Caminos de las Sierras de abril de 2026"
RESPUESTA_ANTERIOR = "SAP 334,43 millones (boletín 257); ZONA G 1,5 millones (boletín 252)."


class _ProviderFalso:
    """Registra si lo llamaron y con qué mensajes."""

    def __init__(self):
        self.llamado = False
        self.mensajes: list[dict] = []

    async def generate_chat(self, messages, temperature=0.7, max_tokens=2000):
        self.llamado = True
        self.mensajes = messages
        return "no lo encontré en el corpus"


def _base_que_explota(*_args, **_kwargs):
    """Si el turno de cortesía abre la base, el test tiene que fallar."""
    raise AssertionError("un turno de cortesía no abre la base")


def _agente(provider=None):
    agente = agent_module.InsightReportingAgent()
    agente.provider = provider or _ProviderFalso()
    return agente


# ------------------------------------------------------------- el detector (puro)


@pytest.mark.parametrize("query", [
    "gracias",
    "¡Gracias!",
    "GRACIAS",
    "Muchas gracias",
    "Muchísimas gracias por todo",
    "gracias, muy amable",
    "mil gracias",
    "ok",
    "dale, listo",
    "perfecto",
    "no, gracias",
    "chau",
])
def test_un_turno_de_cortesia_se_reconoce(query):
    assert respuesta_si_es_turno_sin_pedido(query) == _RESPUESTA_CORTESIA


@pytest.mark.parametrize("query", ["hola", "Hola!", "buenas", "buenos días", "qué tal"])
def test_un_saludo_se_reconoce(query):
    assert respuesta_si_es_turno_sin_pedido(query) == _RESPUESTA_SALUDO


@pytest.mark.parametrize("query", [
    # La pregunta del bug y sus vecinas: tienen que seguir el camino normal.
    "¿qué se publicó sobre obra pública en septiembre?",
    "¿qué finalidades presentan mayor desvío?",
    "¿y el total?",
    # Un seguimiento corto: pocas palabras, pero pide un dato.
    "gracias, ¿y en octubre?",
    "ok, pero ¿cuánto gastó Caminos?",
    "y eso?",
    "¿qué?",
    "¿cuántos actos hay?",
])
def test_un_turno_con_pedido_no_entra_al_corte(query):
    assert respuesta_si_es_turno_sin_pedido(query) is None


def test_un_seguimiento_de_puras_palabras_vacias_no_se_corta():
    """*"de la que se"* no tiene marcador: sólo se corta con uno, no por ser corto."""
    assert respuesta_si_es_turno_sin_pedido("de la que se") is None


@pytest.mark.parametrize("query", ["", "   ", "?", "!!!", "2026"])
def test_un_turno_vacio_tampoco_entra(query):
    """"No es de cortesía" ≠ "no hay respuesta": el camino normal decide."""
    assert respuesta_si_es_turno_sin_pedido(query) is None


# ------------------------------------------------- el turno, contra el agente


async def test_el_gracias_no_toca_la_base_ni_le_devuelve_el_turno_anterior(monkeypatch):
    """El repro del bug, de punta a punta.

    El historial ya tiene la pregunta de Caminos, el usuario escribe "gracias", y
    antes de este corte el modelo recibía esa pregunta con fragmentos de boletines
    que sólo contenían la palabra.  Ahora no hay consulta —la base ni se abre— y el
    modelo no se despierta.
    """
    monkeypatch.setattr(agent_module, "AsyncSessionLocal", _base_que_explota)

    agente = _agente()
    agente.conversation_history = [
        {"role": "user", "content": PREGUNTA_ANTERIOR},
        {"role": "assistant", "content": RESPUESTA_ANTERIOR},
    ]

    out = await agente.query_with_data(GRACIAS)

    assert out["success"] is True
    assert out["response"] == _RESPUESTA_CORTESIA
    # Sin fuente consultada, la burbuja no cita ninguna.
    assert out["data_used"] == []
    # Y el modelo no vio ni la pregunta anterior ni fragmentos basura.
    assert agente.provider.llamado is False
    # La respuesta tampoco reabre la pregunta anterior.
    assert "Caminos" not in out["response"]


async def test_el_saludo_contesta_el_saludo(monkeypatch):
    monkeypatch.setattr(agent_module, "AsyncSessionLocal", _base_que_explota)
    agente = _agente()

    out = await agente.query_with_data("hola")

    assert out["response"] == _RESPUESTA_SALUDO
    assert out["data_used"] == []
    assert agente.provider.llamado is False


async def test_el_turno_corto_queda_en_el_historial(monkeypatch):
    """Para que el turno siguiente —*"¿y eso?"*— tenga de qué agarrarse."""
    monkeypatch.setattr(agent_module, "AsyncSessionLocal", _base_que_explota)
    agente = _agente()

    await agente.query_with_data(GRACIAS)

    assert [m["role"] for m in agente.conversation_history] == ["user", "assistant"]
    assert agente.conversation_history[0]["content"] == GRACIAS


async def test_una_pregunta_de_verdad_si_consulta(monkeypatch):
    """El corte no puede comerse el camino normal: la pregunta del bug consulta."""
    abierta: list[bool] = []

    class _SesionCtx:
        async def __aenter__(self):
            abierta.append(True)
            return None

        async def __aexit__(self, *exc):
            return False

    async def _sin_corpus(*_args, **_kwargs):
        return []

    async def _resumen(*_args, **_kwargs):
        return None

    async def _route(*_args, **_kwargs):
        return {}

    async def _stats(*_args, **_kwargs):
        return {"documentos": 0}

    monkeypatch.setattr(agent_module, "AsyncSessionLocal", lambda: _SesionCtx())
    monkeypatch.setattr(agent_module.PresupuestoTools, "get_ejecucion_resumen", _resumen)
    monkeypatch.setattr(agent_module, "route_presupuesto", _route)
    monkeypatch.setattr(agent_module.DatabaseTools, "get_statistics", _stats)
    monkeypatch.setattr(agent_module.InsightReportingAgent, "_buscar_en_corpus", _sin_corpus)

    agente = _agente()

    out = await agente.query_with_data("¿qué se publicó sobre obra pública en septiembre?")

    assert abierta == [True]
    assert agente.provider.llamado is True
    assert out["data_used"] != []
