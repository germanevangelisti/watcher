#!/usr/bin/env python3
"""
Backfill FTS5 index with existing chunk_records data.

This script populates the chunk_records_fts table with all existing chunks.
Run this after creating the FTS5 migration if you have existing data.

Usage:
    python scripts/backfill_fts5.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent / "watcher-monolith" / "backend"
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def backfill_fts5_index(db_path: str = None):
    """
    Backfill FTS5 index with all existing chunk_records.
    
    Args:
        db_path: Path to SQLite database (default: sqlite.db in backend)
    """
    if db_path is None:
        db_path = project_root / "sqlite.db"
    
    # Create engine
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check if FTS5 table exists
        check_sql = text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='chunk_records_fts'
        """)
        result = session.execute(check_sql)
        if not result.fetchone():
            logger.error("FTS5 table 'chunk_records_fts' does not exist. Run migration first.")
            return False
        
        # Count existing chunks
        count_sql = text("SELECT COUNT(*) FROM chunk_records")
        result = session.execute(count_sql)
        total_chunks = result.scalar()
        
        logger.info(f"Found {total_chunks} chunks in chunk_records table")
        
        if total_chunks == 0:
            logger.info("No chunks to backfill")
            return True
        
        # Check current FTS5 count
        fts_count_sql = text("SELECT COUNT(*) FROM chunk_records_fts")
        result = session.execute(fts_count_sql)
        fts_chunks = result.scalar()
        
        logger.info(f"FTS5 index currently has {fts_chunks} chunks")
        
        if fts_chunks == total_chunks:
            logger.info("FTS5 index is already up to date")
            return True
        
        # Clear FTS5 index first
        logger.info("Clearing FTS5 index...")
        clear_sql = text("DELETE FROM chunk_records_fts")
        session.execute(clear_sql)
        session.commit()
        
        # Insert all chunks into FTS5
        logger.info("Inserting chunks into FTS5 index...")
        insert_sql = text("""
            INSERT INTO chunk_records_fts(rowid, text, document_id, chunk_index, section_type)
            SELECT id, text, document_id, chunk_index, section_type
            FROM chunk_records
        """)
        session.execute(insert_sql)
        session.commit()
        
        # Verify count
        result = session.execute(fts_count_sql)
        final_count = result.scalar()
        
        logger.info(f"✓ Backfill complete! FTS5 index now has {final_count} chunks")
        
        if final_count != total_chunks:
            logger.warning(f"Count mismatch: expected {total_chunks}, got {final_count}")
            return False
        
        # Optimize index
        logger.info("Optimizing FTS5 index...")
        optimize_sql = text("INSERT INTO chunk_records_fts(chunk_records_fts) VALUES('optimize')")
        session.execute(optimize_sql)
        session.commit()
        
        logger.info("✓ FTS5 index optimized")
        
        return True
    
    except Exception as e:
        logger.error(f"Error during backfill: {e}", exc_info=True)
        session.rollback()
        return False
    
    finally:
        session.close()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Backfill FTS5 index with existing chunks")
    parser.add_argument(
        "--db",
        type=str,
        help="Path to SQLite database (default: watcher-monolith/backend/sqlite.db)"
    )
    
    args = parser.parse_args()
    
    logger.info("Starting FTS5 backfill...")
    success = backfill_fts5_index(args.db)
    
    if success:
        logger.info("✓ Backfill completed successfully")
        sys.exit(0)
    else:
        logger.error("✗ Backfill failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
