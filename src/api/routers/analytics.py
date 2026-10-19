from typing import Annotated

from fastapi import APIRouter, Query, status

from api.schemas.analytics import StatsQuery, StatsRowResponse, TerritoryResponse
from database.session import DbSession
from polish_national_registry.transaction_query import TransactionQueryService

router = APIRouter(tags=["analytics"])


@router.get("/analytics/stats", status_code=status.HTTP_200_OK)
async def get_stats(db: DbSession, query: Annotated[StatsQuery, Query()]) -> list[StatsRowResponse]:
    """Count and price per m2 quartiles of clean transactions, one row per group."""
    rows = await TransactionQueryService.get_price_stats(db, query)
    return [StatsRowResponse.model_validate(row) for row in rows]


@router.get("/territories", status_code=status.HTTP_200_OK)
async def list_territories(db: DbSession) -> list[TerritoryResponse]:
    """Voivodeships, powiats and gminas with their codes and names."""
    rows = await TransactionQueryService.list_territories(db)
    return [TerritoryResponse.model_validate(row) for row in rows]
