#!/usr/bin/env python3
"""V.1.3 — run the real pipeline on March 2026 pending boletines.

Uses LocalPro/Ollama.  Does not touch Carnival `failed` rows.  ChromaDB
indexing is off so a missing Google embedding key cannot abort analysis.

Usage (from watcher-backend/):

    uv run python scripts/process_marzo_pending.py --section 4
    uv run python scripts/process_marzo_pending.py
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
BACKEND = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv

    load_dotenv(REPO / ".env")
    load_dotenv(BACKEND / ".env")
except ImportError:
    pass

# Force a finishable LocalPro profile.  14B dumped 110k of invalid JSON and
# left the GPU on 7B; V.1.3 needs the month closed, not a hung fragment.
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
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
        help="Seconds per PDF before skip (keeps the batch moving)",
    )
    return parser.parse_args()


def pending_rows(
    db_path: Path, section: str | None, limit: int, order: str,
) -> list[tuple]:
    sql = (
        "SELECT id, filename, section FROM boletines "
        "WHERE status IN ('pending', 'analyzing', 'extracting', "
        "'indexing', 'chunking', 'cleaning') "
        "AND date LIKE '202603%' "
    )
    params: list = []
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
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    args = parse_args()
    tier = resolve_intelligence_tier()
    if tier != "local":
        raise SystemExit(
            f"Intelligence tier={tier}; V.1.3 necesita LocalPro/Ollama, "
            "no FreeProvider. Set OLLAMA_BASE_URL."
        )
    rows = pending_rows(args.db, args.section, args.limit, args.order)
    print(f"pending marzo: {len(rows)} tier={tier} model=qwen2.5:7b", flush=True)
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
                    session_id=f"v13-{boletin_id}",
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
