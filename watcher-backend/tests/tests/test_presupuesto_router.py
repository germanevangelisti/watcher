"""Tests del router de tools de presupuesto y su contrato con el health.

`story-watcher-chat-presupuesto-tools` (P2) quedó acotada a dos cosas: el **criterio 4**
(la lista de capabilities del agente no mencionaba ninguna tool de presupuesto) y mover
el disparo de una cadena de `if` a un **router con contrato**.  Los criterios 1, 2, 3 y 5
ya los habían cumplido las historias hermanas.

Lo que se fija acá:

- `PRESUPUESTO_TOOLS` es la **única** fuente de la terna intent → key → tool, y la lista
  de capabilities del health **se deriva** de ella: si alguien agrega una tool y se olvida
  del endpoint, el test lo agarra.
- Cada intent declarado es alcanzable: hay al menos una frase real que lo enciende.  Una
  fila muerta en la tabla sería una tool que nunca corre.
- `route_presupuesto` ejecuta sólo lo pedido, no agrega keys vacías, y **una tool caída no
  se lleva las otras** (que es lo que pasaba antes: un fallo en el resumen se llevaba el
  desglose y los actos, que no dependen de la Ley).

Run from watcher-backend/:
    .venv/Scripts/python.exe -m pytest tests/tests/test_presupuesto_router.py -v
"""

import sys
from pathlib import Path

import pytest
import pytest_asyncio

# `agents.*` vive en la raíz del backend, que pytest no agrega solo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agents.tools.presupuesto_tools import (  # noqa: E402
    INTENT_ACTOS_DETALLE,
    INTENT_FINALIDADES,
    INTENT_ORGANISMO_DETALLE,
    INTENT_ORGANISMOS,
    INTENT_RESUMEN,
    PRESUPUESTO_TOOLS,
    budget_tool_names,
    detect_presupuesto_intents,
    route_presupuesto,
)

# Una frase que enciende cada intent declarado.  Si una tool nueva entra a la tabla sin
# forma de dispararse, esto falla — que es el punto.
FRASES = {
    INTENT_RESUMEN: "¿Qué porcentaje del presupuesto vigente se ha ejecutado?",
    INTENT_ORGANISMOS: "¿Qué organismos concentran mayor gasto?",
    INTENT_FINALIDADES: "¿Qué finalidades presentan mayor desvío?",
    INTENT_ORGANISMO_DETALLE: "desglosá los gastos de Caminos de las Sierras",
    INTENT_ACTOS_DETALLE: "desglosá los actos de Caminos de las Sierras de abril",
}


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


# ----------------------------------------------------------------- el contrato


def test_la_tabla_declara_las_cinco_tools_conocidas():
    assert budget_tool_names() == [
        "get_ejecucion_resumen",
        "top_organismos",
        "get_finalidades_desvio",
        "get_organismo_desglose",
        "get_actos",
    ]


def test_no_hay_keys_ni_nombres_repetidos():
    """Una key duplicada haría que una tool pise a la otra en el contexto, en silencio."""
    assert len({t.key for t in PRESUPUESTO_TOOLS}) == len(PRESUPUESTO_TOOLS)
    assert len({t.name for t in PRESUPUESTO_TOOLS}) == len(PRESUPUESTO_TOOLS)


@pytest.mark.parametrize("tool", PRESUPUESTO_TOOLS, ids=lambda t: t.name)
def test_cada_intent_declarado_es_alcanzable(tool):
    """Una fila cuyo intent no se puede encender es una tool muerta."""
    assert tool.intent in FRASES, f"{tool.name} usa un intent sin frase de prueba"

    assert tool.intent in detect_presupuesto_intents(FRASES[tool.intent])


def test_todas_las_tools_documentan_su_contrato():
    """Las keys son contrato con el FE: `chat-sources.ts` las traduce a etiquetas."""
    assert {t.key for t in PRESUPUESTO_TOOLS} == {
        "ejecucion_resumen", "organismos", "finalidades", "organismo_desglose", "actos",
    }
    for tool in PRESUPUESTO_TOOLS:
        assert tool.description.strip()


# ------------------------------------------------------------------ el router


def _tabla(*specs):
    """Tabla de prueba: `PresupuestoTool` es frozen, así que se reemplaza la tupla."""
    from agents.tools.presupuesto_tools import PresupuestoTool

    return tuple(
        PresupuestoTool(
            name=nombre, intent=intent, key=key, description="prueba", fetch=fetch,
        )
        for nombre, intent, key, fetch in specs
    )


async def test_el_router_ejecuta_solo_lo_pedido(session, monkeypatch):
    from agents.tools import presupuesto_tools as pt

    llamado = []

    async def espia(db, query, resumen):
        llamado.append("si")
        return {"algo": 1}

    monkeypatch.setattr(pt, "PRESUPUESTO_TOOLS", _tabla(
        ("espia", INTENT_RESUMEN, "ejecucion_resumen", espia),
    ))

    ctx = await route_presupuesto(
        session, "¿Qué organismos concentran mayor gasto?", None, {INTENT_ORGANISMOS},
    )

    assert llamado == []  # (a) no se pidió: su tool no corre
    assert ctx == {}


async def test_el_router_una_caida_no_se_lleva_las_otras(session, monkeypatch):
    """El comportamiento previo era todo-o-nada; ahora la falla se acota a su key."""
    from agents.tools import presupuesto_tools as pt

    async def explota(db, query, resumen):
        raise RuntimeError("sin colección")

    async def anda(db, query, resumen):
        return {"total_actos": 1}

    monkeypatch.setattr(pt, "PRESUPUESTO_TOOLS", _tabla(
        ("explota", INTENT_FINALIDADES, "finalidades", explota),
        ("anda", INTENT_ACTOS_DETALLE, "actos", anda),
    ))

    ctx = await route_presupuesto(
        session, "x", None, {INTENT_FINALIDADES, INTENT_ACTOS_DETALLE},
    )

    assert "finalidades" not in ctx
    assert ctx["actos"] == {"total_actos": 1}


async def test_una_tool_vacia_no_agrega_su_key(session, monkeypatch):
    """`data_used` lista lo consultado **y con resultado**, no la intención."""
    from agents.tools import presupuesto_tools as pt

    async def vacio(db, query, resumen):
        return None

    monkeypatch.setattr(pt, "PRESUPUESTO_TOOLS", _tabla(
        ("vacio", INTENT_ACTOS_DETALLE, "actos", vacio),
    ))

    ctx = await route_presupuesto(session, "x", None, {INTENT_ACTOS_DETALLE})

    assert ctx == {}


async def test_el_router_detecta_los_intents_si_no_se_los_pasan(session):
    """Contrato usable de parado: sin `intents` los detecta él."""
    ctx = await route_presupuesto(session, "¿Qué finalidades presentan mayor desvío?", None)

    # Sin Ley cargada en el seed, las finalidades no traen nada: el router no miente.
    assert ctx == {}


# ---------------------------------------------------------------- capabilities


@pytest_asyncio.fixture
async def client():
    import httpx
    from app.api.v1.endpoints import agents as agents_endpoint
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(agents_endpoint.router, prefix="/agents")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_el_health_declara_las_tools_de_presupuesto(client):
    r = await client.get("/agents/status/insight_reporting")

    assert r.status_code == 200
    caps = r.json()["capabilities"]

    for nombre in budget_tool_names():
        assert nombre in caps, f"{nombre} no está declarada en el health"
    # Las tres de siempre siguen ahí: la lista se amplía, no se reemplaza.
    assert {"generate_report", "answer_query", "generate_summary"} <= set(caps)


async def test_los_otros_agentes_no_heredan_las_tools(client):
    for otro in ("document_intelligence", "anomaly_detection"):
        caps = (await client.get(f"/agents/status/{otro}")).json()["capabilities"]
        assert not set(budget_tool_names()) & set(caps)
