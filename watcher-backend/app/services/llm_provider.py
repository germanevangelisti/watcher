"""
LLM Provider Abstraction

Provides a unified interface for multiple LLM providers (Google Gemini, Anthropic,
Ollama local). Allows easy switching between providers via configuration.
"""

import importlib.util
import logging
import os
from abc import ABC, abstractmethod
from enum import Enum

import httpx
from app.core.hardware import (
    ollama_base_url,
    ollama_model,
    ollama_num_ctx,
    ollama_timeout_s,
)
from app.services.llm_concurrency import llm_semaphore

logger = logging.getLogger(__name__)


class LLMProviderType(str, Enum):
    """Supported LLM providers"""
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    # Identificador estable del proveedor, distinto del nombre de la clase: el
    # chat lo devuelve en cada respuesta para que la burbuja pueda declarar con
    # qué se generó. Sin esto, comparar dos proveedores es adivinar.
    provider_id: str = "desconocido"

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: str | None = None
    ) -> str:
        """Generate text from a prompt"""
        pass

    @abstractmethod
    async def generate_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text from a conversation history"""
        pass


class GoogleGeminiProvider(LLMProvider):
    """Google Gemini LLM provider"""

    provider_id = "google"

    def __init__(self, api_key: str | None = None, model: str = "gemini-2.5-flash"):
        """
        Initialize Google Gemini provider

        Args:
            api_key: Google API key (reads from GOOGLE_API_KEY env var if not provided)
            model: Model name (default: gemini-2.5-flash)
        """
        try:
            import google.generativeai as genai

            self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
            if not self.api_key:
                raise ValueError("GOOGLE_API_KEY not found in environment or parameters")

            # genai.configure() is called once at app startup in main.py
            self.model = genai.GenerativeModel(model)
            self.model_name = model

            logger.info(f"Google Gemini provider initialized with model: {model}")

        except ImportError:
            raise ImportError("google-generativeai not installed. Install with: pip install google-generativeai")

    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: str | None = None
    ) -> str:
        """Generate text from a prompt using Gemini"""
        import asyncio

        import google.generativeai as genai

        # Combine system prompt and user prompt
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        response = await asyncio.to_thread(
            self.model.generate_content,
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )
        )

        return response.text.strip()

    async def generate_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text from conversation history using Gemini"""
        import asyncio

        import google.generativeai as genai

        # Convert messages to Gemini format
        conversation_text = "\n\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in messages
        ])

        response = await asyncio.to_thread(
            self.model.generate_content,
            conversation_text,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )
        )

        return response.text.strip()


class AnthropicProvider(LLMProvider):
    """Anthropic Claude LLM provider"""

    provider_id = "anthropic"

    def __init__(self, api_key: str | None = None, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize Anthropic provider

        Args:
            api_key: Anthropic API key (reads from ANTHROPIC_API_KEY env var if not provided)
            model: Model name (default: claude-3-5-sonnet-20241022)
        """
        try:
            import anthropic

            self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment or parameters")

            self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
            self.model_name = model

            logger.info(f"Anthropic provider initialized with model: {model}")

        except ImportError:
            raise ImportError("anthropic not installed. Install with: pip install anthropic")

    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: str | None = None
    ) -> str:
        """Generate text from a prompt using Claude"""

        # Build messages
        messages = [{"role": "user", "content": prompt}]

        # Create message with optional system prompt
        kwargs = {
            "model": self.model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        response = await self.client.messages.create(**kwargs)

        return response.content[0].text.strip()

    async def generate_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text from conversation history using Claude"""

        # Extract system message if present
        system_prompt = None
        chat_messages = []

        for msg in messages:
            if msg['role'] == 'system':
                system_prompt = msg['content']
            else:
                chat_messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })

        # Create message
        kwargs = {
            "model": self.model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": chat_messages
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        response = await self.client.messages.create(**kwargs)

        return response.content[0].text.strip()


# Estimación tosca y **conservadora a propósito**: sirve para no pasarse de
# `num_ctx`, no para contar tokens. Se prefiere subestimar el presupuesto de
# salida antes que comerse el prompt.
_CHARS_POR_TOKEN = 4
# Plantilla del chat template + tokens especiales que no vienen del texto.
_MARGEN_TOKENS = 64
_MIN_NUM_PREDICT = 128


class OllamaProvider(LLMProvider):
    """Ollama local server (`POST /api/chat`).

    No necesita API key y nada sale de la máquina, que es la razón de existir
    del perfil local. `__init__` **no hace I/O**: el agente de insight es un
    singleton construido al importar el módulo de la API, así que un servidor
    caído tiene que aparecer en el turno del usuario, no en el arranque del
    backend (donde además rompería los tests, que no tienen Ollama).

    Args:
        base_url: raíz del servidor (por defecto `OLLAMA_BASE_URL`/localhost)
        model: nombre del modelo (por defecto `OLLAMA_MODEL`)
        timeout_s: timeout HTTP (por defecto `OLLAMA_TIMEOUT_S`)
        num_ctx: tamaño del KV-cache (por defecto `OLLAMA_NUM_CTX`)
        transport: transporte httpx, sólo para tests
    """

    provider_id = "ollama"

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_s: float | None = None,
        num_ctx: int | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.base_url = (base_url or ollama_base_url() or "http://127.0.0.1:11434").rstrip("/")
        self.model_name = model or ollama_model()
        self.timeout_s = float(timeout_s) if timeout_s is not None else ollama_timeout_s()
        self.num_ctx = int(num_ctx) if num_ctx is not None else ollama_num_ctx()
        self._transport = transport

    def _num_predict(self, messages: list[dict[str, str]], max_tokens: int) -> int:
        """Cuántos tokens puede generar el modelo sin pisar el prompt.

        Si el prompt no entra en `num_ctx`, Ollama recorta — y de qué lado
        recorta es un detalle del que no quiero depender: el principio del
        prompt es donde viven las reglas del sistema (honestidad, citación) y
        perderlas no da error, da respuestas que mienten con seguridad. Así que
        el recorte se decide acá y de la salida.
        """
        prompt_tokens = sum(len(m.get("content") or "") for m in messages) // _CHARS_POR_TOKEN
        disponible = self.num_ctx - prompt_tokens - _MARGEN_TOKENS
        if disponible >= max_tokens:
            return max_tokens
        recortado = max(_MIN_NUM_PREDICT, disponible)
        logger.warning(
            "Prompt de ~%d tokens contra num_ctx=%d: salida recortada a %d tokens "
            "(pedía %d). Subí OLLAMA_NUM_CTX si las respuestas salen cortas.",
            prompt_tokens, self.num_ctx, recortado, max_tokens,
        )
        return recortado

    async def generate_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Genera desde un historial de conversación.

        A diferencia de los otros providers, los roles viajan **como roles**: el
        bloque `system` no se aplana dentro del user, así que el modelo lo trata
        como instrucciones y no como parte de la pregunta.
        """
        payload = {
            "model": self.model_name,
            "stream": False,
            # Sin esto el modelo se descarga entre mensajes y el primer token de
            # cada turno paga la carga entera.
            "keep_alive": "30m",
            "messages": [
                {"role": m["role"], "content": m["content"]} for m in messages
            ],
            "options": {
                "temperature": temperature,
                "num_ctx": self.num_ctx,
                "num_predict": self._num_predict(messages, max_tokens),
            },
        }
        url = f"{self.base_url}/api/chat"

        # El mismo semáforo que usa la ingesta: un turno de chat y una
        # extracción de boletín comparten GPU y se encolan en vez de pelearla.
        async with llm_semaphore(), httpx.AsyncClient(
            timeout=self.timeout_s, transport=self._transport
        ) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            body = response.json()

        message = body.get("message") or {}
        text = message.get("content") or body.get("response") or ""
        if not text.strip():
            # Devolver "" dejaría una burbuja vacía en el chat: peor que el
            # mensaje de fallback, que al menos dice qué pasó.
            raise ValueError("Ollama devolvió una respuesta vacía")

        return text.strip()

    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: str | None = None
    ) -> str:
        """Genera desde un prompt suelto, con el system prompt como rol aparte."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return await self.generate_chat(messages, temperature, max_tokens)


class LLMProviderFactory:
    """Factory for creating LLM providers"""

    @staticmethod
    def create_provider(
        provider_type: LLMProviderType = LLMProviderType.GOOGLE,
        api_key: str | None = None,
        model: str | None = None
    ) -> LLMProvider:
        """
        Create an LLM provider instance

        Args:
            provider_type: Type of provider (google or anthropic)
            api_key: API key (optional, reads from env var if not provided)
            model: Model name (optional, uses default if not provided)

        Returns:
            LLMProvider instance

        Raises:
            ValueError: If provider type is not supported
        """
        if provider_type == LLMProviderType.GOOGLE:
            return GoogleGeminiProvider(api_key=api_key, model=model or "gemini-2.5-flash")
        elif provider_type == LLMProviderType.ANTHROPIC:
            return AnthropicProvider(api_key=api_key, model=model or "claude-3-5-sonnet-20241022")
        elif provider_type == LLMProviderType.OLLAMA:
            return OllamaProvider(model=model)
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")

    @staticmethod
    def create_from_env() -> LLMProvider:
        """
        Create an LLM provider based on environment configuration

        Reads LLM_PROVIDER environment variable (default: ollama)
        Reads LLM_MODEL environment variable for model selection

        Returns:
            LLMProvider instance
        """
        provider_str = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
        model = os.getenv("LLM_MODEL", None)  # None = use provider default

        try:
            provider_type = _resolve_provider_type(provider_str)
        except ValueError:
            logger.warning(f"Invalid LLM_PROVIDER '{provider_str}', defaulting to Ollama")
            provider_type = LLMProviderType.OLLAMA

        return LLMProviderFactory.create_provider(provider_type, model=model)


def _resolve_provider_type(provider_str: str) -> LLMProviderType:
    """Traduce el valor de `LLM_PROVIDER` a un tipo, resolviendo `auto`.

    `auto` espeja a `INTELLIGENCE_PROVIDER` (ver `.env.example`): si hay un
    Ollama configurado, es local — que es la dirección del producto — y si no,
    Google.
    """
    if provider_str == "auto":
        return LLMProviderType.OLLAMA if ollama_base_url() else LLMProviderType.GOOGLE
    return LLMProviderType(provider_str)


def _construir_o_motivo(valor: str) -> tuple[LLMProvider | None, str | None]:
    """Intenta construir lo que dice `LLM_PROVIDER`. Devuelve `(provider, motivo)`.

    El motivo viaja hacia arriba en vez de quedarse en el log a propósito: el
    panel de agentes muestra la misma frase que el log, porque quien elige el
    proveedor no tiene por qué mirar la consola del backend para enterarse de
    que el suyo no se pudo usar.
    """
    try:
        provider_type = _resolve_provider_type(valor)
    except ValueError:
        return None, f"«{valor}» no es un proveedor conocido"

    try:
        return LLMProviderFactory.create_provider(provider_type), None
    except Exception as exc:
        return None, f"{provider_type.value} no se pudo construir: {exc}"


def resolve_llm_provider() -> LLMProvider:
    """El provider del chat: respeta la configuración y **nunca levanta**.

    Es distinto de `get_llm_provider()`, que construye lo configurado y levanta
    si no puede — eso sirve para scripts y chequeos de configuración, donde
    fallar ruidosamente es lo correcto. Acá, en cambio, la falta de un provider
    no puede tumbar el turno de un usuario: si lo configurado no se puede
    construir (falta la API key, falta el SDK, el valor no existe), se cae a
    Ollama —el único sin secreto ni paquete extra— y se loguea fuerte, porque
    cambiar de proveedor mueve el contexto del boletín fuera de la máquina.
    """
    provider_str = os.getenv("LLM_PROVIDER", "ollama").strip().lower()

    provider, motivo = _construir_o_motivo(provider_str)
    if provider is not None:
        logger.info("Chat LLM: %s (%s)", provider.model_name, provider.provider_id)
        return provider

    logger.warning(
        "LLM_PROVIDER=%s no se pudo construir (%s); el chat usa Ollama local, "
        "no sale nada de la máquina.",
        provider_str, motivo,
    )

    provider = OllamaProvider()
    logger.info("Chat LLM: local %s en %s", provider.model_name, provider.base_url)
    return provider


# ---------------------------------------------------------------------------
# Catálogo y elección explícita (panel de agentes)
# ---------------------------------------------------------------------------
#
# Con qué proveedor contesta el chat es hoy una decisión invisible: sale de
# `LLM_PROVIDER` en el `.env`, y los tres candidatos se diferencian por cosas
# que no se ven desde la pantalla —uno necesita un paquete, otro una API key, el
# local un servidor con el modelo descargado—. Para poder comparar calidad hay
# que poder elegir, y para elegir con criterio hay que saber por qué un
# proveedor no está disponible. Eso es todo lo que hace esta sección: no
# redacta, no decide por el usuario y no esconde la degradación.

# (id, etiqueta, módulo a importar, paquete pip, variable de la key, modelo por
# defecto, si sale de la máquina). El orden es el de la UI: primero el local,
# que es la dirección del producto.
_PROVEEDORES = (
    ("ollama", "Ollama", None, None, None, None, False),
    ("google", "Google Gemini", "google.generativeai", "google-generativeai",
     "GOOGLE_API_KEY", "gemini-2.5-flash", True),
    ("anthropic", "Anthropic Claude", "anthropic", "anthropic",
     "ANTHROPIC_API_KEY", "claude-3-5-sonnet-20241022", True),
)


async def estado_de_ollama(base_url: str | None = None, timeout_s: float = 3.0) -> dict:
    """¿Está el servidor local y qué modelos tiene? **Nunca levanta.**

    El proveedor de Ollama no hace I/O al construirse (a propósito), así que sin
    esta sonda el catálogo diría "disponible" con el servidor apagado y el
    usuario se enteraría recién al mandar el mensaje.
    """
    base = (base_url or ollama_base_url() or "http://127.0.0.1:11434").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            respuesta = await client.get(f"{base}/api/tags")
            respuesta.raise_for_status()
            cuerpo = respuesta.json()
    except Exception as exc:
        return {
            "base_url": base,
            "responde": False,
            "modelos": [],
            "motivo": f"el servidor local no responde en {base} ({type(exc).__name__})",
        }

    modelos = [m["name"] for m in (cuerpo.get("models") or []) if m.get("name")]
    return {"base_url": base, "responde": True, "modelos": modelos, "motivo": None}


async def provider_catalog() -> list[dict]:
    """Cada proveedor con su modelo, si se puede usar y **por qué no**.

    `available` significa "se puede usar tal como está configurado", no "el
    paquete está instalado": un Ollama con el servidor arriba pero sin el modelo
    pedido no sirve para chatear, y decir que sí mandaría al usuario a un error
    que ya sabíamos.
    """
    ollama = await estado_de_ollama()
    catalogo: list[dict] = []

    for pid, etiqueta, modulo, pip, var_key, modelo_def, remoto in _PROVEEDORES:
        entrada = {
            "id": pid,
            "label": etiqueta,
            "local": not remoto,
            "available": True,
            "reason": None,
            "model": None,
            "models": [],
        }

        if pid == "ollama":
            entrada["model"] = ollama_model()
            entrada["models"] = ollama["modelos"]
            if not ollama["responde"]:
                entrada["available"] = False
                entrada["reason"] = ollama["motivo"]
            elif entrada["model"] not in ollama["modelos"]:
                entrada["available"] = False
                entrada["reason"] = (
                    f"el modelo «{entrada['model']}» no está descargado en el servidor local"
                )
        else:
            # `LLM_MODEL` pisa el default de cualquier proveedor remoto: es el
            # que usa `create_from_env`, así que el catálogo tiene que decir eso
            # y no el default del código.
            entrada["model"] = os.getenv("LLM_MODEL") or modelo_def
            if importlib.util.find_spec(modulo) is None:
                entrada["available"] = False
                entrada["reason"] = f"falta el paquete {pip}"
            elif not os.getenv(var_key):
                entrada["available"] = False
                entrada["reason"] = f"falta {var_key}"
            elif remoto:
                entrada["reason"] = "remoto: el contexto del boletín sale de la máquina"

        catalogo.append(entrada)

    return catalogo


def build_provider(provider_id: str, model: str | None = None) -> LLMProvider:
    """Construye el proveedor que el usuario eligió. **Levanta si no se puede.**

    Es lo contrario de `resolve_llm_provider()`, y la diferencia es el punto
    entero de la función: en un turno normal caer a Ollama es preferible a
    fallar, pero cuando alguien eligió Gemini para compararlo contra el local,
    contestarle con Ollama le haría comparar Ollama contra Ollama y sacar una
    conclusión falsa sobre Gemini. Mejor un error que dice por qué.
    """
    valor = str(provider_id or "").strip().lower()
    try:
        provider_type = LLMProviderType(valor)
    except ValueError:
        conocidos = ", ".join(p[0] for p in _PROVEEDORES)
        raise ValueError(f"Proveedor desconocido: «{provider_id}». Los válidos son: {conocidos}.")

    try:
        return LLMProviderFactory.create_provider(provider_type, model=model)
    except Exception as exc:
        raise ValueError(f"No se pudo usar {provider_type.value}: {exc}") from exc


def configured_provider() -> dict:
    """Con qué proveedor arranca el chat y de dónde sale ese valor.

    Existe porque el default es invisible y ahora es remoto: con el SDK de
    Google instalado, un `.env` que diga `LLM_PROVIDER=google` manda el contexto
    de los boletines afuera **sin que nadie toque una línea de código**. Que el
    panel lo diga es la diferencia entre elegir y enterarse.
    """
    bruto = os.getenv("LLM_PROVIDER")
    valor = (bruto or "ollama").strip().lower()

    if bruto is None:
        origen = "LLM_PROVIDER no está definido: el código usa ollama"
    elif valor == "auto":
        origen = (
            "LLM_PROVIDER=auto → local, porque hay un OLLAMA_BASE_URL configurado"
            if ollama_base_url()
            else "LLM_PROVIDER=auto → google, porque no hay OLLAMA_BASE_URL configurado"
        )
    else:
        origen = f"LLM_PROVIDER={valor}"

    provider, motivo = _construir_o_motivo(valor)
    if provider is None:
        local = OllamaProvider()
        return {
            "provider": local.provider_id,
            "model": local.model_name,
            "requested": valor,
            "origin": origen,
            "fallback": True,
            "reason": f"{motivo}; el chat usa Ollama local, no sale nada de la máquina",
        }

    return {
        "provider": provider.provider_id,
        "model": getattr(provider, "model_name", None),
        "requested": valor,
        "origin": origen,
        "fallback": False,
        "reason": None,
    }


# Convenience function for quick access
def get_llm_provider(
    provider_type: LLMProviderType | None = None
) -> LLMProvider:
    """
    Get an LLM provider instance

    Args:
        provider_type: Optional provider type. If not specified, reads from LLM_PROVIDER env var

    Returns:
        LLMProvider instance
    """
    if provider_type:
        return LLMProviderFactory.create_provider(provider_type)
    else:
        return LLMProviderFactory.create_from_env()
