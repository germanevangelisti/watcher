"""Add feature engineering columns to analisis (Epic 3)

Adds per-acto transparency_score, red_flags_json and num_red_flags.

Revision ID: add_acto_feature_engineering
Revises:
Create Date: 2026-06-26 04:30:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'add_acto_feature_engineering'
down_revision = None  # standalone, aligned with existing migrations
branch_labels = None
depends_on = None


_COLUMNS = {
    'transparency_score': sa.Column('transparency_score', sa.Float(), nullable=True),
    'red_flags_json': sa.Column('red_flags_json', sa.JSON(), nullable=True),
    'num_red_flags': sa.Column('num_red_flags', sa.Integer(), nullable=True),
}


def _existing_columns() -> set:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col['name'] for col in inspector.get_columns('analisis')}


def upgrade():
    """Add Epic 3 feature engineering columns if missing (idempotent)."""
    existing = _existing_columns()
    for name, column in _COLUMNS.items():
        if name not in existing:
            op.add_column('analisis', column)


def downgrade():
    """Drop Epic 3 feature engineering columns if present."""
    existing = _existing_columns()
    for name in ('num_red_flags', 'red_flags_json', 'transparency_score'):
        if name in existing:
            op.drop_column('analisis', name)
