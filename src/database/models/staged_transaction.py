import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, Numeric, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base_class import Base


class StagedTransaction(Base):
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
