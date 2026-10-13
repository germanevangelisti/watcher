"""El contrato de ChromaDB 1.x que las funciones de embedding tienen que cumplir.

Regresión de un bug que vivió **en verde** dentro de la suite.

`CollectionCommon._embed()` de ChromaDB no usa el mismo método para las dos
operaciones:

    if is_query:  return self._embedding_function.embed_query(input=input)
    else:         return self._embedding_function(input=input)

Las clases de `app/services/embedding_service.py` implementaban sólo `__call__`,
así que **indexar andaba y buscar no**: `collection.query()` moría con
`AttributeError: 'LocalEmbeddingFunction' object has no attribute 'embed_query'`,
`EmbeddingService.search()` se comía la excepción en su `except` y devolvía `[]`.
La búsqueda semántica quedó muerta sin que nada se pusiera rojo: los tests que
existían (`test_search_basic`, `test_search_with_filter`) afirmaban
`isinstance(results, list)` — que es exactamente lo que devuelve el camino roto.
18/18 en verde con el buscador apagado.

Por eso acá no se mira el tipo de lo que vuelve: se mide que una colección real,
con la función de embedding real, **devuelva el documento**.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

backend_path = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

chromadb = pytest.importorskip("chromadb")

DIM = 8


class _ModeloFalso:
    """Encoder mínimo: mismo texto → mismo vector; textos distintos, vectores distintos.

    Evita cargar el sentence-transformer real. Lo que se mide acá es el contrato con
    ChromaDB, no la calidad del modelo — para eso está `test_search_basic`.
    """

    def encode(self, textos, **kwargs):
        vectores = []
        for texto in textos:
            rng = np.random.default_rng(abs(hash(texto)) % (2 ** 32))
            vectores.append(rng.random(DIM).astype("float32"))
        return np.array(vectores)


def _funcion_local() -> "object":
    """`LocalEmbeddingFunction` real, con el modelo real reemplazado por el falso."""
    from app.services.embedding_service import LocalEmbeddingFunction

    fn = object.__new__(LocalEmbeddingFunction)
    fn.model_name = "modelo-falso"
    fn.dim = DIM
    fn.model = _ModeloFalso()
    return fn


def _coleccion(tmp_path, nombre: str = "contrato"):
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    return client.get_or_create_collection(
        name=nombre, embedding_function=_funcion_local(),
    )


def test_una_busqueda_real_devuelve_el_documento(tmp_path):
    """El test que faltaba: `query()` con nuestra función, contra ChromaDB de verdad.

    Antes del fix esto levantaba AttributeError (y el servicio lo tapaba devolviendo []).
    """
    col = _coleccion(tmp_path)
    col.add(ids=["a"], documents=["contrato de obra pública en la provincia"])

    resultado = col.query(query_texts=["contrato de obra pública en la provincia"], n_results=1)

    assert resultado["ids"][0] == ["a"]


def test_el_documento_se_indexa_y_se_recupera_por_el_mismo_camino(tmp_path):
    """Indexar y buscar tienen que pasar por funciones distintas y dar el mismo vector."""
    fn = _funcion_local()
    col = chromadb.PersistentClient(path=str(tmp_path / "chroma")).get_or_create_collection(
        name="simetria", embedding_function=fn,
    )
    col.add(ids=["x", "y"], documents=["licitación de vialidad", "edicto sucesorio"])

    resultado = col.query(query_texts=["edicto sucesorio"], n_results=2)

    assert resultado["ids"][0][0] == "y"


@pytest.mark.parametrize("nombre", ["GoogleEmbeddingFunction", "LocalEmbeddingFunction"])
def test_las_dos_funciones_cumplen_el_protocolo(nombre):
    """`embed_query` no es opcional: ChromaDB lo llama en cada búsqueda."""
    from app.services import embedding_service as es
    from chromadb.api.types import EmbeddingFunction

    clase = getattr(es, nombre)

    assert issubclass(clase, EmbeddingFunction), (
        f"{nombre} tiene que heredar de chromadb.api.types.EmbeddingFunction: sin eso "
        "no hereda embed_query y toda búsqueda falla."
    )
    assert "embed_query" in dir(clase)


def test_la_funcion_de_google_busca_con_retrieval_query(monkeypatch):
    """`task_type` es parte del contrato de Gemini: la query no es un documento.

    El `__call__` de Google usa `retrieval_document` para indexar; si la búsqueda
    heredara ese default, cada query se embeddearía como documento. Se verifica acá
    porque en esta máquina no hay API key para medirlo en vivo.
    """
    from app.services import embedding_service as es

    usados = []

    class _GenaiFalso:
        @staticmethod
        def embed_content(model, content, task_type):
            usados.append(task_type)
            return {"embedding": [0.0] * DIM}

    # `genai` sólo se bindea si google-generativeai está instalado: en esta máquina no está.
    monkeypatch.setattr(es, "genai", _GenaiFalso, raising=False)

    fn = es.GoogleEmbeddingFunction("api-key-falsa")
    fn.__call__(["un documento"])
    fn.embed_query(["una consulta"])

    assert usados == ["retrieval_document", "retrieval_query"]
