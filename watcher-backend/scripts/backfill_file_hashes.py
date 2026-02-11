#!/usr/bin/env python3
"""
Backfill SHA256 hashes for existing boletines in the database.
Epic 1.1 - SHA256 deduplication

This script:
1. Finds all boletines in DB without file_hash
2. Locates their PDF files on disk
3. Computes SHA256 hash
4. Updates DB with hash and file size
"""

import asyncio
import sys
from pathlib import Path
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "watcher-monolith" / "backend"))

from app.db.database import AsyncSessionLocal
from app.db.models import Boletin
from app.services.hash_utils import compute_sha256
from app.core.config import settings


async def backfill_hashes():
    """Backfill file hashes for existing boletines."""
    
    # Base directory for boletines
    boletines_base = Path("/Users/germanevangelisti/watcher-agent/boletines")
    
    async with AsyncSessionLocal() as db:
        # Find all boletines without file_hash
        query = select(Boletin).where(Boletin.file_hash.is_(None))
        result = await db.execute(query)
        boletines = result.scalars().all()
        
        print(f"\n{'='*80}")
        print(f"BACKFILL FILE HASHES")
        print(f"{'='*80}")
        print(f"Found {len(boletines)} boletines without file_hash\n")
        
        if not boletines:
            print("✅ All boletines already have file_hash!")
            return
        
        updated = 0
        missing = 0
        failed = 0
        
        for idx, boletin in enumerate(boletines, 1):
            print(f"[{idx}/{len(boletines)}] Processing: {boletin.filename}", end=" ... ")
            
            try:
                # Construct file path
                # Expected format: YYYYMMDD_N_Secc.pdf
                year_str = boletin.date[:4] if boletin.date and len(boletin.date) >= 4 else None
                month_str = boletin.date[4:6] if boletin.date and len(boletin.date) >= 6 else None
                
                if not year_str or not month_str:
                    print(f"❌ Invalid date format: {boletin.date}")
                    failed += 1
                    continue
                
                # Try multiple possible locations
                possible_paths = [
                    boletines_base / year_str / month_str / boletin.filename,
                    settings.DATA_DIR / "boletines" / year_str / month_str / boletin.filename,
                    settings.UPLOADS_DIR / year_str / month_str / boletin.filename,
                ]
                
                filepath = None
                for path in possible_paths:
                    if path.exists():
                        filepath = path
                        break
                
                if not filepath:
                    print(f"⚠️  File not found in any location")
                    missing += 1
                    continue
                
                # Compute hash
                file_hash = compute_sha256(filepath)
                file_size = filepath.stat().st_size
                
                # Update DB
                boletin.file_hash = file_hash
                boletin.file_size_bytes = file_size
                
                print(f"✅ Hash: {file_hash[:16]}... ({file_size} bytes)")
                updated += 1
                
            except Exception as e:
                print(f"❌ Error: {e}")
                failed += 1
        
        # Commit all changes
        if updated > 0:
            print(f"\n💾 Committing {updated} updates to database...")
            await db.commit()
            print("✅ Commit successful!")
        
        # Summary
        print(f"\n{'='*80}")
        print(f"SUMMARY")
        print(f"{'='*80}")
        print(f"✅ Updated: {updated}")
        print(f"⚠️  Missing files: {missing}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Total: {len(boletines)}")
        print(f"{'='*80}\n")


async def check_duplicates():
    """Check for duplicate files based on SHA256 hash."""
    async with AsyncSessionLocal() as db:
        # Find duplicate hashes
        query = select(
            Boletin.file_hash,
            func.count(Boletin.id).label('count')
        ).where(
            Boletin.file_hash.isnot(None)
        ).group_by(
            Boletin.file_hash
        ).having(
            func.count(Boletin.id) > 1
        )
        
        result = await db.execute(query)
        duplicates = result.all()
        
        if duplicates:
            print(f"\n⚠️  Found {len(duplicates)} duplicate file hashes:")
            for file_hash, count in duplicates:
                print(f"  - {file_hash}: {count} copies")
                
                # Show details
                detail_query = select(Boletin).where(Boletin.file_hash == file_hash)
                detail_result = await db.execute(detail_query)
                dups = detail_result.scalars().all()
                for dup in dups:
                    print(f"    → ID {dup.id}: {dup.filename} ({dup.status})")
        else:
            print("\n✅ No duplicate files found!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Backfill SHA256 hashes for boletines")
    parser.add_argument(
        "--check-duplicates",
        action="store_true",
        help="Check for duplicate files after backfill"
    )
    
    args = parser.parse_args()
    
    # Run backfill
    asyncio.run(backfill_hashes())
    
    # Check for duplicates if requested
    if args.check_duplicates:
        asyncio.run(check_duplicates())
