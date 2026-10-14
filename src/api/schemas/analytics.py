from typing import Literal

from pydantic import BaseModel, ConfigDict

from api.schemas.transactions import TransactionQuery


class StatsQuery(TransactionQuery):
    """Filters of GET /transactions plus grouping; only clean transactions are counted."""

    group_by: Literal[
        "none",
        "month",
        "rooms",
        "floor",
        "powiat_code",
        "gmina_code",
        "city_name",
        "district_name",
    ] = "none"


class StatsRowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    group: str | None
    count: int
    p25: float | None
    median: float | None
    p75: float | None


class TerritoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    voivodeship_teryt: str
    voivodeship_name: str
    powiat_teryt: str | None
    powiat_name: str | None
    gmina_teryt: str | None
    gmina_name: str | None
