import uuid

from sqlalchemy import Select, String, and_, cast, func, literal, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.transactions import TransactionListQuery, TransactionQuery
from database.models.property_transaction import PropertyTransaction
from polish_national_registry.territory_assignment import TransactionVersionDTO
from polish_national_registry.transaction_cleaning import TransactionRecordDTO


class StagedTransactionRepository:
    @staticmethod
    async def get_versions(session: AsyncSession, powiat_code: str) -> set[TransactionVersionDTO]:
        """Key and version of every transaction of a powiat already in the database."""
        result = await session.execute(
            select(
                PropertyTransaction.external_transaction_identifier,
                PropertyTransaction.external_building_id,
                PropertyTransaction.date_source_version,
            ).where(PropertyTransaction.powiat_code == powiat_code)
        )
        return {TransactionVersionDTO(**row) for row in result.mappings()}

    @staticmethod
    async def upsert(
        session: AsyncSession, records: list[TransactionRecordDTO], run_id: uuid.UUID | None
    ) -> None:
        """Insert new record or update a known one only when its source_version changed"""
        if not records:
            return

        stmt = insert(PropertyTransaction).values(run_id=run_id)
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
            where=PropertyTransaction.date_source_version.is_distinct_from(
                new_row.date_source_version
            ),
        )
        await session.execute(stmt, [record.model_dump() for record in records])

    @staticmethod
    def apply_filters(stmt: Select, query: TransactionQuery) -> Select:
        """Add every passed filter; the same filters for lists and analytics."""
        if query.run_id is not None:
            stmt = stmt.where(PropertyTransaction.run_id == query.run_id)
        if query.powiat_code is not None:
            stmt = stmt.where(PropertyTransaction.powiat_code == query.powiat_code)
        if query.gmina_code is not None:
            stmt = stmt.where(PropertyTransaction.gmina_code == query.gmina_code)
        if query.city_name is not None:
            stmt = stmt.where(PropertyTransaction.city_name == query.city_name)
        if query.district_name is not None:
            stmt = stmt.where(PropertyTransaction.district_name == query.district_name)
        if query.market_type is not None:
            stmt = stmt.where(PropertyTransaction.market_type == query.market_type)
        if query.function is not None:
            stmt = stmt.where(PropertyTransaction.function == query.function)

        if query.date_from is not None:
            stmt = stmt.where(PropertyTransaction.transaction_date >= query.date_from)
        if query.date_to is not None:
            stmt = stmt.where(PropertyTransaction.transaction_date <= query.date_to)
        if query.price_min is not None:
            stmt = stmt.where(PropertyTransaction.price_premises >= query.price_min)
        if query.price_max is not None:
            stmt = stmt.where(PropertyTransaction.price_premises <= query.price_max)
        if query.area_min is not None:
            stmt = stmt.where(PropertyTransaction.area_usable >= query.area_min)
        if query.area_max is not None:
            stmt = stmt.where(PropertyTransaction.area_usable <= query.area_max)
        if query.floor_min is not None:
            stmt = stmt.where(PropertyTransaction.floor >= query.floor_min)
        if query.floor_max is not None:
            stmt = stmt.where(PropertyTransaction.floor <= query.floor_max)
        if query.rooms:
            stmt = stmt.where(PropertyTransaction.rooms.in_(query.rooms))
        if query.voivodeship_code is not None:
            stmt = stmt.where(PropertyTransaction.powiat_code.startswith(query.voivodeship_code))
        if query.address is not None:
            stmt = stmt.where(PropertyTransaction.address.icontains(query.address, autoescape=True))
        if query.exclusion_reason:
            reasons = [reason for reason in query.exclusion_reason if reason != "clean"]
            allowed = [PropertyTransaction.exclusion_reason.in_(reasons)]
            if "clean" in query.exclusion_reason:
                allowed.append(PropertyTransaction.exclusion_reason.is_(None))
            stmt = stmt.where(or_(*allowed))
        return stmt

    @staticmethod
    async def list_by_query(
        session: AsyncSession, query: TransactionListQuery
    ) -> list[PropertyTransaction]:
        """One page of transactions matching the query, ordered by the sort field and id."""
        column = getattr(PropertyTransaction, query.sort)
        desc = query.order == "desc"
        stmt = StagedTransactionRepository.apply_filters(select(PropertyTransaction), query)
        if query.after_id is not None:
            stmt = stmt.where(_after(column, query))
        stmt = stmt.order_by(
            (column.desc() if desc else column.asc()).nulls_last(),
            PropertyTransaction.id.desc() if desc else PropertyTransaction.id.asc(),
        ).limit(query.limit)
        return list(await session.scalars(stmt))

    @staticmethod
    async def get_by_id(session: AsyncSession, transaction_id: int) -> PropertyTransaction | None:
        """One transaction by its id or None."""
        return await session.get(PropertyTransaction, transaction_id)

    @staticmethod
    async def price_stats(session, query):
        price = PropertyTransaction.price_premises / func.nullif(PropertyTransaction.area_usable, 0)
        if query.group_by == "none":
            group = literal(None, String)
        elif query.group_by == "month":
            group = func.to_char(PropertyTransaction.transaction_date, "YYYY-MM")
        else:
            group = cast(getattr(PropertyTransaction, query.group_by), String)

        stmt = select(
            group.label("group"),
            func.count().label("count"),
            func.percentile_cont(0.25).within_group(price).label("p25"),
            func.percentile_cont(0.5).within_group(price).label("median"),
            func.percentile_cont(0.75).within_group(price).label("p75"),
        )

        clean = query.model_copy(update={"exclusion_reason": ["clean"]})
        stmt = StagedTransactionRepository.apply_filters(stmt, clean)
        if query.group_by != "none":
            stmt = stmt.group_by(group).order_by(group)

        return list((await session.execute(stmt)).mappings())


def _after(column, query: TransactionListQuery):
    """Rows after the last row of the previous page; empty sort values come last."""
    desc = query.order == "desc"
    after_id = (
        PropertyTransaction.id < query.after_id if desc else PropertyTransaction.id > query.after_id
    )
    if query.sort == "id":
        return after_id
    if query.after_value is None:
        return and_(column.is_(None), after_id)
    value = cast(literal(query.after_value, String), column.type)
    return or_(
        column < value if desc else column > value,
        and_(column == value, after_id),
        column.is_(None),
    )
