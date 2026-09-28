import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.staged_transaction import StagedTransaction
from polish_national_registry.transaction_cleaning import TransactionRecordDTO


class StagedTransactionRepository:
    @staticmethod
    async def upsert(
        session: AsyncSession, records: list[TransactionRecordDTO], run_id: uuid.UUID | None
    ) -> None:
        """Insert new record or update a known one only when its source_version changed"""
        if not records:
            return

        stmt = insert(StagedTransaction).values(run_id=run_id)
        new_row = stmt.excluded

        updated_fields = {field: new_row[field] for field in TransactionRecordDTO.model_fields}
        stmt = stmt.on_conflict_do_update(
            constraint="uq_staged_transactions_key",
            set_={
                **updated_fields,
                "run_id": run_id,
                "updated_at": func.now(),
                "delivered_at": None,
            },
            where=StagedTransaction.source_version.is_distinct_from(new_row.source_version),
        )
        await session.execute(stmt, [record.model_dump() for record in records])
