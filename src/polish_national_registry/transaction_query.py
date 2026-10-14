import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.analytics import StatsQuery
from api.schemas.transactions import TransactionListQuery
from database.repositories.prefix_map import PrefixMapRepository
from database.repositories.property_transaction import StagedTransactionRepository


class StagedTransactionDTO(BaseModel):
    """DTO for StagedTransaction model."""

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
    exclusion_reason: str | None = None
    attributes: dict[str, Any]
    updated_at: datetime


class PriceStatsRowDTO(BaseModel):
    """Count and price per m2 quartiles of one group."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    group: str | None
    count: int
    p25: float | None
    median: float | None
    p75: float | None


class TerritoryDTO(BaseModel):
    """One voivodeship, powiat or gmina of prefix_map."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    voivodeship_teryt: str
    voivodeship_name: str
    powiat_teryt: str | None
    powiat_name: str | None
    gmina_teryt: str | None
    gmina_name: str | None


class TransactionQueryService:
    @staticmethod
    async def get_transactions(
        session: AsyncSession, query: TransactionListQuery
    ) -> list[StagedTransactionDTO]:
        """One page of the transactions matching the query."""
        return [
            StagedTransactionDTO.model_validate(row)
            for row in await StagedTransactionRepository.list_by_query(session, query)
        ]

    @staticmethod
    async def get_transaction_by_id(
        session: AsyncSession, transaction_id: int
    ) -> StagedTransactionDTO | None:
        """One transaction with every field, None when there is no such id."""
        row = await StagedTransactionRepository.get_by_id(session, transaction_id)
        return None if row is None else StagedTransactionDTO.model_validate(row)

    @staticmethod
    async def get_price_stats(session: AsyncSession, query: StatsQuery) -> list[PriceStatsRowDTO]:
        """Count and price per m2 quartiles of clean transactions, one row per group."""
        return [
            PriceStatsRowDTO.model_validate(row)
            for row in await StagedTransactionRepository.price_stats(session, query)
        ]

    @staticmethod
    async def list_territories(session: AsyncSession) -> list[TerritoryDTO]:
        """Every voivodeship, powiat and gmina known to prefix_map."""
        return [
            TerritoryDTO.model_validate(row)
            for row in await PrefixMapRepository.list_territories(session)
        ]
