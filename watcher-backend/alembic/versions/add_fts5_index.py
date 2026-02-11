"""Add FTS5 full-text search index for chunk_records

Revision ID: add_fts5_index
Revises: add_chunk_records
Create Date: 2026-02-10 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_fts5_index'
down_revision = 'add_chunk_records'
branch_labels = None
depends_on = None


def upgrade():
    """Create FTS5 virtual table and sync triggers."""
    
    # Create FTS5 virtual table
    # Use content= to reference the chunk_records table
    # Use content_rowid= to map to the id column
    # UNINDEXED columns are stored but not indexed for full-text search
    op.execute("""
        CREATE VIRTUAL TABLE chunk_records_fts USING fts5(
            text,
            document_id UNINDEXED,
            chunk_index UNINDEXED,
            section_type UNINDEXED,
            content=chunk_records,
            content_rowid=id
        )
    """)
    
    # Create INSERT trigger to keep FTS5 in sync
    op.execute("""
        CREATE TRIGGER chunk_records_fts_insert AFTER INSERT ON chunk_records
        BEGIN
            INSERT INTO chunk_records_fts(rowid, text, document_id, chunk_index, section_type)
            VALUES (new.id, new.text, new.document_id, new.chunk_index, new.section_type);
        END
    """)
    
    # Create DELETE trigger to keep FTS5 in sync
    op.execute("""
        CREATE TRIGGER chunk_records_fts_delete AFTER DELETE ON chunk_records
        BEGIN
            INSERT INTO chunk_records_fts(chunk_records_fts, rowid, text, document_id, chunk_index, section_type)
            VALUES ('delete', old.id, old.text, old.document_id, old.chunk_index, old.section_type);
        END
    """)
    
    # Create UPDATE trigger to keep FTS5 in sync
    op.execute("""
        CREATE TRIGGER chunk_records_fts_update AFTER UPDATE ON chunk_records
        BEGIN
            INSERT INTO chunk_records_fts(chunk_records_fts, rowid, text, document_id, chunk_index, section_type)
            VALUES ('delete', old.id, old.text, old.document_id, old.chunk_index, old.section_type);
            INSERT INTO chunk_records_fts(rowid, text, document_id, chunk_index, section_type)
            VALUES (new.id, new.text, new.document_id, new.chunk_index, new.section_type);
        END
    """)


def downgrade():
    """Drop FTS5 table and triggers."""
    op.execute("DROP TRIGGER IF EXISTS chunk_records_fts_update")
    op.execute("DROP TRIGGER IF EXISTS chunk_records_fts_delete")
    op.execute("DROP TRIGGER IF EXISTS chunk_records_fts_insert")
    op.execute("DROP TABLE IF EXISTS chunk_records_fts")
