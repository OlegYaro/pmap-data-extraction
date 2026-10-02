import uuid

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.transactions import TransactionQuery
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

    @staticmethod
    async def list_by_query(
        session: AsyncSession, query: TransactionQuery
    ) -> list[StagedTransaction]:
        """Clean transactions matching the query; a filter that is not passed is skipped."""

        stmt = select(StagedTransaction).where(StagedTransaction.exclusion_reason.is_(None))

        if query.run_id is not None:
            stmt = stmt.where(StagedTransaction.run_id == query.run_id)
        if query.powiat_code is not None:
            stmt = stmt.where(StagedTransaction.powiat_code == query.powiat_code)
        if query.gmina_code is not None:
            stmt = stmt.where(StagedTransaction.gmina_code == query.gmina_code)
        if query.city_name is not None:
            stmt = stmt.where(StagedTransaction.city_name == query.city_name)
        if query.district_name is not None:
            stmt = stmt.where(StagedTransaction.district_name == query.district_name)
        if query.market_type is not None:
            stmt = stmt.where(StagedTransaction.market_type == query.market_type)
        if query.function is not None:
            stmt = stmt.where(StagedTransaction.function == query.function)

        if query.date_from is not None:
            stmt = stmt.where(StagedTransaction.transaction_date >= query.date_from)
        if query.date_to is not None:
            stmt = stmt.where(StagedTransaction.transaction_date <= query.date_to)
        if query.price_min is not None:
            stmt = stmt.where(StagedTransaction.price_premises >= query.price_min)
        if query.price_max is not None:
            stmt = stmt.where(StagedTransaction.price_premises <= query.price_max)
        if query.area_min is not None:
            stmt = stmt.where(StagedTransaction.area_usable >= query.area_min)
        if query.area_max is not None:
            stmt = stmt.where(StagedTransaction.area_usable <= query.area_max)
        if query.floor_min is not None:
            stmt = stmt.where(StagedTransaction.floor >= query.floor_min)
        if query.floor_max is not None:
            stmt = stmt.where(StagedTransaction.floor <= query.floor_max)
        if query.rooms:
            stmt = stmt.where(StagedTransaction.rooms.in_(query.rooms))

        result = await session.scalars(stmt.order_by(StagedTransaction.id))
        return list(result)
