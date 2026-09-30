"""Tests del contrato `applicable_laws = { name, official_url }[]` (fix-leyes-links).

La decisión PO (2026-09-28) fija dos cosas que estos tests protegen:

  1. la **forma** del contrato (`{name, official_url}`, con `official_url` siempre
     presente — `null` cuando no hay fuente oficial verificable);
  2. el **set de leyes** no se toca: solo se le agregan URLs.

Y la regla dura derivada: **no inventar links**. Toda URL cargada tiene que apuntar
a un dominio oficial (`*.gob.ar` / `*.gov.ar`); una ley sin fuente queda en `null`
y la UI muestra el nombre + "sin URL".

Run from watcher-backend/:
    uv run pytest tests/tests/test_applicable_laws.py -v
"""

import httpx
import pytest_asyncio
from app.api.v1.endpoints import compliance as compliance_endpoint
from app.db.database import get_db
from app.db.models import Base
from app.schemas.compliance import JurisdictionDocumentsSummary
from app.services.document_tracker import DocumentTracker
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Set de leyes congelado por la decisión PO 2026-09-28: el cambio es de estructura
# + URLs, nunca del conjunto. Si este test falla, alguien agregó/quitó una ley.
LOCKED_LAW_NAMES = {
    "nacion": [
        "Ley 27.275 (Acceso a la Información Pública)",
        "Decreto 780/2024 (Reglamentación)",
        "Ley 24.156 (Administración Financiera)",
    ],
    "cordoba_provincia": [
        "Ley 25.917 Art. 7 (Federal de Responsabilidad Fiscal)",
        # La 10.471 (2017) adhiere al Capítulo IX de la Ley 27.341, no a la 25.917
        # (verificado contra el texto del B.O. y la tabla de adhesiones del Consejo
        # Federal de Responsabilidad Fiscal). Etiqueta corregida el 2026-09-30.
        "Ley Provincial 10.471 (Adhesión al Capítulo IX de la Ley 27.341)",
        "Ley Provincial 8803 (Transparencia y Acceso a la Información)",
    ],
    "cordoba_ciudad": [
        "Ley 25.917 Art. 7 (aplica por adhesión provincial)",
        "Ordenanza Municipal de Transparencia",
    ],
}


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        yield db

    await engine.dispose()


def _config():
    return DocumentTracker(None).load_config()


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def test_config_laws_are_name_url_objects():
    jurisdictions = _config()["jurisdictions"]
    for key, juris in jurisdictions.items():
        for law in juris["applicable_laws"]:
            assert isinstance(law, dict), f"{key}: la ley sigue siendo un string suelto"
            assert set(law) == {"name", "official_url"}, f"{key}: campos inesperados en {law}"
            assert isinstance(law["name"], str) and law["name"].strip(), key
            # `official_url` siempre está presente (null explícito = "no hay fuente"),
            # nunca ausente ni cadena vacía.
            assert law["official_url"] is None or (
                isinstance(law["official_url"], str) and law["official_url"].strip()
            ), f"{key}: URL vacía en {law['name']}"


def test_config_law_set_is_unchanged():
    jurisdictions = _config()["jurisdictions"]
    assert {
        key: [law["name"] for law in juris["applicable_laws"]]
        for key, juris in jurisdictions.items()
    } == LOCKED_LAW_NAMES


def test_config_urls_point_to_official_domains_only():
    """La regla "no inventar": ninguna URL fuera de un dominio oficial."""
    checked = 0
    for key, juris in _config()["jurisdictions"].items():
        for law in juris["applicable_laws"]:
            url = law["official_url"]
            if url is None:
                continue
            checked += 1
            assert url.startswith("https://"), f"{key}: URL no segura en {law['name']}"
            host = url.split("/")[2]
            assert host.endswith((".gob.ar", ".gov.ar")), (
                f"{key}: {law['name']} apunta a un dominio no oficial ({host})"
            )

    # Y que el set no se haya vaciado por accidente: al menos una URL real cargada.
    assert checked >= 5


def test_config_version_marks_the_breaking_shape_change():
    parts = tuple(int(p) for p in _config()["version"].split("."))
    assert parts >= (1, 1, 0), "el cambio de forma de applicable_laws exige bump de versión"


# ---------------------------------------------------------------------------
# Overview / endpoint
# ---------------------------------------------------------------------------

async def test_overview_passes_laws_through_with_urls(session):
    tracker = DocumentTracker(session)
    await tracker.sync_required_documents()

    jurisdictions = _config()["jurisdictions"]
    overview = {j["jurisdiction_key"]: j for j in await tracker.get_all_jurisdictions_overview()}

    for key, summary in overview.items():
        assert summary["applicable_laws"] == jurisdictions[key]["applicable_laws"], key

    nacion = {law["name"]: law for law in overview["nacion"]["applicable_laws"]}
    assert nacion["Ley 27.275 (Acceso a la Información Pública)"]["official_url"].endswith("265949/norma.htm")
    # Sin fuente oficial verificable -> None, no cadena vacía ni URL inventada.
    provincia = {law["name"]: law for law in overview["cordoba_provincia"]["applicable_laws"]}
    assert provincia["Ley Provincial 8803 (Transparencia y Acceso a la Información)"]["official_url"] is None


async def test_overview_endpoint_serves_name_and_official_url(session):
    await DocumentTracker(session).sync_required_documents()

    app = FastAPI()
    app.include_router(compliance_endpoint.router, prefix="/api/v1/compliance")
    app.dependency_overrides[get_db] = lambda: session

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/compliance/documents/overview")

    assert resp.status_code == 200
    for juris in resp.json()["jurisdictions"]:
        for law in juris["applicable_laws"]:
            assert set(law) == {"name", "official_url"}
            assert law["official_url"] is None or law["official_url"].startswith("https://")


def test_legacy_string_laws_are_coerced_not_rejected():
    """Un config viejo (`string[]`) no puede tumbar el endpoint con un 500."""
    summary = JurisdictionDocumentsSummary.model_validate({
        "jurisdiction_code": "AR",
        "jurisdiction_name": "Nación Argentina",
        "applicable_laws": ["Ley vieja sin estructura"],
        "total_documents": 0,
        "missing": 0,
        "downloaded": 0,
        "processed": 0,
        "coverage_percentage": 0.0,
        "by_type": {},
    })
    assert summary.applicable_laws[0].name == "Ley vieja sin estructura"
    assert summary.applicable_laws[0].official_url is None


def test_law_without_url_is_not_given_an_empty_string():
    """`official_url` ausente y `official_url: null` significan lo mismo: sin URL."""
    for payload in ({"name": "Ley X"}, {"name": "Ley X", "official_url": None}):
        summary = JurisdictionDocumentsSummary.model_validate({
            "jurisdiction_code": "AR",
            "jurisdiction_name": "Nación Argentina",
            "applicable_laws": [payload],
            "total_documents": 0,
            "missing": 0,
            "downloaded": 0,
            "processed": 0,
            "coverage_percentage": 0.0,
            "by_type": {},
        })
        assert summary.applicable_laws[0].official_url is None
