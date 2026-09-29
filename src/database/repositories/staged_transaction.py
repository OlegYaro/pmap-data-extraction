import uuid

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.staged_transaction import StagedTransaction
from polish_national_registry.territory_assignment import TransactionVersionDTO
from polish_national_registry.transaction_cleaning import TransactionRecordDTO


class StagedTransactionRepository:
    @staticmethod
    async def get_versions(session: AsyncSession, powiat_code: str) -> set[TransactionVersionDTO]:
        """Key and version of every transaction of a powiat already in the database."""
        result = await session.execute(
            select(
                StagedTransaction.external_transaction_identifier,
                StagedTransaction.external_building_id,
                StagedTransaction.date_source_version,
            ).where(StagedTransaction.powiat_code == powiat_code)
        )
        return {TransactionVersionDTO(**row) for row in result.mappings()}

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
            where=StagedTransaction.date_source_version.is_distinct_from(
                new_row.date_source_version
            ),
        )
        await session.execute(stmt, [record.model_dump() for record in records])
