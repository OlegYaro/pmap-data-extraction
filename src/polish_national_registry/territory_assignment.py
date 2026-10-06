import logging
import traceback
from typing import Any, Self

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.prefix_map import PrefixMap
from database.repositories.prefix_map import PrefixMapRepository
from polish_national_registry.status_service import ExtractionTaskStateService, TaskStatusEnum

log = logging.getLogger(__name__)


class TransactionVersionDTO(BaseModel):
    """Key and version of one transaction in the registry."""

    model_config = ConfigDict(frozen=True)

    external_transaction_identifier: str | None
    external_building_id: str | None
    date_source_version: str | None


class SourceTransactionDTO(BaseModel):
    """One row of the premises layer its key and version, and all its columns."""

    model_config = ConfigDict(frozen=True)

    version: TransactionVersionDTO
    row: dict[str, Any]

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> Self:
        return cls(
            version=TransactionVersionDTO(
                external_transaction_identifier=row.get("tran_lokalny_id_iip"),
                external_building_id=row.get("lok_id_lokalu"),
                date_source_version=row.get("tran_wersja_id"),
            ),
            row=row,
        )


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
    async def assign_one(
        session: AsyncSession, territory_code: str, transactions: list[SourceTransactionDTO]
    ) -> list[AssignedTransactionDTO]:
        """Attach the territory to every transaction of one powiat."""
        territories = await PrefixMapRepository.load_powiat_index(session, territory_code)

        result = []
        for transaction in transactions:
            territory = find_area(transaction.version.external_building_id, territories)
            if territory is None:
                result.append(AssignedTransactionDTO(transaction=transaction.row))
                continue
            result.append(
                AssignedTransactionDTO(
                    transaction=transaction.row,
                    prefix_code=territory.prefix_code,
                    province_code=territory.voivodeship_teryt,
                    province_name=territory.voivodeship_name,
                    powiat_code=territory.powiat_teryt,
                    powiat_name=territory.powiat_name,
                    gmina_code=territory.gmina_teryt,
                    gmina_name=territory.gmina_name,
                    city_name=city_of(territory),
                    district_name=territory.district_name,
                )
            )

        log.info("assignment_ok territory_code=%s total=%d", territory_code, len(result))
        return result

    @staticmethod
    async def assign_territory(
        session: AsyncSession,
        task_id: int,
        territory_code: str,
        transactions: list[SourceTransactionDTO],
    ) -> list[AssignedTransactionDTO]:
        """Join one powiat and keep its task status up to joining."""
        await ExtractionTaskStateService.change_task_status(
            session, task_id, TaskStatusEnum.assigning
        )
        try:
            result = await TerritoryAssignmentService.assign_one(
                session, territory_code, transactions
            )
        except Exception:
            await session.rollback()
            await ExtractionTaskStateService.fail(
                session, task_id, error_trace=traceback.format_exc()
            )
            raise
        return result
