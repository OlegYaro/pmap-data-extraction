"""indexes for the transaction list and the analytics

Revision ID: 3f1c9a7be2d4
Revises: 9760bc2be508
Create Date: 2026-11-07 18:00:00.000000

Before this, every search except "powiat equals X" read the whole table: the default sort
(`transaction_date DESC NULLS LAST`), any other filter, `ORDER BY id DESC`, address search and
all of the analytics. Measured on 1.5 million rows: 220-850 ms became 0.1-60 ms; on the small
production instance a full read takes 20-30 s, which is what the gateway cuts off.

The indexes are built CONCURRENTLY: readers and the loading pipeline keep working, at the price
of a slower build. The old single-column powiat_code index is replaced by `ix_pt_powiat_date`
(its leading column serves every query it served). The cost is slower loads: about 4 s more per
60 thousand rows.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "3f1c9a7be2d4"
down_revision: Union[str, Sequence[str], None] = "9760bc2be508"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "property_transactions"
DATE_DESC = "transaction_date DESC NULLS LAST, id DESC"

# name -> definition after "ON property_transactions"
INDEXES = {
    "ix_pt_date_desc": f"({DATE_DESC})",
    "ix_pt_date_asc": "(transaction_date ASC NULLS LAST, id ASC)",
    "ix_pt_price_desc": "(price_premises DESC NULLS LAST, id DESC)",
    "ix_pt_price_asc": "(price_premises ASC NULLS LAST, id ASC)",
    "ix_pt_powiat_date": f"(powiat_code, {DATE_DESC})",
    # Export and `sort=id`: by id inside a powiat, also when the powiat has no rows at all.
    "ix_pt_powiat_id": "(powiat_code, id)",
    "ix_pt_gmina_date": f"(gmina_code, {DATE_DESC})",
    "ix_pt_city_date": f"(city_name, {DATE_DESC})",
    "ix_pt_district_date": f"(district_name, {DATE_DESC})",
    "ix_pt_address_trgm": "USING gin (address gin_trgm_ops)",
    "ix_pt_clean_powiat_date": (
        "(powiat_code, transaction_date) INCLUDE (price_premises, area_usable) "
        "WHERE exclusion_reason IS NULL"
    ),
    "ix_pt_clean_date": (
        "(transaction_date) INCLUDE (price_premises, area_usable, powiat_code, gmina_code, "
        "city_name, district_name, rooms, floor, function, market_type) "
        "WHERE exclusion_reason IS NULL"
    ),
}


def upgrade() -> None:
    """Upgrade schema."""
    # pg_trgm is a trusted extension: the database owner can create it (also on RDS).
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # CREATE INDEX CONCURRENTLY cannot run inside a transaction. IF NOT EXISTS lets a rerun
    # continue after a failed build; a failed concurrent build leaves an INVALID index that
    # must be dropped by hand first (see the README of the patch).
    with op.get_context().autocommit_block():
        # The default of a 1 GB instance (64 MB) makes every build sort on disk; 128 MB is still
        # safe next to the connections of the API and the worker. Session setting, no restart.
        op.execute("SET maintenance_work_mem = '128MB'")
        for name, definition in INDEXES.items():
            op.execute(f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {name} ON {TABLE} {definition}")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_property_transactions_powiat_code")

    # The statistics must follow the big loads, or the planner picks plans for rows that are
    # no longer there: analyze after 2 % of the rows changed instead of the default 10 %.
    op.execute(
        f"ALTER TABLE {TABLE} SET (autovacuum_analyze_scale_factor = 0.02, "
        "autovacuum_vacuum_scale_factor = 0.05)"
    )
    op.execute(f"ANALYZE {TABLE}")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        f"ALTER TABLE {TABLE} RESET (autovacuum_analyze_scale_factor, autovacuum_vacuum_scale_factor)"
    )
    with op.get_context().autocommit_block():
        op.execute(
            f"CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_property_transactions_powiat_code "
            f"ON {TABLE} (powiat_code)"
        )
        for name in INDEXES:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")
