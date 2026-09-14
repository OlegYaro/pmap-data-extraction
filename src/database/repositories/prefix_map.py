from sqlalchemy import Row, text
from sqlalchemy.ext.asyncio import AsyncSession


class PrefixMapRepository:
    """Queries on the prefix_map table; every method runs in the session it is given."""

    @staticmethod
    async def for_powiat(session: AsyncSession, powiat_teryt: str) -> dict[str, Row]:
        """Load one powiat's registry into a dict of prefix code -> prefix_map row.

        Called once per powiat file; transactions are then resolved in memory.
        """
        result = await session.execute(
            text("SELECT * FROM prefix_map WHERE powiat_teryt = :powiat"),
            {"powiat": powiat_teryt},
        )
        return {row.prefix_code: row for row in result}

    @staticmethod
    async def replace_all(session: AsyncSession, rows: list[dict[str, str | None]]) -> None:
        """Replace every prefix_map row with the given rows; the caller commits."""
        await session.execute(text("TRUNCATE prefix_map"))
        await session.execute(
            text(
                """
                INSERT INTO prefix_map (prefix_code, voivodeship_teryt, voivodeship_name,
                                        powiat_teryt, powiat_name, gmina_teryt, gmina_name,
                                        district_name)
                VALUES (:prefix_code, :voivodeship_teryt, :voivodeship_name,
                        :powiat_teryt, :powiat_name, :gmina_teryt, :gmina_name,
                        :district_name)
                """
            ),
            rows,
        )
