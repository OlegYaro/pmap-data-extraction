import pytest

from database.models.task_status import TaskStatusEnum, TaskTriggerEnum
from polish_national_registry.status_service import ExtractionTaskStateService, TaskNotFoundError

from .factories import RUN_ID, TaskFactory


async def test_initialize_creates_queued_task(session):
    task = await ExtractionTaskStateService.initialize(
        session, TaskTriggerEnum.manual, RUN_ID, "0201"
    )

    assert task.status == TaskStatusEnum.queued
    assert (task.run_id, task.territory_code) == (RUN_ID, "0201")


async def test_fail_stores_stage_and_trace(session, persist):
    task = await persist(TaskFactory(status=TaskStatusEnum.downloading))

    failed = await ExtractionTaskStateService.fail(session, task.id, error_trace="Traceback ...")

    assert failed.status == TaskStatusEnum.failed
    assert failed.failed_stage == TaskStatusEnum.downloading
    assert failed.error_trace == "Traceback ..."
    assert failed.finished_at is not None


async def test_get_raises_for_unknown_task(session):
    with pytest.raises(TaskNotFoundError):
        await ExtractionTaskStateService.get(session, 10**6)
