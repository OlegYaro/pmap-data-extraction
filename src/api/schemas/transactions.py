import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TransactionQuery(BaseModel):
    """Filters of GET /transactions a filter that is not passed is not applied."""

    model_config = ConfigDict(extra="forbid")

    run_id: uuid.UUID | None = None
    powiat_code: str | None = Field(default=None)
    gmina_code: str | None = Field(default=None)
    city_name: str | None = None
    district_name: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    price_min: float | None = Field(default=None, ge=0)
    price_max: float | None = Field(default=None, ge=0)
    area_min: float | None = Field(default=None, ge=0)
    area_max: float | None = Field(default=None, ge=0)
    rooms: list[int] | None = None
    floor_min: int | None = None
    floor_max: int | None = None
    market_type: str | None = None
    function: str | None = None


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: int
    run_id: uuid.UUID | None = None
    external_transaction_identifier: str
    external_building_id: str | None = None
    date_source_version: str | None = None
    transaction_date: date | None = None
    price_premises: float | None = None
    area_usable: float | None = None
    rooms: int | None = None
    floor: int | None = None
    market_type: str | None = None
    function: str | None = None
    address: str | None = None
    powiat_code: str
    gmina_code: str | None = None
    city_name: str | None = None
    district_name: str | None = None
    attributes: dict[str, Any]
    updated_at: datetime
