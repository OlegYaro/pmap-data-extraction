from typing import Annotated

from fastapi import APIRouter, Query, status

from api.schemas.transactions import TransactionQuery, TransactionResponse
from database.session import DbSession
from polish_national_registry.transaction_query import TransactionQueryService

router = APIRouter(tags=["transactions"])


@router.get("/transactions", status_code=status.HTTP_200_OK)
async def get_transactions(
    db: DbSession, query: Annotated[TransactionQuery, Query()]
) -> list[TransactionResponse]:
    """Clean transactions for other services filtered by the query."""
    transactions = await TransactionQueryService.get_transactions(db, query)
    return [TransactionResponse.model_validate(transaction) for transaction in transactions]
