import uuid

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.transactions import TransactionCreate, TransactionUpdate
from database.repositories.property_transaction import StagedTransactionRepository
from polish_national_registry.transaction_query import StagedTransactionDTO

MANUAL = {"source": "manual"}


class ManualEditTransactionService:
    """Transactions entered or corrected by hand; Backend keeps who did it and why."""

    @staticmethod
    async def create_transaction(
        session: AsyncSession, data: TransactionCreate
    ) -> StagedTransactionDTO:
        """Add a transaction by hand under its own manual key."""
        row = await StagedTransactionRepository.create(
            session,
            **data.model_dump(),
            external_transaction_identifier=f"manual-{uuid.uuid4()}",
            attributes=MANUAL,
        )
        dto = StagedTransactionDTO.model_validate(row)
        await session.commit()
        return dto

    @staticmethod
    async def update_transaction(
        session: AsyncSession, transaction_id: int, data: TransactionUpdate
    ) -> StagedTransactionDTO | None:
        """Change the given fields and return the corrected record."""
        row = await StagedTransactionRepository.get_by_id(session, transaction_id)
        if row is None:
            return None

        changes = data.model_dump(exclude_unset=True, exclude={"accept_registry"})
        for field, value in changes.items():
            setattr(row, field, value)

        attributes = dict(row.attributes)
        if data.accept_registry:
            attributes.pop("source", None)
        else:
            attributes["source"] = "manual"
        row.attributes = attributes

        row.updated_at = func.now()
        await session.flush()
        await session.refresh(row)  # read updated_at back from the database
        dto = StagedTransactionDTO.model_validate(row)
        await session.commit()
        return dto
