import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Date,
    DateTime,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base_class import Base


class PropertyTransaction(Base):
    """A cleaned transaction waiting for delivery to the Backend"""

    __tablename__ = "property_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)

    external_transaction_identifier: Mapped[str] = mapped_column(String(64))
    external_building_id: Mapped[str | None] = mapped_column(String(128))
    date_source_version: Mapped[str | None] = mapped_column(String(32))

    transaction_date: Mapped[date | None] = mapped_column(Date)
    price_premises: Mapped[float | None] = mapped_column(Numeric(14, 2))
    area_usable: Mapped[float | None] = mapped_column(Numeric(10, 2))
    rooms: Mapped[int | None]
    floor: Mapped[int | None]
    market_type: Mapped[str | None] = mapped_column(String(32))
    function: Mapped[str | None] = mapped_column(String(64))
    address: Mapped[str | None] = mapped_column(Text)

    powiat_code: Mapped[str] = mapped_column(String(4))
    gmina_code: Mapped[str | None] = mapped_column(String(7))
    city_name: Mapped[str | None] = mapped_column(Text)
    district_name: Mapped[str | None] = mapped_column(Text)

    exclusion_reason: Mapped[str | None] = mapped_column(String(32))
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB)

    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "external_transaction_identifier",
            "external_building_id",
            name="uq_staged_transactions_key",
            postgresql_nulls_not_distinct=True,
        ),
    )


# Indexes for the searches of GET /transactions and GET /analytics/*. Kept in step with the
# migration 20261107_3f1c9a7be2d4. Orders are written as the queries ask for them: `DESC NULLS
# LAST` is not the default of a btree, so each direction needs its own index.
_DATE_DESC = (
    PropertyTransaction.transaction_date.desc().nulls_last(),
    PropertyTransaction.id.desc(),
)
_DATE_ASC = (PropertyTransaction.transaction_date.asc().nulls_last(), PropertyTransaction.id.asc())

# Default sort of the list (newest first) and the opposite direction, with or without filters
# that match many rows (price, area, rooms, function, dates...): the scan stops after one page.
Index("ix_pt_date_desc", *_DATE_DESC)
Index("ix_pt_date_asc", *_DATE_ASC)
Index(
    "ix_pt_price_desc",
    PropertyTransaction.price_premises.desc().nulls_last(),
    PropertyTransaction.id.desc(),
)
Index(
    "ix_pt_price_asc",
    PropertyTransaction.price_premises.asc().nulls_last(),
    PropertyTransaction.id.asc(),
)
# Territory filters (exact match) that keep the date order of the list. powiat_code leads, so the
# prefix range of a voivodeship and the equality of a powiat both use it.
Index("ix_pt_powiat_date", PropertyTransaction.powiat_code, *_DATE_DESC)
# Export and `sort=id`: by id inside a powiat, also when the powiat has no rows at all.
Index("ix_pt_powiat_id", PropertyTransaction.powiat_code, PropertyTransaction.id)
Index("ix_pt_gmina_date", PropertyTransaction.gmina_code, *_DATE_DESC)
Index("ix_pt_city_date", PropertyTransaction.city_name, *_DATE_DESC)
Index("ix_pt_district_date", PropertyTransaction.district_name, *_DATE_DESC)
# ILIKE '%text%' on the address.
Index(
    "ix_pt_address_trgm",
    PropertyTransaction.address,
    postgresql_using="gin",
    postgresql_ops={"address": "gin_trgm_ops"},
)
# Analytics read clean rows only and need just the price and the area: index-only scans.
_CLEAN = text("exclusion_reason IS NULL")
Index(
    "ix_pt_clean_powiat_date",
    PropertyTransaction.powiat_code,
    PropertyTransaction.transaction_date,
    postgresql_include=["price_premises", "area_usable"],
    postgresql_where=_CLEAN,
)
Index(
    "ix_pt_clean_date",
    PropertyTransaction.transaction_date,
    postgresql_include=[
        "price_premises",
        "area_usable",
        "powiat_code",
        "gmina_code",
        "city_name",
        "district_name",
        "rooms",
        "floor",
        "function",
        "market_type",
    ],
    postgresql_where=_CLEAN,
)
