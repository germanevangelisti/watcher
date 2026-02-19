"""Add chunk_records table for Epic 3

Revision ID: add_chunk_records
Revises: 
Create Date: 2026-02-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_chunk_records'
down_revision = None  # Will be updated based on existing migrations
branch_labels = None
depends_on = None


def upgrade():
    """Create chunk_records table."""
    op.create_table(
        'chunk_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.String(length=255), nullable=False),
        sa.Column('boletin_id', sa.Integer(), nullable=True),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('chunk_hash', sa.String(length=64), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('num_chars', sa.Integer(), nullable=False),
        sa.Column('start_char', sa.Integer(), nullable=True),
        sa.Column('end_char', sa.Integer(), nullable=True),
        sa.Column('section_type', sa.String(length=50), nullable=True),
        sa.Column('topic', sa.String(length=100), nullable=True),
        sa.Column('language', sa.String(length=10), nullable=True),
        sa.Column('has_tables', sa.Boolean(), nullable=True),
        sa.Column('has_amounts', sa.Boolean(), nullable=True),
        sa.Column('entities_json', sa.JSON(), nullable=True),
        sa.Column('embedding_model', sa.String(length=100), nullable=True),
        sa.Column('embedding_dimensions', sa.Integer(), nullable=True),
        sa.Column('indexed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['boletin_id'], ['boletines.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices
    op.create_index('idx_chunk_document_index', 'chunk_records', ['document_id', 'chunk_index'], unique=True)
    op.create_index('idx_chunk_section', 'chunk_records', ['section_type'])
    op.create_index('idx_chunk_hash', 'chunk_records', ['chunk_hash'])
    op.create_index('idx_chunk_boletin', 'chunk_records', ['boletin_id'])
    op.create_index('idx_chunk_has_amounts', 'chunk_records', ['has_amounts'])
    op.create_index('idx_chunk_indexed', 'chunk_records', ['indexed_at'])
    op.create_index(op.f('ix_chunk_records_document_id'), 'chunk_records', ['document_id'], unique=False)
    op.create_index(op.f('ix_chunk_records_boletin_id'), 'chunk_records', ['boletin_id'], unique=False)


def downgrade():
    """Drop chunk_records table."""
    op.drop_index(op.f('ix_chunk_records_boletin_id'), table_name='chunk_records')
    op.drop_index(op.f('ix_chunk_records_document_id'), table_name='chunk_records')
    op.drop_index('idx_chunk_indexed', table_name='chunk_records')
    op.drop_index('idx_chunk_has_amounts', table_name='chunk_records')
    op.drop_index('idx_chunk_boletin', table_name='chunk_records')
    op.drop_index('idx_chunk_hash', table_name='chunk_records')
    op.drop_index('idx_chunk_section', table_name='chunk_records')
    op.drop_index('idx_chunk_document_index', table_name='chunk_records')
    op.drop_table('chunk_records')
