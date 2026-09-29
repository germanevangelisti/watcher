"""Tests for the Nación / Provincia / Ciudad hierarchy in DocumentTracker (fix-hierarchy-load).

Root causes covered:
  (a) the overview emitted the config key (`nacion`, ...) as `jurisdiction_code`, so
      the FE fell back to `municipio` for all three rows;
  (c) Nación had `jurisdiction_id: null`, and `get_documents_by_jurisdiction(None)`
      means "no filter", so Nación's summary swallowed every document (b).

Run from watcher-backend/:
    uv run pytest tests/tests/test_document_tracker_hierarchy.py -v
"""

import httpx
import pytest
import pytest_asyncio
from app.api.v1.endpoints import compliance as compliance_endpoint
from app.db.database import get_db
from app.db.models import Base, Jurisdiccion, RequiredDocument
from app.services.document_tracker import DocumentTracker
from fastapi import FastAPI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

NACION_ID = 100


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        yield db

    await engine.dispose()


def _config_counts():
    config = DocumentTracker(None).load_config()["jurisdictions"]
    return {key: len(j["documents"]) for key, j in config.items()}


def test_config_has_no_null_jurisdiction_ids_and_declares_levels():
    config = DocumentTracker(None).load_config()["jurisdictions"]
    assert config["nacion"]["jurisdiction_id"] == NACION_ID
    for key, juris in config.items():
        assert juris["jurisdiction_id"] is not None, key
    assert {k: j["jurisdiction_level"] for k, j in config.items()} == {
        "nacion": "nacion",
        "cordoba_provincia": "provincia",
        "cordoba_ciudad": "municipio",
    }


async def test_sync_seeds_nacion_with_stable_id(session):
    synced = await DocumentTracker(session).sync_required_documents()
    assert synced == _config_counts()

    nacion = await session.get(Jurisdiccion, NACION_ID)
    assert nacion is not None
    assert nacion.nombre == "Nación Argentina"
    assert nacion.tipo == "nacion"

    orphans = await session.execute(
        select(func.count(RequiredDocument.id)).where(RequiredDocument.jurisdiccion_id.is_(None))
    )
    assert orphans.scalar() == 0


async def test_sync_is_idempotent(session):
    tracker = DocumentTracker(session)
    await tracker.sync_required_documents()
    await tracker.sync_required_documents()

    total = await session.execute(select(func.count(RequiredDocument.id)))
    assert total.scalar() == sum(_config_counts().values())
    jur = await session.execute(select(func.count(Jurisdiccion.id)))
    assert jur.scalar() == 3


async def test_sync_adopts_legacy_null_rows_for_nacion(session):
    # A sync made with the old config left Nación's docs with jurisdiccion_id NULL
    session.add(RequiredDocument(
        jurisdiccion_id=None, document_type="presupuesto_anual",
        document_name="Presupuesto Nacional 2025", expected_format="pdf", status="processed",
    ))
    await session.commit()

    await DocumentTracker(session).sync_required_documents()

    rows = (await session.execute(
        select(RequiredDocument).where(RequiredDocument.document_name == "Presupuesto Nacional 2025")
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].jurisdiccion_id == NACION_ID
    assert rows[0].status == "processed"  # sync never resets state


async def test_overview_counts_each_jurisdiction_separately(session):
    tracker = DocumentTracker(session)
    await tracker.sync_required_documents()

    overview = {j["jurisdiction_key"]: j for j in await tracker.get_all_jurisdictions_overview()}
    counts = _config_counts()

    assert {k: j["total_documents"] for k, j in overview.items()} == counts
    assert overview["nacion"]["jurisdiction_id"] == NACION_ID
    assert overview["nacion"]["jurisdiction_code"] == "AR"
    assert overview["cordoba_provincia"]["jurisdiction_code"] == "AR-X"
    assert overview["cordoba_ciudad"]["jurisdiction_code"] == "AR-X-CBA"
    assert [j["jurisdiction_level"] for j in overview.values()] == ["nacion", "provincia", "municipio"]
    for j in overview.values():
        assert sum(t["total"] for t in j["by_type"].values()) == j["total_documents"]
        assert j["missing"] == j["total_documents"]


async def test_overview_without_sync_does_not_merge_all_docs_into_nacion(session):
    # Rows exist for provincia but Nación was never seeded: Nación must be 0, not "all"
    session.add(Jurisdiccion(id=1, nombre="Provincia de Córdoba", tipo="provincia"))
    session.add(RequiredDocument(
        jurisdiccion_id=1, document_type="presupuesto_anual",
        document_name="x", expected_format="pdf", status="processed",
    ))
    await session.commit()

    overview = {j["jurisdiction_key"]: j for j in await DocumentTracker(session).get_all_jurisdictions_overview()}
    assert overview["nacion"]["jurisdiction_id"] is None
    assert overview["nacion"]["total_documents"] == 0
    assert overview["cordoba_provincia"]["total_documents"] == 1
    assert overview["cordoba_provincia"]["processed"] == 1


@pytest.mark.asyncio
async def test_overview_endpoint_contract(session):
    await DocumentTracker(session).sync_required_documents()

    app = FastAPI()
    app.include_router(compliance_endpoint.router, prefix="/api/v1/compliance")
    app.dependency_overrides[get_db] = lambda: session

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/compliance/documents/overview")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_documents"] == sum(_config_counts().values())
    assert sum(j["total_documents"] for j in body["jurisdictions"]) == body["total_documents"]
    levels = {j["jurisdiction_code"]: j["jurisdiction_level"] for j in body["jurisdictions"]}
    assert levels == {"AR": "nacion", "AR-X": "provincia", "AR-X-CBA": "municipio"}
