"""
Unit tests for the IngestionRun SQLAlchemy model.

Tests the model fields, defaults, and __repr__ without hitting a database.
"""



from app.db.models import IngestionRun


class TestIngestionRunModel:
    def test_tablename(self):
        assert IngestionRun.__tablename__ == "ingestion_runs"

    def test_repr_contains_key_fields(self):
        run = IngestionRun(pipeline_name="provincial_boletin", status="loaded")
        r = repr(run)
        assert "provincial_boletin" in r
        assert "loaded" in r

    def test_column_names_present(self):
        columns = {c.key for c in IngestionRun.__table__.columns}
        expected = {
            "id", "pipeline_name", "source_id", "status",
            "rows_in", "rows_loaded", "error", "started_at", "finished_at",
        }
        assert expected.issubset(columns)

    def test_status_column_has_default(self):
        col = IngestionRun.__table__.columns["status"]
        assert col.default is not None or col.server_default is not None or col.nullable is False

    def test_pipeline_name_is_indexed(self):
        col = IngestionRun.__table__.columns["pipeline_name"]
        assert col.index is True or any(
            "pipeline_name" in str(idx.columns)
            for idx in IngestionRun.__table__.indexes
        )
