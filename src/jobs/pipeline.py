# import logging

# from sqlalchemy.ext.asyncio import AsyncSession

# from database.models.task_status import TaskTriggerEnum
# from polish_national_registry.data_download import DataDownloadService
# from polish_national_registry.status_service import ExtractionTaskStateService

# log = logging.getLogger(__name__)


# async def start_pipeline(
#     session: AsyncSession,
#     territory_code: str | None,
#     trigger: TaskTriggerEnum,
#     task_id: int | None = None,
#     is_admin: bool = False,
# ):
#     """Start the pipeline of hole service with a new task."""

#     if task_id is None:
#         task_id = (await ExtractionTaskStateService.initialize(session, trigger)).id

#     try:
#         log.info("pipeline_download_started task_id=%s territory_code=%s", task_id, territory_code)
#         results = await DataDownloadService.start_downloading(
#             session=session, task_id=task_id, territory_code=territory_code, is_admin=is_admin
#         )

#         return results

#     except Exception:
#         log.exception("pipeline_failed task_id=%s", task_id)
#         await session.rollback()
#         await ExtractionTaskStateService.fail(session, task_id)
#         raise
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from core import settings
from database.repositories.prefix_map import PrefixMapRepository
from polish_national_registry.data_download import DataDownloadService
from polish_national_registry.status_service import ExtractionTaskStateService

log = logging.getLogger(__name__)


async def resolve_territories(session: AsyncSession, territory_code: str | None) -> list[str]:
    """One powiat when a territory_code is given, every powiat there is when it is not."""
    if territory_code:
        return [territory_code]
    return await PrefixMapRepository.list_powiats(session=session)


async def run_territory(session: AsyncSession, task_id: int) -> Path | None:
    """Start the pipeline for all service for one powiat with a new task."""
    task = await ExtractionTaskStateService.get(session, task_id)
    target_dir = settings.DOWNLOAD_DIR / task.started_at.strftime("%Y-%m-%d")
    target_dir.mkdir(parents=True, exist_ok=True)

    log.info("pipeline_started task_id=%s territory_code=%s", task_id, task.territory_code)
    path = await DataDownloadService.start_downloading(
        session, task_id, task.territory_code, target_dir
    )
    # next stages: cleaning, joining - the same way, each service owns its statuses
    return path
