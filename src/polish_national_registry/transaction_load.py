import logging
import traceback
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.property_transaction import StagedTransactionRepository
from polish_national_registry.status_service import ExtractionTaskStateService, TaskStatusEnum
from polish_national_registry.transaction_cleaning import TransactionRecordDTO

log = logging.getLogger(__name__)


class TransactionLoadService:
    @staticmethod
    async def start_loading(
        session: AsyncSession,
        task_id: int,
        territory_code: str,
        run_id: uuid.UUID | None,
        records: list[TransactionRecordDTO],
    ) -> None:
        """Save one powiat and set staged in the same commit"""
        unique_by_key = {}
        for record in records:
            key = (record.external_transaction_identifier, record.external_building_id)
            unique_by_key[key] = record
        unique: list[TransactionRecordDTO] = list(unique_by_key.values())

        try:
            await StagedTransactionRepository.upsert(session, unique, run_id)
            await ExtractionTaskStateService.change_task_status(
                session, task_id, TaskStatusEnum.done
            )
        except Exception:
            await session.rollback()
            await ExtractionTaskStateService.fail(
                session, task_id, error_trace=traceback.format_exc()
            )
            raise

        log.info(
            "loading_ok territory_code=%s received=%d saved=%d",
            territory_code,
            len(records),
            len(unique),
        )
