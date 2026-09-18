#!/usr/bin/env python3
"""Live ledger idempotency check for V.1.3 (one existing boletin_id)."""

from __future__ import annotations

import asyncio
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.models import EjecucionPresupuestaria
from app.services.ejecucion_ledger import upsert_boletin_ejecucion
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

DB = Path(__file__).resolve().parent.parent / "sqlite.db"


async def main() -> None:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    row = conn.execute(
        "SELECT boletin_id, COUNT(*) FROM ejecucion_presupuestaria "
        "GROUP BY boletin_id ORDER BY COUNT(*) DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if not row:
        print("no ledger rows")
        return
    boletin_id, before = row
    engine = create_async_engine(f"sqlite+aiosqlite:///{DB}")
    maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as db:
        first = await upsert_boletin_ejecucion(db, boletin_id)
        await db.commit()
        second = await upsert_boletin_ejecucion(db, boletin_id)
        await db.commit()
        count = (
            await db.execute(
                select(func.count()).select_from(EjecucionPresupuestaria).where(
                    EjecucionPresupuestaria.boletin_id == boletin_id
                )
            )
        ).scalar_one()
    await engine.dispose()
    print(
        f"boletin_id={boletin_id} before={before} "
        f"after_first={first.rows_written} after_second={second.rows_written} "
        f"db_count={count} stable={count == first.rows_written == second.rows_written}"
    )


if __name__ == "__main__":
    asyncio.run(main())
