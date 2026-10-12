"""El provider local del chat: `OllamaProvider` y la resolución de proveedor.

Hasta esta historia el agente de insight hablaba **sólo** con Gemini:
`google-generativeai` estaba declarado en `pyproject.toml` pero no instalado en
el venv, así que `self.model` quedaba en None y cada respuesta del chat era el
texto enlatado que mandaba a configurar la API de Google.  El runtime local ya
estaba pago —Ollama con `qwen2.5:7b`, probado por `scripts/check-ai-providers.py`—
pero servía a la capa de **análisis** (`LocalProProvider` extrae actos de
fragmentos); no había ningún camino de generación hacia él.

Acá se fija el contrato HTTP con `/api/chat` (roles, opciones, recorte de la
salida) y la política de resolución (respetar `LLM_PROVIDER`, caer a local sin
levantar nunca).  Ningún test toca la red: `httpx.MockTransport` intercepta, que
es justamente lo que permite medir esto en una máquina sin Ollama.

Run from watcher-backend/:
    .venv/Scripts/python.exe -m pytest tests/tests/unit/test_llm_provider_ollama.py -v
"""

import json
import sys
from pathlib import Path

import httpx
import pytest

backend_path = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from app.services import llm_provider as lp  # noqa: E402

NUM_CTX = 4096


def _provider(
    respuesta: dict | None = None,
    status: int = 200,
    num_ctx: int = NUM_CTX,
) -> tuple[lp.OllamaProvider, dict]:
    """Un `OllamaProvider` con la red interceptada.

    Devuelve también el dict donde el handler deja la request: así cada test
    mira lo que **de verdad** se envió, no lo que el provider dice que envía.
    """
    capturado: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["url"] = str(request.url)
        capturado["payload"] = json.loads(request.content)
        if status != 200:
            return httpx.Response(status, json={"error": "boom"})
        return httpx.Response(200, json=respuesta or {"message": {"content": "hola"}})

    provider = lp.OllamaProvider(
        base_url="http://ollama.test:11434",
        model="modelo-de-prueba",
        timeout_s=5,
        num_ctx=num_ctx,
        transport=httpx.MockTransport(handler),
    )
    return provider, capturado


# ----------------------------------------------------------------- contrato HTTP


async def test_generate_chat_manda_los_roles_como_roles():
    """El bloque `system` no se aplana dentro del user: viaja como rol.

    Esto es lo que los otros providers no hacen —Gemini y Anthropic arman un
    texto único— y lo que importa acá: el modelo tiene que leer las reglas
    (honestidad, citación) como instrucciones, no como parte de la pregunta.
    """
    provider, capturado = _provider()

    await provider.generate_chat([
        {"role": "system", "content": "sos un asistente"},
        {"role": "user", "content": "¿cuánto se ejecutó?"},
        {"role": "assistant", "content": "algo"},
    ])

    assert capturado["url"] == "http://ollama.test:11434/api/chat"
    assert capturado["payload"]["messages"] == [
        {"role": "system", "content": "sos un asistente"},
        {"role": "user", "content": "¿cuánto se ejecutó?"},
        {"role": "assistant", "content": "algo"},
    ]


async def test_stream_apagado_keep_alive_y_modelo_configurado():
    provider, capturado = _provider()

    await provider.generate_chat([{"role": "user", "content": "hola"}])

    assert capturado["payload"]["stream"] is False
    assert capturado["payload"]["model"] == "modelo-de-prueba"
    # Sin keep_alive el modelo se descarga entre turnos y el primer token de
    # cada mensaje paga la carga entera.
    assert capturado["payload"]["keep_alive"]


async def test_las_opciones_llevan_lo_que_configura_el_agente():
    provider, capturado = _provider()

    await provider.generate_chat(
        [{"role": "user", "content": "hola"}], temperature=0.3, max_tokens=512,
    )

    options = capturado["payload"]["options"]
    assert options["temperature"] == 0.3
    assert options["num_predict"] == 512
    assert options["num_ctx"] == NUM_CTX


async def test_devuelve_el_contenido_del_mensaje():
    provider, _ = _provider({"message": {"content": "  la respuesta  "}})

    assert await provider.generate_chat([{"role": "user", "content": "x"}]) == "la respuesta"


async def test_generate_text_pone_el_system_prompt_como_rol():
    provider, capturado = _provider()

    await provider.generate_text("resumí esto", system_prompt="sos un analista")

    assert capturado["payload"]["messages"] == [
        {"role": "system", "content": "sos un analista"},
        {"role": "user", "content": "resumí esto"},
    ]


# ------------------------------------------------------------------- fallas


async def test_una_respuesta_vacia_levanta_para_no_dejar_la_burbuja_en_blanco():
    """Devolver "" dejaría una burbuja vacía: peor que el mensaje que explica qué pasó."""
    provider, _ = _provider({"message": {"content": "   "}})

    with pytest.raises(ValueError):
        await provider.generate_chat([{"role": "user", "content": "x"}])


async def test_un_error_http_propaga_y_el_agente_decide():
    """El provider no se come el error: el fallback es decisión del agente."""
    provider, _ = _provider(status=500)

    with pytest.raises(httpx.HTTPStatusError):
        await provider.generate_chat([{"role": "user", "content": "x"}])


# ---------------------------------------------------- recorte del prompt


async def test_un_prompt_largo_recorta_la_salida_y_no_el_prompt():
    """Si no entra todo, se recorta la salida.

    El principio del prompt es donde viven las reglas del sistema.  Perderlas no
    da error: da respuestas que mienten con seguridad — que es el modo de falla
    más caro que ya tuvo este producto ("0 documentos encontrados" sobre
    organismos que nunca se consultaron).
    """
    provider, capturado = _provider(num_ctx=2048)
    largo = "x" * 4000  # ~1000 tokens estimados

    await provider.generate_chat([{"role": "system", "content": largo}], max_tokens=2000)

    assert capturado["payload"]["messages"][0]["content"] == largo  # el prompt va entero
    assert capturado["payload"]["options"]["num_predict"] < 2000
    assert capturado["payload"]["options"]["num_predict"] >= 128


async def test_un_prompt_corto_no_recorta_la_salida():
    provider, capturado = _provider()

    await provider.generate_chat([{"role": "user", "content": "hola"}], max_tokens=2000)

    assert capturado["payload"]["options"]["num_predict"] == 2000


# ------------------------------------------------------------- resolución


def test_ollama_es_un_valor_valido_de_llm_provider():
    assert lp.LLMProviderType("ollama") is lp.LLMProviderType.OLLAMA


def test_la_factory_construye_ollama():
    provider = lp.LLMProviderFactory.create_provider(lp.LLMProviderType.OLLAMA)

    assert isinstance(provider, lp.OllamaProvider)


def test_resolve_respeta_ollama_explicito(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")

    assert isinstance(lp.resolve_llm_provider(), lp.OllamaProvider)


def test_resolve_se_cae_a_local_cuando_lo_configurado_no_se_puede_construir(monkeypatch):
    """`LLM_PROVIDER=google` sin SDK y sin key no puede tumbar el chat.

    Es el estado exacto de la máquina que destapó el bug: el `.env` decía
    `google`, el paquete no estaba instalado y la key no estaba puesta.
    """
    monkeypatch.setenv("LLM_PROVIDER", "google")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    assert isinstance(lp.resolve_llm_provider(), lp.OllamaProvider)


def test_resolve_no_levanta_ni_con_un_provider_inventado(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "proveedor-que-no-existe")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    assert isinstance(lp.resolve_llm_provider(), lp.OllamaProvider)


def test_auto_es_local_si_hay_ollama_y_google_si_no(monkeypatch):
    """`auto` espeja a `INTELLIGENCE_PROVIDER`, que ya documentaba esta regla."""
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    assert lp._resolve_provider_type("auto") is lp.LLMProviderType.OLLAMA

    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    assert lp._resolve_provider_type("auto") is lp.LLMProviderType.GOOGLE


def test_ingesta_y_chat_comparten_el_semaforo_de_la_gpu():
    """El tope de concurrencia sólo sirve si es global.

    Dos semáforos de tamaño `LLM_MAX_CONCURRENT` dejan pasar el doble, y la GPU
    es una sola: el chat y una extracción de boletín tienen que hacer cola entre
    ellos, no pelearse el modelo.
    """
    from app.services import llm_concurrency, local_intelligence

    assert local_intelligence.llm_semaphore is llm_concurrency.llm_semaphore
    assert llm_concurrency.llm_semaphore() is llm_concurrency.llm_semaphore()
