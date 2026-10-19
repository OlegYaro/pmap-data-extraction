"""index property_transactions by powiat_code

Revision ID: 9760bc2be508
Revises: bd40217d26dc
Create Date: 2026-10-12 13:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9760bc2be508'
down_revision: Union[str, Sequence[str], None] = 'bd40217d26dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Every powiat reads its rows by powiat_code; without the index each read
    # scans the whole table.
    op.create_index(op.f('ix_property_transactions_powiat_code'), 'property_transactions', ['powiat_code'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_property_transactions_powiat_code'), table_name='property_transactions')
