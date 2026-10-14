from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from api.schemas.transactions import TransactionListQuery, TransactionResponse
from database.session import DbSession
from polish_national_registry.transaction_query import TransactionQueryService

router = APIRouter(tags=["transactions"])


@router.get("/transactions", status_code=status.HTTP_200_OK)
async def get_transactions(
    db: DbSession, query: Annotated[TransactionListQuery, Query()]
) -> list[TransactionResponse]:
    """One page of transactions for other services filtered by the query."""
    transactions = await TransactionQueryService.get_transactions(db, query)
    return [TransactionResponse.model_validate(transaction) for transaction in transactions]


@router.get("/transactions/{transaction_id}", status_code=status.HTTP_200_OK)
async def get_transaction_by_id(db: DbSession, transaction_id: int) -> TransactionResponse:
    """One transaction with every field, including the three price levels in attributes."""
    transaction = await TransactionQueryService.get_transaction_by_id(db, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return TransactionResponse.model_validate(transaction)
