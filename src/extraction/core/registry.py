from sqlalchemy import Row, text
from sqlalchemy.ext.asyncio import AsyncSession


async def prefix_map_for(session: AsyncSession, powiat_teryt: str) -> dict[str, Row]:
    """Load one powiat's registry into a dict of prefix code -> prefix_map row.

    Called once per powiat file; transactions are then resolved in memory.
    """

    result = await session.execute(
        text("SELECT * FROM prefix_map WHERE powiat_teryt = :powiat"),
        {"powiat": powiat_teryt},
    )
    return {row.prefix_code: row for row in result}


def resolve(identifier: str | None, lookup: dict[str, Row]) -> Row | None:
    """Find the territory of a transaction by its cadastral identifier.

    Tries "unit.obreb" first, which gives the district, then "unit", which gives the gmina.
    """

    if not identifier:
        return None
    unit, _, rest = identifier.partition(".")
    obreb = rest.partition(".")[0]
    return lookup.get(f"{unit}.{obreb}") or lookup.get(unit)
