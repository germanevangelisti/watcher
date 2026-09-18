"""Unit tests for app.services.coverage_inventory (V.1.1)."""

from datetime import date

import httpx
import pytest
from app.services.coverage_inventory import (
    DbBoletin,
    ProbeResult,
    classify_status,
    db_boletin_from_row,
    diff_inventory,
    filename_for,
    parse_filename,
    parse_section,
    parse_ymd,
    probe_slot,
    published_set,
    slot_url,
    weekday_dates,
    weekday_slots,
)


class TestParsers:
    def test_filename_roundtrip(self):
        assert filename_for(date(2026, 3, 6), 4) == "20260306_4_Secc.pdf"
        assert parse_filename("20260306_4_Secc.pdf") == (date(2026, 3, 6), 4)

    def test_filename_with_path(self):
        assert parse_filename("2026/03/20260306_1_Secc.pdf") == (date(2026, 3, 6), 1)

    def test_section_shapes(self):
        assert parse_section("S4") == 4
        assert parse_section("1_Secc") == 1
        assert parse_section(5) == 5
        assert parse_section("9") is None

    def test_ymd_and_iso(self):
        assert parse_ymd("20260306") == date(2026, 3, 6)
        assert parse_ymd("2026-03-06") == date(2026, 3, 6)
        assert parse_ymd("nope") is None

    def test_status_buckets(self):
        assert classify_status("completed") == "completed"
        assert classify_status("error") == "failed"
        assert classify_status("failed") == "failed"
        assert classify_status("pending") == "pending"
        assert classify_status("processing") == "pending"
        assert classify_status("weird") == "other"

    def test_canonical_url_matches_fetcher(self):
        url = slot_url(date(2026, 3, 6), 4)
        assert url.endswith("/2026/03/4_Secc_060326.pdf")


class TestWeekdays:
    def test_skips_weekend_like_sync(self):
        # 2026-03-06 Friday, 2026-03-07 Saturday, 2026-03-09 Monday
        days = weekday_dates(date(2026, 3, 6), date(2026, 3, 9))
        assert days == [date(2026, 3, 6), date(2026, 3, 9)]

    def test_slots_are_date_times_five_sections(self):
        slots = weekday_slots(date(2026, 3, 6), date(2026, 3, 6))
        assert slots == [(date(2026, 3, 6), s) for s in range(1, 6)]


def _row(
    id_: int,
    ymd: str,
    section: int,
    status: str,
    fuente: str = "provincial",
    error: str | None = None,
) -> DbBoletin:
    slot_date = parse_ymd(ymd)
    return DbBoletin(
        id=id_,
        filename=filename_for(slot_date, section),
        date=slot_date,
        section=section,
        status=status,
        fuente=fuente,
        error_message=error,
    )


class TestDiffInventory:
    def test_hueco_when_published_missing_from_db(self):
        published = {(date(2026, 3, 6), 1), (date(2026, 3, 6), 2)}
        rows = [_row(1, "20260306", 1, "completed")]
        report = diff_inventory(
            date(2026, 3, 6),
            date(2026, 3, 6),
            rows,
            published=published,
            probe_mode="cached",
        )
        assert [(h.date, h.section) for h in report.huecos] == [(date(2026, 3, 6), 2)]
        assert report.covered_slots == 1
        assert report.pct_sections_present == 50.0
        assert report.pct_published_days_covered == 0.0

    def test_full_day_covered(self):
        published = {(date(2026, 3, 6), s) for s in range(1, 6)}
        rows = [_row(s, "20260306", s, "completed") for s in range(1, 6)]
        report = diff_inventory(
            date(2026, 3, 6),
            date(2026, 3, 6),
            rows,
            published=published,
            probe_mode="cached",
        )
        assert report.huecos == []
        assert report.covered_slots == 5
        assert report.pct_published_days_covered == 100.0
        assert report.pct_sections_present == 100.0

    def test_failed_and_pending_are_listed(self):
        published = {(date(2026, 3, 6), 1), (date(2026, 3, 6), 2)}
        rows = [
            _row(1, "20260306", 1, "failed", error="HTTP 404"),
            _row(2, "20260306", 2, "pending"),
        ]
        report = diff_inventory(
            date(2026, 3, 6),
            date(2026, 3, 6),
            rows,
            published=published,
            probe_mode="cached",
        )
        assert report.db_failed == 1
        assert report.db_pending == 1
        assert report.covered_slots == 0
        assert report.failed_rows[0].id == 1
        assert report.pending_rows[0].id == 2

    def test_feriado_is_unpublished_weekday_not_hueco(self):
        # Carnival Monday 2026-02-16: weekday, no PDF.
        published = {(date(2026, 2, 17), 1)}
        rows = [_row(1, "20260217", 1, "completed")]
        report = diff_inventory(
            date(2026, 2, 16),
            date(2026, 2, 17),
            rows,
            published=published,
            probe_mode="live",
        )
        assert date(2026, 2, 16) in report.unpublished_weekdays
        assert report.huecos == []
        assert report.published_days == 1

    def test_weekdays_assumed_treats_all_slots_as_published(self):
        rows = [_row(1, "20260306", 1, "completed")]
        report = diff_inventory(date(2026, 3, 6), date(2026, 3, 6), rows)
        assert report.probe_mode == "weekdays_assumed"
        assert report.published_slots == 5
        assert len(report.huecos) == 4

    def test_extra_in_db_when_not_published(self):
        published = {(date(2026, 3, 6), 1)}
        rows = [
            _row(1, "20260306", 1, "completed"),
            _row(2, "20260306", 4, "completed"),
        ]
        report = diff_inventory(
            date(2026, 3, 6),
            date(2026, 3, 6),
            rows,
            published=published,
            probe_mode="cached",
        )
        assert [r.id for r in report.extra_in_db] == [2]

    def test_skips_municipal_fuente(self):
        rows = [
            DbBoletin(
                id=1,
                filename="capital_20260306.pdf",
                date=date(2026, 3, 6),
                section=1,
                status="completed",
                fuente="municipal_capital",
            )
        ]
        report = diff_inventory(
            date(2026, 3, 6),
            date(2026, 3, 6),
            rows,
            published=set(),
            probe_mode="cached",
        )
        assert report.db_total == 0

    def test_markdown_mentions_huecos(self):
        published = {(date(2026, 3, 6), 1)}
        report = diff_inventory(
            date(2026, 3, 6),
            date(2026, 3, 6),
            [],
            published=published,
            probe_mode="cached",
        )
        md = report.to_markdown()
        assert "20260306_1_Secc.pdf" in md
        assert "Huecos" in md
        assert "## Lectura" in md
        assert "CGE/SIGAF" in md


class TestDbRowLoader:
    def test_from_mapping_recovers_date_from_filename(self):
        row = db_boletin_from_row(
            {
                "id": 9,
                "filename": "20260306_4_Secc.pdf",
                "date": None,
                "section": "4_Secc",
                "status": "completed",
                "fuente": "provincial",
                "error_message": None,
            }
        )
        assert row.date == date(2026, 3, 6)
        assert row.section == 4


class TestProbe:
    @pytest.mark.asyncio
    async def test_pdf_content_type_counts_as_published(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers={"content-type": "application/pdf"},
                content=b"%PDF-1.4 fake",
            )

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            result = await probe_slot(client, date(2026, 3, 6), 4)
        assert result.published is True
        assert result.http_status == 200

    @pytest.mark.asyncio
    async def test_html_200_is_not_published(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                content=b"<html>not found</html>",
            )

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            result = await probe_slot(client, date(2026, 3, 6), 4)
        assert result.published is False

    @pytest.mark.asyncio
    async def test_404_is_not_published(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, content=b"missing")

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            result = await probe_slot(client, date(2026, 2, 16), 1)
        assert result.published is False
        assert result.http_status == 404

    def test_published_set_filters(self):
        results = [
            ProbeResult(date(2026, 3, 6), 1, "u", True),
            ProbeResult(date(2026, 3, 6), 2, "u", False),
        ]
        assert published_set(results) == {(date(2026, 3, 6), 1)}
