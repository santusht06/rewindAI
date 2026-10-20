"""add duration_seconds to movies

Revision ID: de72b6e86a31
Revises: 0cb724f2f5e5
Create Date: 2026-10-17 12:44:20.083671

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'de72b6e86a31'
down_revision: str | Sequence[str] | None = '0cb724f2f5e5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('movies', sa.Column('duration_seconds', sa.Integer(), nullable=False, server_default='7200'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('movies', 'duration_seconds')
