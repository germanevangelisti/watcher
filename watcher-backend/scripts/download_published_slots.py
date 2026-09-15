#!/usr/bin/env python3
"""Download canonical provincial bulletin PDFs for a list of (date, section) slots.

Used by V.1.2 (gold set) and V.1.3 (fill March huecos).  Writes under
settings.BOLETINES_DIR (gitignored) using the same scraper as sync.

Usage:
    uv run python scripts/download_published_slots.py --from-json ../watcher-doc/data/2026/cobertura_calendario.json --huecos
    uv run python scripts/download_published_slots.py --filename 20260303_4_Secc.pdf
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.scrapers.base_scraper import DocumentType
from app.scrapers.pds_prov import create_provincial_scraper
from app.services.coverage_inventory import parse_filename, parse_ymd


def slots_from_args(args) -> list[tuple[date, int]]:
    slots: list[tuple[date, int]] = []
    if args.from_json and args.huecos:
        payload = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
        for item in payload.get("huecos", []):
            slots.append((parse_ymd(item["date"]), int(item["section"])))
    if args.filename:
        for name in args.filename:
            parsed = parse_filename(name)
            if not parsed:
                raise SystemExit(f"filename inválido: {name}")
            slots.append(parsed)
    if args.date and args.section:
        slots.append((parse_ymd(args.date), int(args.section)))
    # de-dup preserving order
    seen: set[tuple[date, int]] = set()
    unique: list[tuple[date, int]] = []
    for slot in slots:
        if slot not in seen:
            seen.add(slot)
            unique.append(slot)
    return unique


async def download_slots(slots: list[tuple[date, int]], output_dir: Path) -> list[dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    scraper = create_provincial_scraper(
        output_dir=output_dir,
        rate_limit_delay=0.4,
        timeout=60.0,
    )
    results = []
    for i, (slot_date, section) in enumerate(slots, 1):
        result = await scraper.download_single(
            target_date=slot_date,
            document_type=DocumentType.BOLETIN,
            section=section,
        )
        print(
            f"[{i}/{len(slots)}] {result.filename} {result.status} "
            f"{result.size or 0} {result.error or ''}",
            flush=True,
        )
        results.append(
            {
                "filename": result.filename,
                "status": result.status,
                "size": result.size,
                "path": result.path,
                "error": result.error,
            }
        )
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-json", type=Path, default=None)
    parser.add_argument("--huecos", action="store_true")
    parser.add_argument("--filename", nargs="*", default=None)
    parser.add_argument("--date", default=None)
    parser.add_argument("--section", type=int, default=None)
    parser.add_argument("--out", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    slots = slots_from_args(args)
    if not slots:
        raise SystemExit("Nada que descargar")
    out = args.out or settings.BOLETINES_DIR
    print(f"Descargando {len(slots)} slots -> {out}", flush=True)
    results = asyncio.run(download_slots(slots, out))
    ok = sum(1 for r in results if r["status"] in {"downloaded", "exists"})
    print(f"OK {ok}/{len(results)}")


if __name__ == "__main__":
    main()
