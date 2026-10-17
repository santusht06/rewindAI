"""add duration_seconds to movies

Revision ID: de72b6e86a31
Revises: 0cb724f2f5e5
Create Date: 2026-10-17 12:44:20.083671

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de72b6e86a31'
down_revision: Union[str, Sequence[str], None] = '0cb724f2f5e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('movies', sa.Column('duration_seconds', sa.Integer(), nullable=False, server_default='7200'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('movies', 'duration_seconds')
