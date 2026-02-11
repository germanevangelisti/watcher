"""
Migration script to add required_documents table
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.db.models import Base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./sqlite.db")

async def run_migration():
    """Create all tables including new required_documents"""
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        # The import of Base already has all models registered via their class definitions
        from app.db import models  # This will register all models
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Migration completed: All tables created/updated including required_documents")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_migration())
