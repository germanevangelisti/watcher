#!/usr/bin/env python3
"""
Quick validation script for FTS5 functionality.
Run this after applying the FTS5 migration.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent / "watcher-monolith" / "backend"
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.services.fts_service import FTSService
from datetime import datetime

def validate_fts5(db_path: str = None):
    """Validate FTS5 setup and basic functionality."""
    
    if db_path is None:
        db_path = project_root / "sqlite.db"
    
    print(f"Validating FTS5 setup in: {db_path}")
    print("-" * 60)
    
    # Create engine
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 1. Check if FTS5 table exists
        print("\n1. Checking if FTS5 table exists...")
        check_sql = text("SELECT name FROM sqlite_master WHERE type='table' AND name='chunk_records_fts'")
        result = session.execute(check_sql)
        if result.fetchone():
            print("   ✓ FTS5 table 'chunk_records_fts' exists")
        else:
            print("   ✗ FTS5 table does not exist. Run migration first.")
            return False
        
        # 2. Check triggers
        print("\n2. Checking FTS5 triggers...")
        triggers_sql = text("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'chunk_records_fts%'")
        result = session.execute(triggers_sql)
        triggers = [row[0] for row in result.fetchall()]
        
        expected_triggers = ['chunk_records_fts_insert', 'chunk_records_fts_delete', 'chunk_records_fts_update']
        for trigger in expected_triggers:
            if trigger in triggers:
                print(f"   ✓ Trigger '{trigger}' exists")
            else:
                print(f"   ✗ Trigger '{trigger}' missing")
        
        # 3. Get index stats
        print("\n3. Getting FTS5 index statistics...")
        service = FTSService(session)
        stats = service.get_index_stats()
        
        print(f"   Total chunks in FTS5: {stats.get('total_chunks', 0)}")
        print(f"   Source chunks: {stats.get('source_chunks', 0)}")
        print(f"   In sync: {stats.get('in_sync', False)}")
        
        if stats.get('by_section'):
            print(f"   Sections indexed: {len(stats['by_section'])}")
            for section, count in list(stats['by_section'].items())[:5]:
                print(f"      - {section}: {count}")
        
        # 4. Test simple search
        print("\n4. Testing BM25 search...")
        if stats.get('total_chunks', 0) > 0:
            # Try a simple search
            results = service.search_bm25("decreto", top_k=3)
            print(f"   Search for 'decreto' returned {len(results)} results")
            if results:
                print(f"   Top result score: {results[0].bm25_score:.4f}")
                print(f"   Sample text: {results[0].text[:100]}...")
        else:
            print("   No chunks indexed yet, skipping search test")
        
        # 5. Test query validation
        print("\n5. Testing query validation...")
        test_result = service.test_query("decreto OR resolución")
        if test_result['valid']:
            print(f"   ✓ Query validation works")
        else:
            print(f"   ✗ Query validation failed: {test_result.get('error')}")
        
        print("\n" + "=" * 60)
        print("✓ FTS5 validation complete!")
        print("=" * 60)
        
        return True
    
    except Exception as e:
        print(f"\n✗ Error during validation: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        session.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate FTS5 setup")
    parser.add_argument("--db", type=str, help="Path to SQLite database")
    
    args = parser.parse_args()
    
    success = validate_fts5(args.db)
    sys.exit(0 if success else 1)
