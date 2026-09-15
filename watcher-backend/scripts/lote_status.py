#!/usr/bin/env python3
"""Snapshot of bulletin lots in sqlite.db vs disk.  Safe to re-run; read-only.

Usage (from watcher-backend/):

    uv run python scripts/lote_status.py
    uv run python scripts/lote_status.py --watch 20
"""

from __future__ import annotations

import argparse
import calendar
import sqlite3
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402

DB = Path(__file__).resolve().parent.parent / "sqlite.db"
PENDING_STATUSES = (
    "pending",
    "analyzing",
    "extracting",
    "indexing",
    "chunking",
    "cleaning",
    "processing",
    "queued",
)


def _utf8() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass


def month_key(year: int, month: int) -> str:
    return f"{year:04d}{month:02d}"


def remaining_months(today: date | None = None) -> list[str]:
    today = today or date.today()
    months: list[str] = []
    year, month = 2026, 4
    while (year, month) <= (today.year, today.month):
        months.append(month_key(year, month))
        month += 1
        if month > 12:
            year += 1
            month = 1
    return months


def weekday_slot_estimate(ym: str, today: date) -> int:
    year, month = int(ym[:4]), int(ym[4:6])
    last = calendar.monthrange(year, month)[1]
    if (year, month) == (today.year, today.month):
        last = min(last, today.day)
    n_weekdays = sum(
        1
        for day in range(1, last + 1)
        if date(year, month, day).weekday() < 5
    )
    return n_weekdays * 5


def dump(db_path: Path) -> None:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    print(f"DB {db_path}  disk {settings.BOLETINES_DIR}", flush=True)

    print("\n== DB por mes ==", flush=True)
    print(f"{'mes':8} {'completed':>10} {'pending':>8} {'failed':>8} {'otro':>6}", flush=True)
    rows = conn.execute(
        "SELECT substr(date,1,6) ym, status, COUNT(1) n "
        "FROM boletines GROUP BY ym, status ORDER BY ym, status"
    ).fetchall()
    by_month: dict[str, Counter[str]] = {}
    for ym, status, n in rows:
        by_month.setdefault(ym, Counter())[status] += n
    for ym in sorted(by_month):
        c = by_month[ym]
        pending = sum(c[s] for s in PENDING_STATUSES)
        other = sum(c.values()) - c["completed"] - c["failed"] - pending
        print(
            f"{ym:8} {c['completed']:10d} {pending:8d} {c['failed']:8d} {other:6d}",
            flush=True,
        )

    print("\n== Cola viva (no completed / no failed) ==", flush=True)
    live = conn.execute(
        "SELECT id, date, section, filename, status FROM boletines "
        "WHERE status NOT IN ('completed','failed') "
        "ORDER BY date, section"
    ).fetchall()
    if not live:
        print("(vacía)", flush=True)
    else:
        for row in live[:40]:
            print(f"  {row[0]} {row[1]} S{row[2]} {row[3]} {row[4]}", flush=True)
        if len(live) > 40:
            print(f"  ... +{len(live) - 40} más", flush=True)

    print("\n== Failed no justificados ==", flush=True)
    unjust = conn.execute(
        "SELECT date, section, filename, substr(COALESCE(error_message,''),1,90) "
        "FROM boletines WHERE status='failed' "
        "AND COALESCE(error_message,'') NOT LIKE 'justified:%' "
        "ORDER BY date, section"
    ).fetchall()
    if not unjust:
        print("(ninguno — Carnaval 16–17 feb queda justificado)", flush=True)
    else:
        for row in unjust:
            print(f"  {row[0]} S{row[1]} {row[2]} {row[3]}", flush=True)

    disk: Counter[str] = Counter()
    root = settings.BOLETINES_DIR
    if root.exists():
        for pdf in root.rglob("*.pdf"):
            name = pdf.name
            if len(name) >= 6 and name[:6].isdigit():
                disk[name[:6]] += 1
    print("\n== PDFs en disco ==", flush=True)
    if not disk:
        print("(ninguno)", flush=True)
    else:
        for ym, n in sorted(disk.items()):
            print(f"  {ym} {n}", flush=True)

    print("\n== Lotes que faltan (no están en DB) ==", flush=True)
    print(
        "Feb–mar y abril 2026 cerrados en DB. Mayo–hoy no se ingestó. "
        "Gold set recall 44.4%; V.2 = matching antes de más meses.",
        flush=True,
    )
    today = date.today()
    print(f"{'mes':8} {'slots lun–vie (est.)':>22} {'en DB':>8}", flush=True)
    for ym in remaining_months(today):
        in_db = conn.execute(
            "SELECT COUNT(1) FROM boletines WHERE date LIKE ?",
            (f"{ym}%",),
        ).fetchone()[0]
        print(f"{ym:8} {weekday_slot_estimate(ym, today):22d} {in_db:8d}", flush=True)
    conn.close()
    print(flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB)
    parser.add_argument(
        "--watch",
        type=int,
        default=0,
        metavar="SEC",
        help="Refresh every N seconds (0 = once)",
    )
    return parser.parse_args()


def main() -> None:
    _utf8()
    args = parse_args()
    while True:
        dump(args.db)
        if args.watch <= 0:
            return
        print(f"— watch {args.watch}s (Ctrl+C para salir) —", flush=True)
        time.sleep(args.watch)


if __name__ == "__main__":
    main()
