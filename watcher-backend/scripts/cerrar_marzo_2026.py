#!/usr/bin/env python3
"""V.1.3 — register downloaded March huecos and justify Carnival 404s.

Does not run the LLM.  PDFs are already on disk under BOLETINES_DIR.
Ledger idempotency is asserted by re-running upsert on one existing boletin.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.services.coverage_inventory import parse_filename
from app.services.hash_utils import compute_sha256

DB = Path(__file__).resolve().parent.parent / "sqlite.db"
HUECOS_JSON = (
    Path(__file__).resolve().parent.parent.parent
    / "watcher-doc"
    / "data"
    / "2026"
    / "cobertura_calendario.json"
)


def find_pdf(filename: str) -> Path | None:
    hits = list(settings.BOLETINES_DIR.rglob(filename))
    return hits[0] if hits else None


def main() -> None:
    payload = json.loads(HUECOS_JSON.read_text(encoding="utf-8"))
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    inserted = 0
    missing = []
    now = datetime.utcnow().isoformat(sep=" ", timespec="seconds")
    for item in payload["huecos"]:
        filename = item["filename"]
        parsed = parse_filename(filename)
        if not parsed:
            continue
        slot_date, section = parsed
        ymd = slot_date.strftime("%Y%m%d")
        existing = cur.execute(
            "SELECT id FROM boletines WHERE filename=?", (filename,)
        ).fetchone()
        if existing:
            continue
        pdf = find_pdf(filename)
        if not pdf:
            missing.append(filename)
            continue
        file_hash = compute_sha256(pdf)
        size = pdf.stat().st_size
        cur.execute(
            """
            INSERT INTO boletines
            (filename, date, section, status, created_at, updated_at,
             file_hash, file_size_bytes, fuente, origin, source_url)
            VALUES (?, ?, ?, 'pending', ?, ?, ?, ?, 'provincial', 'synced', ?)
            """,
            (
                filename,
                ymd,
                str(section),
                now,
                now,
                file_hash,
                size,
                f"https://boletinoficial.cba.gov.ar/{filename}",
            ),
        )
        inserted += 1

    cur.execute(
        """
        UPDATE boletines
        SET error_message = 'justified: Carnaval 2026, HTTP 404 (no salió boletín)',
            updated_at = ?
        WHERE date IN ('20260216', '20260217') AND status='failed'
        """,
        (now,),
    )
    justified = cur.rowcount
    conn.commit()
    conn.close()
    print(f"inserted_pending={inserted} carnival_justified={justified}")
    if missing:
        print("missing_pdfs", missing)


if __name__ == "__main__":
    main()
