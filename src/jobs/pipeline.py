import logging

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.task_status import TaskTriggerEnum
from polish_national_registry.data_download import DataDownloadService
from polish_national_registry.status_service import ExtractionTaskStateService

log = logging.getLogger(__name__)


async def start_pipeline(
    session: AsyncSession,
    territory_code: str | None,
    trigger: TaskTriggerEnum,
    task_id: int | None = None,
    is_admin: bool = False,
):
    """Start the pipeline of hole service with a new task."""

    if task_id is None:
        task_id = (await ExtractionTaskStateService.initialize(session, trigger)).id

    try:
        log.info("pipeline_download_started task_id=%s territory_code=%s", task_id, territory_code)
        results = await DataDownloadService.start_downloading(
            session=session, task_id=task_id, territory_code=territory_code, is_admin=is_admin
        )

        return results

    except Exception:
        log.exception("pipeline_failed task_id=%s", task_id)
        await session.rollback()
        await ExtractionTaskStateService.fail(session, task_id)
        raise
