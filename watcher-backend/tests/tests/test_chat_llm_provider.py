"""El chat contra un provider de lenguaje: el cableado, no la calidad.

`InsightReportingAgent` llamaba a `genai.GenerativeModel` directo —sin capa de
providers— así que sin `google-generativeai` instalado y sin API key `self.model`
quedaba en None y **cada** respuesta del chat era `_generate_fallback_response`.
El síntoma que vio el PO fue una burbuja contestando *"requiere configurar la API
de Google"* con las fuentes ya citadas: el routing andaba, la redacción no
existía.

Acá se mide que el agente use el provider (los roles llegan enteros, la respuesta
es la del modelo y no la enlatada), que un provider caído no se lleve el turno, y
que sin provider el mensaje diga la verdad en vez de mandar a arreglar lo que no
está roto.

Run from watcher-backend/:
    .venv/Scripts/python.exe -m pytest tests/tests/test_chat_llm_provider.py -v
"""

import sys
from pathlib import Path

import pytest

# `agents.*` vive en la raíz del backend, que pytest no agrega solo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Query del chip (b).  Enruta a `organismos` y no dispara ningún otro branch de
# `query_with_data` — ni estadísticas (no trae la palabra "resumen") ni entidades
# (`organismo` está, pero lo gana el intent de presupuesto).
PREGUNTA = "¿Qué organismos concentran mayor gasto?"

TEXTO_FALLBACK = "modelo de lenguaje"


class _SessionCtx:
    """Sesión que nunca se toca: `route_presupuesto` es el único que vería el `db`."""

    def __init__(self, db):
        self._db = db

    async def __aenter__(self):
        return self._db

    async def __aexit__(self, *exc):
        return False


class _ProviderFalso:
    """Provider de mentira: registra lo que le mandan y devuelve un texto fijo."""

    def __init__(self, respuesta: str = "respuesta del modelo", falla: bool = False):
        self.respuesta = respuesta
        self.falla = falla
        self.llamadas: list[dict] = []

    async def generate_chat(self, messages, temperature=0.7, max_tokens=2000):
        self.llamadas.append({
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        })
        if self.falla:
            raise RuntimeError("ollama no responde")
        return self.respuesta

    async def generate_text(self, prompt, temperature=0.7, max_tokens=2000, system_prompt=None):
        if self.falla:
            raise RuntimeError("ollama no responde")
        return self.respuesta


@pytest.fixture
def agente(monkeypatch):
    """Agente real con la sesión y el routing de presupuesto sustituidos.

    Se corta la búsqueda sobre el corpus: si no, el agente arma el
    `RetrievalService` real y el test termina leyendo el ChromaDB **de la
    máquina**.  Acá se mide el cableado del provider, no la recuperación.
    """
    from agents.insight_reporting import agent as agent_module

    async def _resumen_sin_leer_la_db(db):
        return None

    async def _route(db, query, resumen, intents=None):
        return {"organismos": [{"organismo": "MINISTERIO DE SALUD", "monto_publicado": 100.0}]}

    monkeypatch.setattr(agent_module, "AsyncSessionLocal", lambda: _SessionCtx(object()))
    monkeypatch.setattr(agent_module.PresupuestoTools, "get_ejecucion_resumen", _resumen_sin_leer_la_db)
    monkeypatch.setattr(agent_module, "route_presupuesto", _route)

    agente = agent_module.InsightReportingAgent()
    # Se corta la búsqueda sobre el corpus: el agente arma su propio
    # `RetrievalService` (con sesión) y el test terminaría leyendo el ChromaDB
    # **de la máquina** (`~/.watcher/chromadb`), así que `data_used` cambiaría
    # según lo que cada desarrollador tenga indexado.
    async def _sin_corpus(*_args, **_kwargs):
        return []

    monkeypatch.setattr(agent_module.InsightReportingAgent, "_buscar_en_corpus", _sin_corpus)
    return agente


# ------------------------------------------------------------------- cableado


async def test_la_respuesta_la_escribe_el_provider(agente):
    """El caso del bug: antes salía la enlatada aunque hubiera modelo disponible."""
    agente.provider = _ProviderFalso("El 34% del vigente está publicado.")

    out = await agente.query_with_data(PREGUNTA)

    assert out["success"] is True
    assert out["response"] == "El 34% del vigente está publicado."
    assert out["data_used"] == ["organismos"]


async def test_el_bloque_de_sistema_viaja_como_rol_y_no_pegado_a_la_query(agente):
    falso = _ProviderFalso()
    agente.provider = falso

    await agente.query_with_data(PREGUNTA)

    mensajes = falso.llamadas[0]["messages"]
    assert mensajes[0]["role"] == "system"
    assert "transparencia" in mensajes[0]["content"]
    assert mensajes[-1]["role"] == "user"
    assert PREGUNTA in mensajes[-1]["content"]
    assert "transparencia" not in mensajes[-1]["content"]


async def test_la_generacion_usa_la_config_del_agente(agente):
    falso = _ProviderFalso()
    agente.provider = falso

    await agente.query_with_data(PREGUNTA)

    assert falso.llamadas[0]["temperature"] == agente.config.temperature
    assert falso.llamadas[0]["max_tokens"] == agente.config.max_tokens


async def test_la_narrativa_de_reporte_tambien_pasa_por_el_provider(agente):
    """El otro camino que llamaba a genai directo: los reportes, no el chat."""
    agente.provider = _ProviderFalso("Resumen en prosa.")

    out = await agente.generate_summary({"results": []})

    assert out["narrative"] == "Resumen en prosa."


# ------------------------------------------------------------------ fallas


async def test_sin_provider_el_mensaje_no_culpa_a_google(agente):
    """El texto viejo mandaba a configurar Google, que ya no es lo que se usa.

    Un mensaje que manda al usuario a arreglar lo que no está roto cuesta más
    que no decir nada: el PO lo leyó como un problema de configuración cuando
    el problema era que el chat no tenía a quién preguntarle.
    """
    agente.provider = None

    out = await agente.query_with_data(PREGUNTA)

    assert out["success"] is True
    assert "Google" not in out["response"]
    assert TEXTO_FALLBACK in out["response"]
    # El hueco es de redacción, no de datos: la consulta se hizo igual.
    assert out["data_used"] == ["organismos"]


async def test_un_provider_caido_no_se_lleva_el_turno(agente):
    agente.provider = _ProviderFalso(falla=True)

    out = await agente.query_with_data(PREGUNTA)

    assert out["success"] is True
    assert TEXTO_FALLBACK in out["response"]
    # El turno se cierra igual: una respuesta degradada sigue siendo respuesta.
    assert [m["role"] for m in agente.conversation_history] == ["user", "assistant"]
