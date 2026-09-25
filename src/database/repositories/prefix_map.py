from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.prefix_map import PrefixMap


class PrefixMapRepository:
    """Queries on the prefix_map table; every method runs in the session it is given."""

    @staticmethod
    async def load_powiat_index(session: AsyncSession, powiat_teryt: str) -> dict[str, PrefixMap]:
        """Load one powiat's registry into a dict of prefix code -> PrefixMap.

        Called once per powiat file; transactions are then resolved in memory.
        """
        result = await session.scalars(
            select(PrefixMap).where(PrefixMap.powiat_teryt == powiat_teryt)
        )
        return {row.prefix_code: row for row in result}

    @staticmethod
    async def rewrite_boundaris(session: AsyncSession, rows: list[dict[str, str | None]]) -> None:
        """Replace every prefix_map row with the given rows; the caller commits."""
        await session.execute(delete(PrefixMap))
        if rows:
            await session.execute(insert(PrefixMap), rows)

    @staticmethod
    async def list_powiats(session: AsyncSession) -> list[str]:
        """Get a list of all powiat_teryt values in the prefix_map table, ordered and distinct."""
        result = await session.scalars(
            select(PrefixMap.powiat_teryt)
            .where(PrefixMap.powiat_teryt.is_not(None))
            .distinct()
            .order_by(PrefixMap.powiat_teryt)
        )
        return list(result)
