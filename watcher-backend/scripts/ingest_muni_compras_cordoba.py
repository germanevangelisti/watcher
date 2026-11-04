#!/usr/bin/env python3
"""Ingest the Cordoba city procurement portal (MuniCompras, WMU1).

One-off CLI job: pages through the portal's public API for the date range,
upserts ``boletines`` + ``analisis`` (one row per procedure) and dedupes against
the acts already ingested from the municipal bulletin.  Politeness: one request
at a time with ``--delay`` seconds between them, plus an on-disk cache so a
re-run does not hit the API again (``--no-cache`` to ignore it).

The amount stored is the **presupuesto oficial** of the call: the awarded
supplier and amount are not public without a token (see ``muni_compras.py``).

Usage (from watcher-backend/):
    python scripts/ingest_muni_compras_cordoba.py --year 2026
    python scripts/ingest_muni_compras_cordoba.py --desde 2026-10-01 --hasta 2026-11-04 --limit-paginas 1
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
from app.scrapers.muni_compras import MuniComprasClient  # noqa: E402
from app.services.muni_compras_ingest import ingest_compras  # noqa: E402


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--year", type=int, default=date.today().year)
    parser.add_argument("--desde", type=date.fromisoformat)
    parser.add_argument("--hasta", type=date.fromisoformat)
    parser.add_argument("--limit-paginas", type=int, help="max pages (smoke run)")
    parser.add_argument("--delay", type=float, default=1.2, help="seconds between requests")
    parser.add_argument("--no-cache", action="store_true", help="ignore the on-disk page cache")
    args = parser.parse_args()

    desde = args.desde or date(args.year, 1, 1)
    hasta = args.hasta or min(date(args.year, 12, 31), date.today())
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    client = MuniComprasClient(delay=args.delay, use_cache=not args.no_cache)
    async with AsyncSessionLocal() as db:
        stats = await ingest_compras(db, client, desde, hasta, limit_paginas=args.limit_paginas)
    out = stats.as_dict()
    out.update({"desde": desde.isoformat(), "hasta": hasta.isoformat(), "requests": client.requests,
                "cache_hits": client.cache_hits, "errores": out["errores"][:20]})
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
