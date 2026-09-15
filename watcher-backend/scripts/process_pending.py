#!/usr/bin/env python3
"""Run LocalPro pipeline on pending boletines for one or more months.

Does not touch `failed` rows with error_message `justified:…` (Carnaval).
ChromaDB off so a missing Google key cannot abort analysis.

Usage (from watcher-backend/):

    uv run python scripts/process_pending.py --month 202604
    uv run python scripts/process_pending.py --month 202604 --section 4
    uv run python scripts/process_pending.py --from 202604 --to 202609
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
BACKEND = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv

    load_dotenv(REPO / ".env")
    load_dotenv(BACKEND / ".env")
except ImportError:
    pass

os.environ["HARDWARE_PROFILE"] = "local"
os.environ["INTELLIGENCE_PROVIDER"] = "local"
os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:11434"
os.environ["OLLAMA_MODEL"] = "qwen2.5:7b"
os.environ["LLM_MAX_CONCURRENT"] = "1"
os.environ["OLLAMA_TIMEOUT_S"] = "480"
os.environ["OLLAMA_NUM_CTX"] = "4096"
os.environ["ANALYSIS_MAX_FRAGMENTS"] = "4"
os.chdir(BACKEND)

sys.path.insert(0, str(BACKEND))

from app.api.v1.endpoints.pipeline import (  # noqa: E402
    _process_document_pipeline,
)
from app.schemas.pipeline import IndexingConfig, PipelineConfig  # noqa: E402
from app.services.intelligence_provider import (  # noqa: E402
    resolve_intelligence_tier,
)

DB = BACKEND / "sqlite.db"
PENDING = (
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


def month_start(ym: str) -> str:
    if len(ym) != 6 or not ym.isdigit():
        raise SystemExit(f"mes debe ser YYYYMM, vino {ym!r}")
    return f"{ym}01"


def month_end_exclusive(ym: str) -> str:
    year, month = int(ym[:4]), int(ym[4:6])
    if month == 12:
        nxt = date(year + 1, 1, 1)
    else:
        nxt = date(year, month + 1, 1)
    return nxt.strftime("%Y%m%d")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", help="YYYYMM (inclusive)")
    parser.add_argument("--from", dest="date_from", help="YYYYMM start")
    parser.add_argument("--to", dest="date_to", help="YYYYMM end inclusive")
    parser.add_argument("--section", type=str, default=None, help="1..5")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--order",
        type=str,
        default="4,5,1,3,2",
        help="Section priority (gasto first)",
    )
    parser.add_argument("--db", type=Path, default=DB)
    parser.add_argument(
        "--doc-timeout",
        type=int,
        default=600,
        help="Seconds per PDF before skip",
    )
    parser.add_argument(
        "--retry-timeouts",
        action="store_true",
        help="Also pick failed rows whose error starts with 'timeout '",
    )
    return parser.parse_args()


def date_bounds(args: argparse.Namespace) -> tuple[str, str]:
    if args.month and (args.date_from or args.date_to):
        raise SystemExit("Usá --month o --from/--to, no ambos")
    if args.month:
        return month_start(args.month), month_end_exclusive(args.month)
    start_ym = args.date_from or "202604"
    end_ym = args.date_to or args.date_from or "202604"
    return month_start(start_ym), month_end_exclusive(end_ym)


def pending_rows(
    db_path: Path,
    start: str,
    end_excl: str,
    section: str | None,
    limit: int,
    order: str,
    retry_timeouts: bool,
) -> list[tuple]:
    placeholders = ",".join("?" * len(PENDING))
    sql = (
        "SELECT id, filename, section FROM boletines "
        f"WHERE date >= ? AND date < ? AND status IN ({placeholders}) "
    )
    params: list = [start, end_excl, *PENDING]
    if retry_timeouts:
        sql = (
            "SELECT id, filename, section FROM boletines "
            f"WHERE date >= ? AND date < ? AND ("
            f"status IN ({placeholders}) OR "
            "(status='failed' AND error_message LIKE 'timeout %')"
            ") AND COALESCE(error_message,'') NOT LIKE 'justified:%' "
        )
        params = [start, end_excl, *PENDING]
    if section:
        sql += "AND section=? "
        params.append(section)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    rank = {s.strip(): i for i, s in enumerate(order.split(","))}
    rows.sort(key=lambda r: (rank.get(str(r[2]), 99), r[1]))
    if limit:
        rows = rows[:limit]
    return rows


def _mark_failed(db_path: Path, boletin_id: int, message: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE boletines SET status='failed', error_message=? WHERE id=?",
        (message, boletin_id),
    )
    conn.commit()
    conn.close()


async def main() -> None:
    _utf8()
    args = parse_args()
    start, end_excl = date_bounds(args)
    tier = resolve_intelligence_tier()
    if tier != "local":
        raise SystemExit(
            f"Intelligence tier={tier}; hace falta LocalPro/Ollama. "
            "Set OLLAMA_BASE_URL."
        )
    rows = pending_rows(
        args.db,
        start,
        end_excl,
        args.section,
        args.limit,
        args.order,
        args.retry_timeouts,
    )
    print(
        f"pending {start}≤date<{end_excl} n={len(rows)} "
        f"tier={tier} model=qwen2.5:7b",
        flush=True,
    )
    if not rows:
        return
    config = PipelineConfig(
        indexing=IndexingConfig(
            use_chromadb=False, use_fts5=False, use_sqlite=True,
        ),
    )
    ok = fail = 0
    for i, (boletin_id, filename, section) in enumerate(rows, 1):
        print(f"[{i}/{len(rows)}] {boletin_id} {filename} S{section}", flush=True)
        try:
            await asyncio.wait_for(
                _process_document_pipeline(
                    boletin_id,
                    filename,
                    session_id=f"lote-{boletin_id}",
                    config=config,
                ),
                timeout=args.doc_timeout,
            )
            ok += 1
            print(f"  done {filename}", flush=True)
        except TimeoutError:
            fail += 1
            print(f"  TIMEOUT {filename} after {args.doc_timeout}s", flush=True)
            _mark_failed(args.db, boletin_id, f"timeout {args.doc_timeout}s")
        except Exception as exc:
            fail += 1
            print(f"  FAIL {filename}: {exc}", flush=True)
    print(f"ok={ok} fail={fail} total={len(rows)}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
