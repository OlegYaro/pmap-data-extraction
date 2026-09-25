import asyncio
import logging
import sqlite3
import tempfile
import traceback
import zipfile
from contextlib import closing
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.prefix_map import PrefixMap
from database.repositories.prefix_map import PrefixMapRepository
from polish_national_registry.status_service import ExtractionTaskStateService, TaskStatusEnum

log = logging.getLogger(__name__)


class TerritoryAssignmentError(Exception):
    """The file could not be joined with the boundaries."""


class AssignedTransactionDTO(BaseModel):
    """All columns of one transaction row plus its territory."""

    model_config = ConfigDict(frozen=True)

    transaction: dict[str, Any]
    prefix_code: str | None = None
    province_code: str | None = None
    province_name: str | None = None
    powiat_code: str | None = None
    powiat_name: str | None = None
    gmina_code: str | None = None
    gmina_name: str | None = None
    city_name: str | None = None
    district_name: str | None = None


def find_area(identifier: str | None, areas: dict[str, PrefixMap]) -> PrefixMap | None:
    """Find the territory of a transaction by its cadastral identifier."""
    if not identifier:
        return None
    unit, _, rest = identifier.partition(".")
    obreb = rest.partition(".")[0]
    return areas.get(f"{unit}.{obreb}") or areas.get(unit)


def city_of(territory: PrefixMap) -> str | None:
    """The city of a territory, when its cadastral unit is urban; None for rural areas."""
    kind = territory.prefix_code[7:8]
    # 1 - urban gmina, 4 - town of an urban-rural gmina, 8/9 - district of a city with powiat rights.
    return territory.gmina_name if kind and kind in "1489" else None


class TerritoryAssignmentService:
    @staticmethod
    def read_transactions(archive: Path) -> list[dict[str, Any]]:
        """Every row of the layer that has the identifier column, as column -> value dicts."""
        with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(archive) as zf:
            name = next(n for n in zf.namelist() if n.endswith(".gpkg"))
            gpkg = Path(zf.extract(name, tmp))
            with closing(sqlite3.connect(gpkg)) as conn:
                conn.row_factory = sqlite3.Row
                tables = [r[0] for r in conn.execute("SELECT table_name FROM gpkg_contents")]
                for table in tables:
                    columns = [c[1] for c in conn.execute(f'PRAGMA table_info("{table}")')]
                    if "lok_id_lokalu" in columns:
                        rows = conn.execute(f'SELECT * FROM "{table}"')  # noqa: S608
                        return [dict(row) for row in rows]
        raise TerritoryAssignmentError(f"{archive.name}: no layer with column {'lok_id_lokalu'}")

    @staticmethod
    async def assign_one(
        session: AsyncSession, territory_code: str, archive: Path
    ) -> list[AssignedTransactionDTO]:
        """Read one powiat file and attach the territory to every transaction."""
        territories = await PrefixMapRepository.load_powiat_index(session, territory_code)
        rows = await asyncio.to_thread(TerritoryAssignmentService.read_transactions, archive)

        result = []
        for row in rows:
            territory = find_area(row.get("lok_id_lokalu"), territories)
            fields = (
                {
                    "prefix_code": territory.prefix_code,
                    "province_code": territory.voivodeship_teryt,
                    "province_name": territory.voivodeship_name,
                    "powiat_code": territory.powiat_teryt,
                    "powiat_name": territory.powiat_name,
                    "gmina_code": territory.gmina_teryt,
                    "gmina_name": territory.gmina_name,
                    "city_name": city_of(territory),
                    "district_name": territory.district_name,
                }
                if territory
                else {}
            )
            result.append(AssignedTransactionDTO(transaction=row, **fields))

        log.info("assignment_ok territory_code=%s total=%d", territory_code, len(result))
        return result

    @staticmethod
    async def start_assigning(
        session: AsyncSession, task_id: int, territory_code: str, archive: Path
    ) -> list[AssignedTransactionDTO]:
        """Join one powiat and keep its task status up to joining."""
        await ExtractionTaskStateService.change_task_status(
            session, task_id, TaskStatusEnum.assigning
        )
        try:
            result = await TerritoryAssignmentService.assign_one(session, territory_code, archive)
        except Exception:
            await session.rollback()
            await ExtractionTaskStateService.fail(
                session, task_id, error_trace=traceback.format_exc()
            )
            raise
        await ExtractionTaskStateService.change_task_status(session, task_id, TaskStatusEnum.staged)
        return result
