from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from api.schemas.transactions import (
    TransactionCreate,
    TransactionListQuery,
    TransactionResponse,
    TransactionUpdate,
)
from database.session import DbSession
from polish_national_registry.manual_edit import ManualEditTransactionService
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


@router.post("/transactions", status_code=status.HTTP_201_CREATED)
async def create_transaction(db: DbSession, data: TransactionCreate) -> TransactionResponse:
    """Add a transaction by hand."""
    return TransactionResponse.model_validate(
        await ManualEditTransactionService.create_transaction(db, data)
    )


@router.patch("/transactions/{transaction_id}", status_code=status.HTTP_200_OK)
async def update_transaction(
    db: DbSession, transaction_id: int, data: TransactionUpdate
) -> TransactionResponse:
    """Correct a transaction by hand and return the corrected record."""
    transaction = await ManualEditTransactionService.update_transaction(db, transaction_id, data)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return TransactionResponse.model_validate(transaction)
