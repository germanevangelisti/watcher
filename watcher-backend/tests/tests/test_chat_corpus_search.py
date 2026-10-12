"""La búsqueda sobre el corpus del chat: sus dos mitades y su ausencia declarada.

El 2026-10-01 el chat contestó *"No se publicó información sobre obra pública en
septiembre"*.  Es falso —cinco boletines de septiembre publican la frase, con
licitaciones de obra reales— y el corpus no se había mirado: `hybrid_search` corría
con las dos mitades apagadas.

- **keyword**: el agente construía el `RetrievalService` **sin sesión**, así que
  `fts_service` quedaba en `None` y `search_bm25` no se ejecutaba nunca (un log de
  debug, invisible).  El índice FTS estaba sano.
- **semántica**: sin función de embedding el servicio abría la colección vacía
  `watcher_documents` mientras los 983 chunks reales vivían en
  `watcher_documents_local`, y devolvía `[]` con un INFO.

Acá se fija que la búsqueda use una sesión, que las degradaciones se digan fuerte en
vez de devolver un `0` que se lee como "sin coincidencias", y que el hueco viaje al
system prompt como un hecho —para que el modelo no tenga que inferir la diferencia
entre *no busqué* y *busqué y no había*.

Run from watcher-backend/:
    .venv/Scripts/python.exe -m pytest tests/tests/test_chat_corpus_search.py -v
"""

import logging
import sys
from pathlib import Path

import pytest

# `agents.*` vive en la raíz del backend, que pytest no agrega solo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# La pregunta del turno que destapó el bug.
PREGUNTA = "¿qué se publicó sobre obra pública en septiembre?"


class _SessionCtx:
    """Sesión asíncrona que nunca se toca."""

    def __init__(self, db=None):
        self._db = db

    async def __aenter__(self):
        return self._db

    async def __aexit__(self, *exc):
        return False


class _ProviderFalso:
    """Registra los mensajes que recibe y devuelve un texto fijo."""

    def __init__(self, respuesta: str = "no lo encontré en el corpus"):
        self.respuesta = respuesta
        self.mensajes: list[dict] = []

    async def generate_chat(self, messages, temperature=0.7, max_tokens=2000):
        self.mensajes = messages
        return self.respuesta


# --------------------------------------------------- F1: la sesión que faltaba


async def test_la_busqueda_del_corpus_usa_una_sesion_y_la_cierra(monkeypatch):
    """Sin sesión, `RetrievalService` apaga la mitad keyword en silencio.

    Es el contrato mínimo de F1: la búsqueda del chat tiene que construir el
    servicio **con** sesión, y la sesión tiene que cerrarse al terminar.
    """
    capturado: dict = {}

    class _Sesion:
        def close(self):
            capturado["cerrada"] = True

    class _Servicio:
        def __init__(self, session):
            capturado["session"] = session

        async def hybrid_search(self, query, top_k=5, rerank=False):
            capturado["query"] = query
            return []

    monkeypatch.setattr("app.db.sync_session.SyncSessionLocal", _Sesion)
    monkeypatch.setattr("app.services.retrieval_service.RetrievalService", _Servicio)

    from agents.insight_reporting import agent as agent_module

    agente = agent_module.InsightReportingAgent()

    assert await agente._buscar_en_corpus(PREGUNTA) == []
    assert isinstance(capturado["session"], _Sesion)
    assert capturado["cerrada"] is True
    assert capturado["query"] == PREGUNTA


def test_pedir_keyword_sin_sesion_avisa_en_vez_de_devolver_vacio(caplog):
    """El caso viejo: `hybrid_search` sin sesión era semántica sola, sin decirlo."""
    from app.services.retrieval_service import RetrievalService

    servicio = RetrievalService(None)

    with caplog.at_level(logging.WARNING):
        assert servicio.keyword_search(PREGUNTA) == []

    assert any("sin sesión de base" in r.message for r in caplog.records)


# --------------------------------------- F2/F3: la degradación, dicha fuerte


def _servicio_degradado(tmp_path, monkeypatch, caplog=None):
    """Un `EmbeddingService` como el de esta máquina: sin EF local."""
    from app.services import embedding_service as es

    monkeypatch.setattr(es, "SENTENCE_TRANSFORMERS_AVAILABLE", False)
    monkeypatch.setattr(
        es, "SENTENCE_TRANSFORMERS_ERROR",
        "ImportError: DLL load failed while importing _dist_metrics",
    )
    return es.EmbeddingService(
        persist_directory=str(tmp_path), embedding_provider="local",
    )


def test_el_motivo_de_la_degradacion_queda_en_la_instancia(tmp_path, monkeypatch):
    svc = _servicio_degradado(tmp_path, monkeypatch)

    assert svc.embedding_fn is None
    assert svc.degraded_reason
    assert "_dist_metrics" in svc.degraded_reason


def test_no_dice_que_falta_el_paquete_cuando_lo_que_falla_es_el_import(tmp_path, monkeypatch, caplog):
    """`sentence-transformers` está instalado: lo bloquea la política de la máquina.

    El mensaje viejo ("is not installed") mandaba a instalar algo que ya está, y
    dejaba tapado el hecho que importa: no hay embeddings locales.
    """
    from app.services import embedding_service as es

    with caplog.at_level(logging.ERROR):
        _servicio_degradado(tmp_path, monkeypatch)

    errores = [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR]
    assert any("_dist_metrics" in m for m in errores)
    assert any(es.LOCAL_COLLECTION_NAME in m for m in errores)
    assert not any("is not installed" in m for m in errores)


def test_una_coleccion_vacia_con_hermana_llena_se_grita(tmp_path, monkeypatch, caplog):
    """El `0 results` que se creía "sin coincidencias" era una colección vacía.

    Se arma el escenario real de la máquina: el servicio abre `watcher_documents`
    (vacía) y al lado está la `*_local` con documentos.
    """
    from app.services import embedding_service as es

    svc = _servicio_degradado(tmp_path, monkeypatch)
    svc.client.get_or_create_collection(es.LOCAL_COLLECTION_NAME).add(
        ids=["20260903_5_Secc_chunk_4"],
        documents=["FÍJASE el Presupuesto Oficial de la obra"],
        embeddings=[[0.1] * svc.embedding_dim],
        metadatas=[{"document_id": "20260903_5_Secc"}],
    )

    with caplog.at_level(logging.ERROR):
        svc._avisar_si_hay_documentos_en_otra_coleccion()

    errores = [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR]
    assert any("VACÍA" in m and es.LOCAL_COLLECTION_NAME in m for m in errores)


async def test_una_busqueda_sin_resultados_con_el_servicio_degradado_lo_dice(tmp_path, monkeypatch, caplog):
    svc = _servicio_degradado(tmp_path, monkeypatch)

    with caplog.at_level(logging.ERROR):
        assert await svc.search(PREGUNTA) == []

    assert any("degradado" in r.message for r in caplog.records if r.levelno == logging.ERROR)


# --------------------------------------------- F4: el hueco, declarado como dato


def test_el_bloque_dice_que_no_encontro_y_no_que_no_se_publico():
    from agents.tools.presupuesto_tools import build_corpus_system_block

    bloque = build_corpus_system_block(
        {"ejecutada": True, "resultados": 0, "motivo": "sin fragmentos"}
    )

    assert "NO devolvió fragmentos" in bloque
    assert "no lo encontraste" in bloque
    assert "nunca" in bloque and "no se publicó" in bloque


def test_el_bloque_dice_que_no_se_busco_cuando_no_se_busco():
    from agents.tools.presupuesto_tools import build_corpus_system_block

    bloque = build_corpus_system_block(
        {"ejecutada": False, "resultados": 0, "motivo": "deshabilitada"}
    )

    assert "NO se ejecutó" in bloque
    assert "no revisaste el corpus" in bloque


def test_con_fragmentos_no_se_emite_bloque():
    """El resto del chat no cambia de comportamiento: los fragmentos están en el contexto."""
    from agents.tools.presupuesto_tools import build_corpus_system_block

    assert build_corpus_system_block({"ejecutada": True, "resultados": 3}) == ""
    assert build_corpus_system_block(None) == ""


@pytest.fixture
def agente(monkeypatch):
    """Agente real con DB y router de presupuesto sustituidos, y el corpus cortado."""
    from agents.insight_reporting import agent as agent_module

    async def _resumen(db):
        return None

    async def _route(db, query, resumen, intents=None):
        return {}

    async def _stats(db):
        return {"documentos": 0}

    async def _sin_corpus(*_args, **_kwargs):
        return []

    monkeypatch.setattr(agent_module, "AsyncSessionLocal", lambda: _SessionCtx())
    monkeypatch.setattr(agent_module.PresupuestoTools, "get_ejecucion_resumen", _resumen)
    monkeypatch.setattr(agent_module, "route_presupuesto", _route)
    monkeypatch.setattr(agent_module.DatabaseTools, "get_statistics", _stats)
    monkeypatch.setattr(agent_module.InsightReportingAgent, "_buscar_en_corpus", _sin_corpus)

    return agent_module.InsightReportingAgent()


async def test_el_turno_sin_corpus_le_dice_al_modelo_que_no_afirme_ausencia(agente):
    """El turno exacto del bug: corpus vacío + pregunta "qué se publicó sobre X".

    Antes el modelo recibía sólo estadísticas generales, sin ninguna marca de que se
    hubiera buscado, y contestaba *"No se publicó información…"*.  Ahora el system
    prompt lleva el estado de la búsqueda.
    """
    falso = _ProviderFalso()
    agente.provider = falso

    out = await agente.query_with_data(PREGUNTA)

    system = falso.mensajes[0]["content"]
    assert falso.mensajes[0]["role"] == "system"
    assert "BÚSQUEDA SOBRE EL CORPUS" in system
    assert "NO devolvió fragmentos" in system
    # Sin fragmentos no hay fuente que citar.
    assert "corpus_boletines" not in out["data_used"]


async def test_con_fragmentos_el_prompt_no_lleva_el_bloque_de_ausencia(agente, monkeypatch):
    """Y la mitad que sí encuentra algo sigue igual que antes."""

    class _Resultado:
        text = "FÍJASE el Presupuesto Oficial de la obra"
        score = 0.9
        document_id = "20260903_5_Secc"

    async def _con_corpus(*_args, **_kwargs):
        return [_Resultado()]

    monkeypatch.setattr(agente, "_buscar_en_corpus", _con_corpus)

    falso = _ProviderFalso()
    agente.provider = falso

    out = await agente.query_with_data(PREGUNTA)

    assert "corpus_boletines" in out["data_used"]
    assert "BÚSQUEDA SOBRE EL CORPUS" not in falso.mensajes[0]["content"]
