"""El selector de proveedor del chat (`story-watcher-chat-llm-selector`).

Lo que fija esta suite es una decisión, no una pantalla: **elegir un proveedor
para comparar calidad no puede terminar en otro proveedor**.  El chat tenía una
regla correcta para su caso —si lo configurado no se puede construir, se cae a
Ollama y se loguea fuerte, porque un turno de usuario no puede tumbar el
backend—, pero esa misma regla aplicada a una elección explícita es peor que un
error: alguien que elige Gemini y recibe Ollama compara Ollama contra Ollama y
concluye algo falso sobre Gemini.  De ahí que `build_provider()` levante y
`resolve_llm_provider()` siga sin levantar.

También fija lo que la burbuja declara: con qué proveedor se redactó cada
respuesta, y `None` cuando no la redactó un modelo (el texto de cortesía y el de
fallback salen por el mismo camino que una respuesta real).

Run from watcher-backend/:
    .venv/Scripts/python.exe -m pytest tests/tests/test_chat_llm_provider_selector.py -v
"""

import sys
from pathlib import Path

import httpx
import pytest
import pytest_asyncio

# `agents.*` vive en la raíz del backend, que pytest no agrega solo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.services import llm_provider as lp  # noqa: E402

# Un puerto donde nadie escucha: la sonda del servidor local tiene que fallar
# rápido y sin tocar el Ollama de la máquina de quien corre los tests.
SIN_SERVIDOR = "http://127.0.0.1:1"

PREGUNTA = "¿Qué organismos concentran mayor gasto?"


# --------------------------------------------------------------------- dobles


class _ProviderFalso:
    """Provider que no redacta: registra y devuelve un texto reconocible."""

    provider_id = "falso"
    model_name = "modelo-falso"

    def __init__(self, falla: bool = False):
        self.falla = falla
        self.llamados = 0

    async def generate_chat(self, messages, temperature=0.7, max_tokens=2000):
        self.llamados += 1
        if self.falla:
            raise RuntimeError("el modelo se cayó")
        return "respuesta del doble"

    async def generate_text(self, *args, **kwargs):
        return "texto del doble"


class _SessionCtx:
    """Sesión inyectada donde el módulo espera `AsyncSessionLocal`."""

    def __init__(self, db):
        self._db = db

    async def __aenter__(self):
        return self._db

    async def __aexit__(self, *exc):
        return False


# ------------------------------------------------------------------- fixtures


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


@pytest.fixture
def agent_module():
    import agents.insight_reporting.agent as mod

    return mod


@pytest.fixture
def wired_agent(monkeypatch, session, agent_module):
    """Agente real con la base sembrada detrás y la búsqueda del corpus cortada.

    Sin el corte, `_buscar_en_corpus` abriría el ChromaDB **de la máquina** y el
    test mediría lo que cada quien tenga indexado en vez del proveedor del turno.
    """
    monkeypatch.setattr(agent_module, "AsyncSessionLocal", lambda: _SessionCtx(session))
    agente = agent_module.InsightReportingAgent()

    async def _sin_corpus(*args, **kwargs):
        return {"ejecutada": False, "resultados": 0, "motivo": "cortado en el test"}

    monkeypatch.setattr(
        agent_module.InsightReportingAgent, "_contexto_de_corpus", _sin_corpus
    )
    agente.provider = _ProviderFalso()
    return agente


@pytest_asyncio.fixture
async def client():
    """App mínima con sólo el router de agentes (sin `app.main`)."""
    from app.api.v1.endpoints import agents as agents_endpoint
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(agents_endpoint.router, prefix="/agents")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c, agents_endpoint


# ------------------------------------------------------- el catálogo (lo que se puede usar)


async def test_el_catalogo_ofrece_los_tres_y_arranca_por_el_local(monkeypatch):
    """Orden deliberado: primero el local, que es la dirección del producto."""
    monkeypatch.setenv("OLLAMA_BASE_URL", SIN_SERVIDOR)

    ids = [p["id"] for p in await lp.provider_catalog()]

    assert ids == ["ollama", "google", "anthropic"]


async def test_el_catalogo_dice_que_le_falta_a_cada_uno(monkeypatch):
    """Un selector no puede ofrecer opciones que fallan: dice el motivo.

    Es la misma regla de honestidad que el chat aplica a los datos, aplicada a
    la configuración: "no se pudo" sin decir por qué obliga a leer el log.
    """
    monkeypatch.setenv("OLLAMA_BASE_URL", SIN_SERVIDOR)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "una-key-de-mentira")

    por_id = {p["id"]: p for p in await lp.provider_catalog()}

    assert "ANTHROPIC_API_KEY" in por_id["anthropic"]["reason"]
    assert por_id["anthropic"]["available"] is False

    assert por_id["google"]["available"] is True
    # Disponible, pero remoto: elegirlo manda el contexto de los boletines afuera.
    assert por_id["google"]["local"] is False
    assert "sale de la máquina" in por_id["google"]["reason"]


async def test_el_catalogo_marca_el_local_indisponible_si_el_servidor_no_responde(
    monkeypatch,
):
    """`OllamaProvider` no hace I/O al construirse, así que sin la sonda el
    catálogo diría "disponible" con el servidor apagado y el usuario se
    enteraría al mandar el mensaje."""
    monkeypatch.setenv("OLLAMA_BASE_URL", SIN_SERVIDOR)

    ollama = (await lp.provider_catalog())[0]

    assert ollama["available"] is False
    assert SIN_SERVIDOR in ollama["reason"]


async def test_el_catalogo_marca_el_local_indisponible_si_falta_el_modelo(
    monkeypatch, agent_module
):
    """Servidor arriba pero sin el modelo pedido tampoco sirve para chatear."""
    monkeypatch.setenv("OLLAMA_MODEL", "un-modelo-que-no-esta")

    async def _servidor_arriba(*args, **kwargs):
        return {
            "base_url": "http://127.0.0.1:11434",
            "responde": True,
            "modelos": ["qwen2.5:7b", "qwen2.5:14b"],
            "motivo": None,
        }

    monkeypatch.setattr(lp, "estado_de_ollama", _servidor_arriba)

    ollama = (await lp.provider_catalog())[0]

    assert ollama["available"] is False
    assert "un-modelo-que-no-esta" in ollama["reason"]
    # Los que sí están viajan igual: el FE puede ofrecer cambiarlo.
    assert ollama["models"] == ["qwen2.5:7b", "qwen2.5:14b"]


async def test_el_catalogo_nombra_el_paquete_que_falta(monkeypatch):
    """La rama que estuvo viva hasta que se instaló el SDK.

    Se fuerza con `find_spec` porque hoy los dos paquetes están instalados: la
    rama sigue existiendo y es la que ve quien clone el repo sin instalarlos.
    """
    import importlib.util

    real = importlib.util.find_spec
    monkeypatch.setattr(
        lp.importlib.util,
        "find_spec",
        lambda nombre: None if nombre == "anthropic" else real(nombre),
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "una-key-de-mentira")

    anthropic = {p["id"]: p for p in await lp.provider_catalog()}["anthropic"]

    assert anthropic["available"] is False
    # El nombre del paquete de pip, no el del módulo: es lo que hay que instalar.
    assert "anthropic" in anthropic["reason"]
    # Con el paquete ausente el motivo es el paquete, no la key (que sí está).
    assert "ANTHROPIC_API_KEY" not in anthropic["reason"]


# ------------------------------------------- la elección explícita (nunca cae a otro)


def test_build_provider_levanta_con_el_motivo_en_vez_de_caer_a_ollama(monkeypatch):
    """El corazón de la historia.

    `resolve_llm_provider()` cae a Ollama a propósito y está bien para el turno
    de alguien que no eligió nada.  Acá no: el usuario eligió Anthropic para
    compararlo, así que la única respuesta honesta es el motivo.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(ValueError) as exc:
        lp.build_provider("anthropic")

    assert "ANTHROPIC_API_KEY" in str(exc.value)


def test_build_provider_rechaza_un_id_desconocido_y_lista_los_validos(monkeypatch):
    with pytest.raises(ValueError) as exc:
        lp.build_provider("gpt-4")

    assert "gpt-4" in str(exc.value)
    for valido in ("ollama", "google", "anthropic"):
        assert valido in str(exc.value)


def test_build_provider_construye_el_local_con_el_modelo_pedido(monkeypatch):
    """El modelo es parte de lo que se elige: 7B y 14B son una comparación."""
    monkeypatch.setenv("OLLAMA_BASE_URL", SIN_SERVIDOR)

    provider = lp.build_provider("ollama", model="qwen2.5:14b")

    assert isinstance(provider, lp.OllamaProvider)
    assert provider.model_name == "qwen2.5:14b"
    assert provider.provider_id == "ollama"


def test_los_proveedores_se_saben_nombrar():
    """`provider_id` es lo que viaja al FE: sin él la burbuja no puede declarar."""
    assert lp.GoogleGeminiProvider.provider_id == "google"
    assert lp.AnthropicProvider.provider_id == "anthropic"
    assert lp.OllamaProvider.provider_id == "ollama"


# ------------------------------------------------- el default, dicho en voz alta


def test_configured_provider_cuenta_de_donde_sale_el_valor(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", SIN_SERVIDOR)
    monkeypatch.setenv("LLM_PROVIDER", "ollama")

    config = lp.configured_provider()

    assert config["provider"] == "ollama"
    assert config["fallback"] is False
    assert "LLM_PROVIDER=ollama" in config["origin"]


def test_configured_provider_avisa_cuando_lo_configurado_cae_a_local(monkeypatch):
    """El caso real de la máquina: `.env` dice google, no hay key disponible."""
    monkeypatch.setenv("LLM_PROVIDER", "google")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    config = lp.configured_provider()

    assert config["provider"] == "ollama"
    assert config["fallback"] is True
    assert config["requested"] == "google"
    assert "no sale nada de la máquina" in config["reason"]


def test_configured_provider_declara_que_no_hay_variable(monkeypatch):
    """`LLM_PROVIDER` sin definir es una decisión del código, no del usuario."""
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("OLLAMA_BASE_URL", SIN_SERVIDOR)

    config = lp.configured_provider()

    assert "no está definido" in config["origin"]


def test_configured_provider_explica_auto(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    monkeypatch.setenv("OLLAMA_BASE_URL", SIN_SERVIDOR)

    assert "local" in lp.configured_provider()["origin"]

    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    assert "google" in lp.configured_provider()["origin"]


# --------------------------------------------- el turno declara quién lo redactó


async def test_el_turno_declara_quien_lo_redacto(wired_agent):
    elegido = _ProviderFalso()

    out = await wired_agent.query_with_data(PREGUNTA, provider=elegido)

    assert out["llm"] == {"provider": "falso", "model": "modelo-falso"}


async def test_el_turno_usa_el_elegido_y_no_el_del_agente(wired_agent):
    """El proveedor del agente es el del entorno; el del turno es el elegido."""
    del_agente = wired_agent.provider
    elegido = _ProviderFalso()

    await wired_agent.query_with_data(PREGUNTA, provider=elegido)

    assert elegido.llamados == 1
    assert del_agente.llamados == 0


async def test_sin_eleccion_el_turno_usa_el_proveedor_del_agente(wired_agent):
    out = await wired_agent.query_with_data(PREGUNTA)

    assert out["llm"] == {"provider": "falso", "model": "modelo-falso"}
    assert wired_agent.provider.llamados == 1


async def test_si_el_modelo_falla_no_se_declara_ningun_proveedor(wired_agent):
    """Un fallo del modelo sale como texto de fallback por el mismo camino.

    Declarar ahí el proveedor elegido sería atribuirle una frase que no
    escribió: exactamente el dato falso que esta pantalla existe para no mostrar.
    """
    caido = _ProviderFalso(falla=True)

    out = await wired_agent.query_with_data(PREGUNTA, provider=caido)

    assert caido.llamados == 1
    assert out["llm"] is None
    assert "no hay un modelo" in out["response"]


async def test_un_turno_sin_pedido_no_declara_proveedor(wired_agent):
    """La cortesía la escribe el sistema: no hay modelo que acreditar."""
    out = await wired_agent.query_with_data("gracias")

    assert out["llm"] is None
    assert wired_agent.provider.llamados == 0


# ------------------------------------------------------------- el endpoint


async def test_el_endpoint_publica_el_catalogo_y_el_default(monkeypatch, client):
    monkeypatch.setenv("OLLAMA_BASE_URL", SIN_SERVIDOR)
    c, _ = client

    respuesta = await c.get("/agents/llm/providers")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert [p["id"] for p in cuerpo["providers"]] == ["ollama", "google", "anthropic"]
    assert set(cuerpo["configured"]) >= {"provider", "model", "origin", "fallback"}


async def test_el_endpoint_falla_con_400_y_el_motivo_si_no_puede_usar_lo_elegido(
    monkeypatch, client
):
    """400 y no 200-con-otro-modelo: el turno no se ejecuta."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    c, endpoint = client

    consultado = False

    async def _espia(*args, **kwargs):
        nonlocal consultado
        consultado = True
        return {"success": True}

    monkeypatch.setattr(endpoint.insight_agent, "query_with_data", _espia)

    respuesta = await c.post("/agents/chat", json={"query": "hola", "provider": "anthropic"})

    assert respuesta.status_code == 400
    assert "ANTHROPIC_API_KEY" in respuesta.json()["detail"]
    # Ni siquiera se consultó la base: si el proveedor no sirve, el turno no gasta.
    assert consultado is False


async def test_el_endpoint_le_pasa_al_agente_el_proveedor_elegido(monkeypatch, client):
    monkeypatch.setenv("GOOGLE_API_KEY", "una-key-de-mentira")
    c, endpoint = client

    visto = {}

    async def _espia(query, provider=None):
        visto["query"] = query
        visto["provider"] = provider
        return {"success": True, "llm": None}

    monkeypatch.setattr(endpoint.insight_agent, "query_with_data", _espia)

    respuesta = await c.post("/agents/chat", json={"query": "hola", "provider": "google"})

    assert respuesta.status_code == 200
    assert isinstance(visto["provider"], lp.GoogleGeminiProvider)
    assert visto["provider"].provider_id == "google"


async def test_el_endpoint_sin_provider_no_cambia_nada(monkeypatch, client):
    """El contrato viejo sigue andando: el FE puede no mandar `provider`."""
    c, endpoint = client

    visto = {}

    async def _espia(query, provider=None):
        visto["provider"] = provider
        return {"success": True, "llm": None}

    monkeypatch.setattr(endpoint.insight_agent, "query_with_data", _espia)

    respuesta = await c.post("/agents/chat", json={"query": "hola"})

    assert respuesta.status_code == 200
    assert visto["provider"] is None


async def test_el_endpoint_rechaza_un_modelo_local_que_no_esta_descargado(
    monkeypatch, client
):
    """Un modelo recordado en el navegador y borrado del servidor.

    Sin esto el turno falla en cada mensaje con un error de HTTP que no dice
    cuál es el problema.
    """
    c, endpoint = client

    async def _servidor_arriba(*args, **kwargs):
        return {
            "base_url": "http://127.0.0.1:11434",
            "responde": True,
            "modelos": ["qwen2.5:7b"],
            "motivo": None,
        }

    monkeypatch.setattr(endpoint, "estado_de_ollama", _servidor_arriba)

    respuesta = await c.post(
        "/agents/chat",
        json={"query": "hola", "provider": "ollama", "model": "qwen2.5:14b"},
    )

    assert respuesta.status_code == 400
    detalle = respuesta.json()["detail"]
    assert "qwen2.5:14b" in detalle
    # Los que sí están, para que el aviso sirva para elegir otro.
    assert "qwen2.5:7b" in detalle


async def test_el_endpoint_avisa_si_el_servidor_local_esta_apagado(monkeypatch, client):
    """La otra mitad del mismo caso: sin servidor, el motivo es el servidor."""
    monkeypatch.setenv("OLLAMA_BASE_URL", SIN_SERVIDOR)
    c, _ = client

    respuesta = await c.post(
        "/agents/chat",
        json={"query": "hola", "provider": "ollama", "model": "qwen2.5:14b"},
    )

    assert respuesta.status_code == 400
    assert SIN_SERVIDOR in respuesta.json()["detail"]
