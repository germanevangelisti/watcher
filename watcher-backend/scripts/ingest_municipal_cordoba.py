#!/usr/bin/env python3
"""Ingest the Cordoba city municipal bulletin (pm-municipal-cobertura).

One-off CLI job: lists the editions published in the range through the
bulletin's public API, downloads each act's PDF (cached under
``boletines/municipal/cordoba/<year>/actos``), reads the monto, classifies the
act and upserts ``boletines`` + ``analisis``.  Polite: one request at a time
with ``--delay`` seconds between them.

Usage (from watcher-backend/):
    python scripts/ingest_municipal_cordoba.py --year 2026
    python scripts/ingest_municipal_cordoba.py --desde 2026-10-01 --hasta 2026-11-03 --limit 2
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import AsyncSessionLocal  # noqa: E402
from app.scrapers.pds_muni import CordobaMunicipalClient  # noqa: E402
from app.services.municipal_ingest import ingest_cordoba  # noqa: E402


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--year", type=int, default=date.today().year)
    parser.add_argument("--desde", type=date.fromisoformat)
    parser.add_argument("--hasta", type=date.fromisoformat)
    parser.add_argument("--limit", type=int, help="max editions (smoke run)")
    parser.add_argument("--delay", type=float, default=1.5, help="seconds between requests")
    args = parser.parse_args()

    desde = args.desde or date(args.year, 1, 1)
    hasta = args.hasta or min(date(args.year, 12, 31), date.today())
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    client = CordobaMunicipalClient(delay=args.delay)
    async with AsyncSessionLocal() as db:
        stats = await ingest_cordoba(db, client, desde, hasta, limit_ediciones=args.limit)
    out = stats.as_dict()
    out["errores"] = out["errores"][:20]
    out["requests"] = client.requests
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
