"""add task status values

Revision ID: 53ee61e57123
Revises: 77a2184495e2
Create Date: 2026-09-17 19:25:44.172603

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '53ee61e57123'
down_revision: Union[str, Sequence[str], None] = '77a2184495e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ENUM_NAME = "taskstatusenum"
NEW_VALUES = ("queued","downloading", "staged", "failed")


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for value in NEW_VALUES:
            op.execute(f"ALTER TYPE {ENUM_NAME} ADD VALUE IF NOT EXISTS '{value}'")



def downgrade() -> None:
    """Downgrade schema."""
    pass
