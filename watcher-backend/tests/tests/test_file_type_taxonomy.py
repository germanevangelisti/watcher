"""Tests de la taxonomía de tipos de archivo y su mapping legal (fix-taxonomia-tipos).

Decisión PO (2026-09-28): "Documentos por tipo" pasa a tener el **tipo de archivo**
(`expected_format`) como eje primario, con la categoría legal (`document_type`) como
mapping secundario. El eje legal (`by_type`) **no** se rompe: se mantiene y se le
agrega `by_file_type` al lado.

Invariantes que estos tests protegen:
  - cada bucket de archivo suma lo mismo que el total de la jurisdicción;
  - `legal_categories` suma exactamente `total` del bucket (un doc = un bucket);
  - la taxonomía cubre **todos** los `expected_format` del config (sin formatos
    inventados ni typo'd) y se publica ordenada;
  - un formato fuera de la taxonomía **pasa igual** (extensible), no se descarta.

Run from watcher-backend/:
    uv run pytest tests/tests/test_file_type_taxonomy.py -v
"""

import httpx
import pytest_asyncio
from app.api.v1.endpoints import compliance as compliance_endpoint
from app.db.database import get_db
from app.db.models import Base, RequiredDocument
from app.services.document_tracker import DocumentTracker
from app.services.file_type_taxonomy import (
    FILE_TYPE_LABELS,
    file_type_label,
    file_type_order,
    file_type_taxonomy,
)
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Conteos por tipo de archivo del config (22 documentos), por jurisdicción.
EXPECTED_BY_FILE_TYPE = {
    "nacion": {"pdf": 2, "csv": 2, "xlsx": 1},
    "cordoba_provincia": {"pdf": 4, "csv": 6, "xlsx": 2},
    "cordoba_ciudad": {"pdf": 3, "csv": 1, "xlsx": 1},
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


def _config_jurisdictions():
    return DocumentTracker(None).load_config()["jurisdictions"]


def _format_counts(juris_data):
    counts = {}
    for doc in juris_data["documents"]:
        counts[doc["expected_format"]] = counts.get(doc["expected_format"], 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Taxonomía
# ---------------------------------------------------------------------------

def test_taxonomy_declares_the_minimum_formats():
    assert {"pdf", "csv", "xlsx"} <= set(FILE_TYPE_LABELS)


def test_taxonomy_covers_every_format_in_the_config():
    """Un formato en el config que no esté en la taxonomía es un agujero del eje."""
    for key, juris in _config_jurisdictions().items():
        for file_type in _format_counts(juris):
            assert file_type in FILE_TYPE_LABELS, f"{key}: '{file_type}' sin entrada en la taxonomía"


def test_taxonomy_is_extensible_and_orders_unknown_last():
    assert file_type_label("docx") == "DOCX"  # pasa igual, no se descarta
    assert file_type_order("pdf") < file_type_order("csv") < file_type_order("xlsx")
    assert file_type_order("docx") > file_type_order("xlsx")


# ---------------------------------------------------------------------------
# Agregación
# ---------------------------------------------------------------------------

async def test_summary_aggregates_by_file_type_and_keeps_the_legal_mapping(session):
    tracker = DocumentTracker(session)
    await tracker.sync_required_documents()

    for key, juris in _config_jurisdictions().items():
        summary = await tracker.get_jurisdiction_summary(juris["jurisdiction_id"])
        by_file_type = summary["by_file_type"]

        assert {ft: b["total"] for ft, b in by_file_type.items()} == EXPECTED_BY_FILE_TYPE[key]
        # Un documento cae en un solo bucket: los dos ejes tienen que cerrar.
        assert sum(b["total"] for b in by_file_type.values()) == summary["total"]
        assert sum(b["total"] for b in summary["by_type"].values()) == summary["total"]

        for file_type, bucket in by_file_type.items():
            assert sum(bucket["legal_categories"].values()) == bucket["total"], file_type
            assert bucket["missing"] == bucket["total"]  # recién sincronizado
            for legal in bucket["legal_categories"]:
                assert legal in summary["by_type"], f"{file_type}: categoría legal desconocida {legal}"


async def test_legal_axis_is_not_broken_and_both_axes_agree(session):
    tracker = DocumentTracker(session)
    await tracker.sync_required_documents()
    summary = await tracker.get_jurisdiction_summary(1)

    # El contrato viejo sigue vivo y con los mismos totales que el eje nuevo.
    assert summary["by_type"]["ejecucion_trimestral"]["total"] == 4
    assert summary["by_type"]["empleo_publico"]["total"] == 2
    assert sum(b["total"] for b in summary["by_type"].values()) == summary["total"] == 12

    # El mapping archivo -> categoría legal, con los 6 CSV de provincia.
    assert summary["by_file_type"]["csv"]["legal_categories"] == {
        "ejecucion_trimestral": 4,   # Q1/Q4, Devengado y Caja
        "deuda_flotante": 1,
        "servicios_deuda": 1,
    }
    assert summary["by_file_type"]["xlsx"]["legal_categories"] == {"empleo_publico": 2}
    assert summary["by_file_type"]["pdf"]["legal_categories"] == {
        "presupuesto_anual": 1,
        "presupuesto_plurianual": 1,
        "deuda_publica": 1,
        "cuenta_inversion": 1,
    }


async def test_buckets_come_back_in_taxonomy_order(session):
    tracker = DocumentTracker(session)
    await tracker.sync_required_documents()
    summary = await tracker.get_jurisdiction_summary(1)

    assert list(summary["by_file_type"]) == ["pdf", "csv", "xlsx"]


async def test_out_of_taxonomy_format_is_kept_not_dropped(session):
    await DocumentTracker(session).sync_required_documents()
    session.add(RequiredDocument(
        jurisdiccion_id=1, document_type="otro", document_name="Documento DOCX",
        expected_format="docx", status="missing",
    ))
    await session.commit()

    summary = await DocumentTracker(session).get_jurisdiction_summary(1)
    assert summary["by_file_type"]["docx"]["total"] == 1
    # Ordenado después de la taxonomía.
    assert list(summary["by_file_type"])[-1] == "docx"
    assert sum(b["total"] for b in summary["by_file_type"].values()) == summary["total"]


async def test_overview_exposes_by_file_type_and_the_taxonomy(session):
    await DocumentTracker(session).sync_required_documents()

    app = FastAPI()
    app.include_router(compliance_endpoint.router, prefix="/api/v1/compliance")
    app.dependency_overrides[get_db] = lambda: session

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/compliance/documents/overview")

    assert resp.status_code == 200
    body = resp.json()

    assert body["file_type_taxonomy"] == [
        {"key": "pdf", "label": "PDF"},
        {"key": "csv", "label": "CSV"},
        {"key": "xlsx", "label": "XLSX"},
    ]
    assert file_type_taxonomy()[0] == {"key": "pdf", "label": "PDF"}

    for juris in body["jurisdictions"]:
        key = juris["jurisdiction_key"]
        assert {ft: b["total"] for ft, b in juris["by_file_type"].items()} == EXPECTED_BY_FILE_TYPE[key]
        # El eje legal sigue viajando en la respuesta (contrato viejo intacto).
        assert juris["by_type"]


async def test_overview_without_sync_still_reports_empty_file_types(session):
    """Sin fila en DB la jurisdicción va en cero — y con los dos ejes vacíos."""
    overview = {j["jurisdiction_key"]: j for j in await DocumentTracker(session).get_all_jurisdictions_overview()}
    for juris in overview.values():
        assert juris["by_file_type"] == {}
        assert juris["by_type"] == {}
        assert juris["total_documents"] == 0
