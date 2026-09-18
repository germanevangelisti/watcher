"""Add gasto público classification columns to analisis (P.7.1)

Adds per-acto is_gasto_publico, etapa_gasto and jurisdiccion_gasto so the
spending ledger can exclude remates, corporate filings and budget line
transfers from the accumulated totals.

Revision ID: add_acto_gasto_classification
Revises:
Create Date: 2026-09-13 02:10:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'add_acto_gasto_classification'
down_revision = None  # standalone, aligned with existing migrations
branch_labels = None
depends_on = None


_COLUMNS = {
    'is_gasto_publico': sa.Column('is_gasto_publico', sa.Boolean(), nullable=True),
    'etapa_gasto': sa.Column('etapa_gasto', sa.String(length=20), nullable=True),
    'jurisdiccion_gasto': sa.Column('jurisdiccion_gasto', sa.String(length=20), nullable=True),
}


def _existing_columns() -> set:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col['name'] for col in inspector.get_columns('analisis')}


def upgrade():
    """Add P.7 gasto classification columns if missing (idempotent)."""
    existing = _existing_columns()
    for name, column in _COLUMNS.items():
        if name not in existing:
            op.add_column('analisis', column)


def downgrade():
    """Drop P.7 gasto classification columns if present."""
    existing = _existing_columns()
    for name in ('jurisdiccion_gasto', 'etapa_gasto', 'is_gasto_publico'):
        if name in existing:
            op.drop_column('analisis', name)
