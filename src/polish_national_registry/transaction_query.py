import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.transactions import TransactionQuery
from database.repositories.staged_transaction import StagedTransactionRepository


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
    attributes: dict[str, Any]
    updated_at: datetime


class TransactionQueryService:
    @staticmethod
    async def get_transactions(
        session: AsyncSession, query: TransactionQuery
    ) -> list[StagedTransactionDTO]:
        """All clean transactions matching the query."""
        return [
            StagedTransactionDTO.model_validate(row)
            for row in await StagedTransactionRepository.list_by_query(session, query)
        ]
