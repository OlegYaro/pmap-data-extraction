from database.models.task_status import TaskTriggerEnum
from database.session import SessionFactory
from polish_national_registry.status_service import TaskStatusService

STAGE_DOWNLOAD = "download"


async def start_pipeline(
    teryt: str | None,
    trigger: TaskTriggerEnum,
    task_id: int | None = None,
):
    """Start the pipeline of hole service with a new task and manage its status."""

    async with SessionFactory.begin() as session:
        if task_id is None:
            task_id = (await TaskStatusService.create_new_task(session, trigger)).id

    try:
        # result = await download() example of a download function that may raise an exception
        async with SessionFactory.begin() as session:
            await TaskStatusService.mark_download(session, task_id)
        stage = STAGE_DOWNLOAD

    except Exception:
        async with SessionFactory.begin() as session:
            await TaskStatusService.mark_failed(session, task_id, stage)
        raise

    async with SessionFactory.begin() as session:
        await TaskStatusService.mark_staged(session, task_id)

    return None  # result
