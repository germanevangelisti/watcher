#!/usr/bin/env python3
"""Probe + download + register one calendar month.  Does not run the LLM.

Skips slots already in `boletines`.  Does not touch Carnival `justified:` rows.

Usage (from watcher-backend/):

    uv run python scripts/ingest_month.py --month 202604
    uv run python scripts/ingest_month.py --month 202604 --no-download
"""

from __future__ import annotations

import argparse
import asyncio
import calendar
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from app.services.coverage_inventory import (  # noqa: E402
    filename_for,
    probe_slots,
    published_set,
    slot_url,
    weekday_slots,
)
from app.services.hash_utils import compute_sha256  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from download_published_slots import download_slots  # noqa: E402

DB = Path(__file__).resolve().parent.parent / "sqlite.db"


def _utf8() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass


def month_range(ym: str) -> tuple[date, date]:
    if len(ym) != 6 or not ym.isdigit():
        raise SystemExit(f"--month debe ser YYYYMM, vino {ym!r}")
    year, month = int(ym[:4]), int(ym[4:6])
    last = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last)


def find_pdf(filename: str) -> Path | None:
    hits = list(settings.BOLETINES_DIR.rglob(filename))
    return hits[0] if hits else None


def register_slot(cur: sqlite3.Cursor, slot_date: date, section: int) -> str:
    filename = filename_for(slot_date, section)
    existing = cur.execute(
        "SELECT id FROM boletines WHERE filename=?", (filename,)
    ).fetchone()
    if existing:
        return "exists"
    pdf = find_pdf(filename)
    if not pdf:
        return "missing_pdf"
    now = datetime.utcnow().isoformat(sep=" ", timespec="seconds")
    cur.execute(
        """
        INSERT INTO boletines
        (filename, date, section, status, created_at, updated_at,
         file_hash, file_size_bytes, fuente, origin, source_url)
        VALUES (?, ?, ?, 'pending', ?, ?, ?, ?, 'provincial', 'synced', ?)
        """,
        (
            filename,
            slot_date.strftime("%Y%m%d"),
            str(section),
            now,
            now,
            compute_sha256(pdf),
            pdf.stat().st_size,
            slot_url(slot_date, section),
        ),
    )
    return "inserted"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", required=True, help="YYYYMM")
    parser.add_argument("--db", type=Path, default=DB)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Only probe + register PDFs already on disk",
    )
    return parser.parse_args()


async def run(args: argparse.Namespace) -> None:
    start, end = month_range(args.month)
    candidates = weekday_slots(start, end)
    print(
        f"Probe {args.month} {start}→{end}  {len(candidates)} slots lun–vie",
        flush=True,
    )
    probes = await probe_slots(candidates, concurrency=args.concurrency)
    published = sorted(published_set(probes))
    n_err = sum(1 for p in probes if p.error)
    print(
        f"Publicados {len(published)}/{len(probes)}  errores HTTP {n_err}",
        flush=True,
    )
    if not published:
        raise SystemExit(
            "Cero PDFs publicados: CloudFront bloqueó o el mes no salió. "
            "Abortar sin registrar."
        )

    conn = sqlite3.connect(args.db)
    already = {
        row[0]
        for row in conn.execute("SELECT filename FROM boletines").fetchall()
    }
    missing = [
        slot for slot in published if filename_for(*slot) not in already
    ]
    print(f"Ya en DB {len(published) - len(missing)}  a bajar/registrar {len(missing)}", flush=True)
    conn.close()

    if missing and not args.no_download:
        print(f"Descarga → {settings.BOLETINES_DIR}", flush=True)
        await download_slots(missing, settings.BOLETINES_DIR)

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()
    counts = {"inserted": 0, "exists": 0, "missing_pdf": 0}
    for slot_date, section in published:
        counts[register_slot(cur, slot_date, section)] += 1
    conn.commit()
    conn.close()
    print(
        f"register inserted={counts['inserted']} exists={counts['exists']} "
        f"missing_pdf={counts['missing_pdf']}",
        flush=True,
    )
    print(
        f"Siguiente: uv run python scripts/process_pending.py --month {args.month}",
        flush=True,
    )


def main() -> None:
    _utf8()
    args = parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
