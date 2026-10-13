"""Un solo semáforo para toda la inferencia local.

El tope existe por la GPU: `llm_max_concurrent()` devuelve 1 en perfil local
justamente para no sobre-suscribir los 12 GB. Pero el tope sólo sirve si es
**global**: dos semáforos de tamaño 1 dejan pasar dos requests, y el segundo
espera a que Ollama vacíe su cola con el timeout del usuario corriendo.

Antes vivía dentro de `local_intelligence.py`, que era el único que hablaba con
Ollama. Ahora también lo hace el chat (`llm_provider.OllamaProvider`), así que
el semáforo se muda acá: un turno de chat y una extracción de boletín comparten
la misma cola en vez de pelearse la GPU.
"""

from __future__ import annotations

import asyncio

from app.core.hardware import llm_max_concurrent

_LLM_SEM: asyncio.Semaphore | None = None


def llm_semaphore() -> asyncio.Semaphore:
    """Semáforo compartido por todos los llamadores de Ollama del proceso.

    Se crea perezosamente: importar este módulo no debe instanciar nada, y el
    tamaño sale de env en cada arranque (los tests parchean `os.environ` antes
    del primer uso).
    """
    global _LLM_SEM
    if _LLM_SEM is None:
        _LLM_SEM = asyncio.Semaphore(llm_max_concurrent())
    return _LLM_SEM
