import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.task_status import TaskStatusEnum, TaskTriggerEnum
from database.repositories.task_status import DataExtractionTaskRepository


class DataExtractionTaskDTO(BaseModel):
    """DTO for DataExtractionTask model."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: int
    run_id: uuid.UUID | None = None
    territory_code: str | None = None
    status: TaskStatusEnum
    trigger: TaskTriggerEnum
    started_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None
    failed_stage: str | None = None
    error_trace: str | None = None


class RunSummaryDTO(BaseModel):
    """Counters of one run and the failed powiats with their traces."""

    run_id: uuid.UUID
    total: int
    downloaded: int
    joined: int
    not_published: int
    failed: int
    in_progress: int
    failed_tasks: list[DataExtractionTaskDTO]


class TaskStatusServiceError(Exception):
    """Base service error"""


class TaskNotFoundError(TaskStatusServiceError):
    """Not found task_id error"""

    def __init__(self, task_id: int) -> None:
        self.task_id = task_id
        super().__init__(f"task_status id={task_id} not found")


class ExtractionTaskStateService:
    """Service for managing task statuses."""

    @staticmethod
    async def initialize(
        session: AsyncSession, trigger: TaskTriggerEnum, run_id: uuid.UUID, territory_code: str
    ) -> DataExtractionTaskDTO:
        """Create a new task for one powiat of a run and return its DTO."""

        task = await DataExtractionTaskRepository.create(
            session=session, trigger=trigger, run_id=run_id, territory_code=territory_code
        )
        await session.flush()
        await session.refresh(task)
        return DataExtractionTaskDTO.model_validate(task)

    @staticmethod
    async def get(session: AsyncSession, task_id: int) -> DataExtractionTaskDTO:
        task = await DataExtractionTaskRepository.get_by_id(session=session, task_id=task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        return DataExtractionTaskDTO.model_validate(task)

    @staticmethod
    async def change_task_status(
        session: AsyncSession, task_id: int, status: TaskStatusEnum
    ) -> DataExtractionTaskDTO:
        """Change the status of a task to the given status."""
        try:
            task = await DataExtractionTaskRepository.update_status(
                session, task_id=task_id, status=status
            )
            dto = DataExtractionTaskDTO.model_validate(task)
            await session.commit()
        except NoResultFound as exc:
            await session.rollback()
            raise TaskNotFoundError(task_id) from exc
        return dto

    @staticmethod
    async def fail(
        session: AsyncSession, task_id: int, error_trace: str | None = None
    ) -> DataExtractionTaskDTO:
        """Close a task as failed at the stage where it failed."""

        try:
            failed_stage = (await DataExtractionTaskRepository.get_by_id(session, task_id)).status
            task = await DataExtractionTaskRepository.update_failure(
                session, task_id=task_id, failed_stage=failed_stage, error_trace=error_trace
            )
            dto = DataExtractionTaskDTO.model_validate(task)
            await session.commit()
        except NoResultFound as exc:
            await session.rollback()
            raise TaskNotFoundError(task_id) from exc
        return dto

    @staticmethod
    async def get_run(session: AsyncSession, run_id: uuid.UUID) -> RunSummaryDTO:
        """How many powiats of the run are downloaded, not published, failed, still running."""

        tasks = [
            DataExtractionTaskDTO.model_validate(task)
            for task in await DataExtractionTaskRepository.list_by_run(session, run_id)
        ]
        statuses = [task.status for task in tasks]
        downloaded = statuses.count(TaskStatusEnum.joining)
        joined = statuses.count(TaskStatusEnum.staged)
        not_published = statuses.count(TaskStatusEnum.not_published)
        failed_tasks = [task for task in tasks if task.status == TaskStatusEnum.failed]

        return RunSummaryDTO(
            run_id=run_id,
            total=len(tasks),
            downloaded=downloaded,
            joined=joined,
            not_published=not_published,
            failed=len(failed_tasks),
            in_progress=len(tasks) - downloaded - joined - not_published - len(failed_tasks),
            failed_tasks=failed_tasks,
        )
