import logging
import traceback
from collections import Counter
from datetime import date, datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from polish_national_registry.status_service import ExtractionTaskStateService, TaskStatusEnum
from polish_national_registry.territory_assignment import AssignedTransactionDTO

log = logging.getLogger(__name__)

ATTRIBUTES = (
    "tran_rodzaj_trans",
    "tran_sprzedajacy",
    "tran_kupujacy",
    "tran_cena_brutto",
    "tran_vat",
    "nier_rodzaj",
    "nier_prawo",
    "nier_udzial",
    "nier_pow_gruntu",
    "nier_cena_brutto",
    "nier_vat",
    "lok_nr_lokalu",
    "lok_pow_przyn",
    "lok_vat",
)
# ask
CLEAN_PRICE_PER_SQM_MIN = None
CLEAN_PRICE_PER_SQM_MAX = None


class TransactionRecordDTO(BaseModel):
    """One premises of a transaction, as it goes to staged_transactions."""

    model_config = ConfigDict(frozen=True)

    source_local_id: str | None
    premises_id: str | None
    source_version: str | None
    transaction_date: date | None
    price_premises: float | None
    area_usable: float | None
    rooms: int | None
    floor: int | None
    market_type: str | None
    function: str | None
    address: str | None
    powiat_code: str
    gmina_code: str | None
    city_name: str | None
    district_name: str | None
    exclusion_reason: str | None
    attributes: dict[str, Any]


def to_date(value: str | None) -> date | None:
    """The source keeps Polish midnight in UTC, but we want the date in local time."""
    if not value:
        return None
    return (datetime.fromisoformat(value) + timedelta(hours=2)).date()


def exclusion_reason(assigned: AssignedTransactionDTO, premises_in_deal: int) -> str | None:
    """Why the transaction is wrong, the first rule that fires, None means it is fine."""
    source = assigned.transaction
    price = source.get("lok_cena_brutto") or 0
    area = source.get("lok_pow_uzyt") or 0
    deal_price = source.get("tran_cena_brutto") or 0

    numerator, _, denominator = (source.get("nier_udzial") or "1/1").partition("/")
    if numerator.strip() != denominator.strip():
        return "fractional_share"

    if premises_in_deal > 1 or (price and deal_price and deal_price != price):
        return "package_deal"

    if source.get("tran_rodzaj_trans") != "wolnyRynek":
        return "non_market"

    if price <= 0 or area <= 0:
        return "missing_fields"

    if not source.get("dok_data") or not source.get("lok_id_lokalu"):
        return "missing_fields"

    if assigned.city_name is None and assigned.district_name is None:
        return "no_city_district"

    low = CLEAN_PRICE_PER_SQM_MIN
    high = CLEAN_PRICE_PER_SQM_MAX
    if (low is not None and price / area < low) or (high is not None and price / area > high):
        return "implausible_price"

    return None


class TransactionCleaningService:
    @staticmethod
    def to_record(assigned: AssignedTransactionDTO, premises_in_deal: int) -> TransactionRecordDTO:
        """Take the needed fields of one row and mark it"""
        source = assigned.transaction
        return TransactionRecordDTO(
            source_local_id=source.get("tran_lokalny_id_iip"),
            premises_id=source.get("lok_id_lokalu"),
            source_version=source.get("tran_wersja_id"),
            transaction_date=to_date(source.get("dok_data")),
            price_premises=source.get("lok_cena_brutto"),
            area_usable=source.get("lok_pow_uzyt"),
            rooms=source.get("lok_liczba_izb"),
            floor=source.get("lok_nr_kond"),
            market_type=source.get("tran_rodzaj_rynku"),
            function=source.get("lok_funkcja"),
            address=source.get("lok_adres"),
            powiat_code=source["teryt"],
            gmina_code=assigned.gmina_code,
            city_name=assigned.city_name,
            district_name=assigned.district_name,
            exclusion_reason=exclusion_reason(assigned, premises_in_deal),
            attributes={key: source.get(key) for key in ATTRIBUTES},
        )

    @staticmethod
    def clean_all(assigned: list[AssignedTransactionDTO]) -> list[TransactionRecordDTO]:
        """Clean one powiat file the package rule counts premises of one deed over the file."""
        premises_per_deal = Counter(
            item.transaction.get("tran_lokalny_id_iip") for item in assigned
        )
        return [
            TransactionCleaningService.to_record(
                item, premises_per_deal[item.transaction.get("tran_lokalny_id_iip")]
            )
            for item in assigned
        ]

    @staticmethod
    async def start_cleaning(
        session: AsyncSession,
        task_id: int,
        territory_code: str,
        assigned: list[AssignedTransactionDTO],
    ) -> list[TransactionRecordDTO]:
        """Clean one powiat and keep its task status up to cleaning."""
        await ExtractionTaskStateService.change_task_status(
            session, task_id, TaskStatusEnum.cleaning
        )
        try:
            records = TransactionCleaningService.clean_all(assigned)
            await ExtractionTaskStateService.change_task_status(
                session, task_id, TaskStatusEnum.staged
            )
        except Exception:
            await session.rollback()
            await ExtractionTaskStateService.fail(
                session, task_id, error_trace=traceback.format_exc()
            )
            raise

        log.info(
            "cleaning_ok territory_code=%s total=%d excluded=%d",
            territory_code,
            len(records),
            sum(record.exclusion_reason is not None for record in records),
        )
        return records
