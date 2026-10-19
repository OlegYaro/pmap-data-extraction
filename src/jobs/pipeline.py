import logging

from sqlalchemy.ext.asyncio import AsyncSession

from core import settings
from core.timing import timed
from database.repositories.prefix_map import PrefixMapRepository
from polish_national_registry.data_download import DataDownloadService
from polish_national_registry.status_service import ExtractionTaskStateService
from polish_national_registry.territory_assignment import TerritoryAssignmentService
from polish_national_registry.transaction_cleaning import TransactionCleaningService
from polish_national_registry.transaction_filter import TransactionFilterService
from polish_national_registry.transaction_load import TransactionLoadService

log = logging.getLogger(__name__)


async def resolve_territories(session: AsyncSession, territory_code: str | None) -> list[str]:
    """One powiat when a territory_code is given, every powiat there is when it is not."""
    if territory_code:
        return [territory_code]
    return await PrefixMapRepository.list_powiats(session=session)


async def run_territory(session: AsyncSession, task_id: int) -> None:
    """Start the pipeline for all service for one powiat with a new task."""
    task = await ExtractionTaskStateService.get(session, task_id)
    target_dir = settings.DOWNLOAD_DIR / task.started_at.strftime("%Y-%m-%d")
    target_dir.mkdir(parents=True, exist_ok=True)
    ctx = {"task_id": task_id, "territory_code": task.territory_code}

    log.info("pipeline_started task_id=%s territory_code=%s", task_id, task.territory_code)
    with timed("pipeline", **ctx):
        with timed("download", **ctx):
            path = await DataDownloadService.start_downloading(
                session, task_id, task.territory_code, target_dir
            )
        if path is None:
            return
        try:
            with timed("filter", **ctx):
                transactions = await TransactionFilterService.start_filtering(
                    session, task_id, task.territory_code, path
                )
        finally:
            path.unlink(missing_ok=True)
        with timed("assign", **ctx):
            assigned = await TerritoryAssignmentService.assign_territory(
                session, task_id, task.territory_code, transactions
            )
        with timed("clean", **ctx):
            records = await TransactionCleaningService.start_cleaning(
                session, task_id, task.territory_code, assigned
            )
        with timed("load", **ctx):
            await TransactionLoadService.start_loading(
                session, task_id, task.territory_code, task.run_id, records
            )
