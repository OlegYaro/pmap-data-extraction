from sqlalchemy.ext.asyncio import AsyncSession

from database.models.task_status import TaskStatusEnum, TaskTriggerEnum
from polish_national_registry.status_service import ExtractionTaskStateService


async def start_pipeline(
    session: AsyncSession,
    teryt: str | None,
    trigger: TaskTriggerEnum,
    task_id: int | None = None,
):
    """Start the pipeline of hole service with a new task and manage its status."""

    if task_id is None:
        task_id = (await ExtractionTaskStateService.initialize(session, trigger)).id

    try:
        stage = TaskStatusEnum.download
        # result = await download() example of a download function that may raise an exception
        await ExtractionTaskStateService.enter_stage(session, task_id, TaskStatusEnum.download)

        await ExtractionTaskStateService.enter_stage(
            session, task_id=task_id, status=TaskStatusEnum.staged
        )
    except Exception:
        await ExtractionTaskStateService.fail(session, task_id, stage)

    return None  # result
