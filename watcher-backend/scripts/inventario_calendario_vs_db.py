#!/usr/bin/env python3
"""V.1.1 — inventario calendario boletinoficial.cba.gov.ar vs tabla `boletines`.

Compares weekday×section slots against what `sync` stored in sqlite.  Optionally
probes the canonical PDF URLs so feriados are not reported as lost bulletins.

Usage (from watcher-backend/):

    uv run python scripts/inventario_calendario_vs_db.py
    uv run python scripts/inventario_calendario_vs_db.py --probe
    uv run python scripts/inventario_calendario_vs_db.py --from-probes path.json

Does not write sqlite.db.  Markdown lands in knowledgebase/current/.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.coverage_inventory import (
    CoverageReport,
    db_boletin_from_row,
    diff_inventory,
    dump_probes,
    load_probes,
    parse_ymd,
    probe_slots,
    published_set,
    weekday_slots,
)

DB_PATH = Path(__file__).resolve().parent.parent / "sqlite.db"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_MD = REPO_ROOT / "knowledgebase" / "current" / "cobertura-calendario.md"
DEFAULT_JSON = REPO_ROOT / "watcher-doc" / "data" / "2026" / "cobertura_calendario.json"

LOAD_SQL = """
SELECT id, filename, date, section, status, fuente, error_message
FROM boletines
"""


def infer_range(rows, fallback_start: date, fallback_end: date) -> tuple[date, date]:
    dates = [r.date for r in rows if r.date is not None]
    if not dates:
        return fallback_start, fallback_end
    return min(dates), max(dates)


def load_rows(db_path: Path) -> list:
    if not db_path.exists():
        raise SystemExit(f"DB no encontrada: {db_path}")
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(LOAD_SQL)
        return [db_boletin_from_row(row) for row in cur.fetchall()]
    finally:
        conn.close()


def report_to_dict(report: CoverageReport) -> dict:
    return {
        "start": report.start.isoformat(),
        "end": report.end.isoformat(),
        "probe_mode": report.probe_mode,
        "weekday_days": report.weekday_days,
        "weekday_slots": report.weekday_slots,
        "published_days": report.published_days,
        "published_slots": report.published_slots,
        "db_total": report.db_total,
        "db_completed": report.db_completed,
        "db_failed": report.db_failed,
        "db_pending": report.db_pending,
        "db_other": report.db_other,
        "covered_slots": report.covered_slots,
        "pct_published_days_covered": report.pct_published_days_covered,
        "pct_sections_present": report.pct_sections_present,
        "huecos": [
            {"date": s.date.isoformat(), "section": s.section, "filename": s.filename}
            for s in report.huecos
        ],
        "failed": [
            {
                "id": r.id,
                "date": r.date.isoformat() if r.date else None,
                "section": r.section,
                "status": r.status,
                "filename": r.filename,
                "error_message": r.error_message,
            }
            for r in report.failed_rows
        ],
        "pending": [
            {
                "id": r.id,
                "date": r.date.isoformat() if r.date else None,
                "section": r.section,
                "status": r.status,
                "filename": r.filename,
            }
            for r in report.pending_rows
        ],
        "unpublished_weekdays": [d.isoformat() for d in report.unpublished_weekdays],
        "sections_present_by_day": report.sections_present_by_day,
        "notes": report.notes,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--start", type=str, default=None, help="YYYY-MM-DD")
    parser.add_argument("--end", type=str, default=None, help="YYYY-MM-DD")
    parser.add_argument(
        "--probe",
        action="store_true",
        help="HEAD/GET the official PDF URLs (live source of truth)",
    )
    parser.add_argument("--from-probes", type=Path, default=None)
    parser.add_argument("--write-probes", type=Path, default=None)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--concurrency", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    args = parse_args()
    rows = load_rows(args.db)
    fallback_start, fallback_end = infer_range(rows, date(2026, 2, 1), date(2026, 3, 31))
    start = parse_ymd(args.start) or fallback_start
    end = parse_ymd(args.end) or fallback_end

    notes = [
        "Inventario sobre lo que `sync` persistió en `boletines`, no sobre disco.",
        "No mezclar con ejecución CGE/SIGAF.",
    ]
    published = None
    probe_mode = "weekdays_assumed"

    if args.from_probes:
        probes = load_probes(args.from_probes.read_text(encoding="utf-8"))
        published = published_set(probes)
        probe_mode = "cached"
        notes.append(f"Probes leídos de {args.from_probes}")
    elif args.probe:
        slots = weekday_slots(start, end)
        print(f"Probe live de {len(slots)} URLs ({start} -> {end})...", flush=True)
        probes = asyncio.run(probe_slots(slots, concurrency=args.concurrency))
        n_ok = sum(1 for p in probes if p.published)
        n_err = sum(1 for p in probes if p.error)
        print(f"Publicados: {n_ok}/{len(probes)}  errores HTTP: {n_err}", flush=True)
        published = published_set(probes)
        probe_mode = "live"
        notes.append("Probe live contra boletinoficial.cba.gov.ar (UA de navegador).")
        if args.write_probes:
            args.write_probes.parent.mkdir(parents=True, exist_ok=True)
            args.write_probes.write_text(dump_probes(probes), encoding="utf-8")
            notes.append(f"Probes crudos en {args.write_probes}")
        elif args.json_out:
            probe_path = args.json_out.with_name("cobertura_probes.json")
            probe_path.parent.mkdir(parents=True, exist_ok=True)
            probe_path.write_text(dump_probes(probes), encoding="utf-8")
            notes.append(f"Probes crudos en {probe_path}")
        if n_ok == 0:
            notes.append(
                "CERO PDFs detectados — el probe falló o CloudFront bloqueó. "
                "El diff usa el set vacío de publicados; revisar probes."
            )

    report = diff_inventory(
        start,
        end,
        rows,
        published=published,
        probe_mode=probe_mode,
        notes=notes,
    )
    markdown = report.to_markdown()
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.write_text(markdown, encoding="utf-8")
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(
        json.dumps(report_to_dict(report), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(markdown)
    print(f"\nWrote {args.md_out}")
    print(f"Wrote {args.json_out}")


if __name__ == "__main__":
    main()
