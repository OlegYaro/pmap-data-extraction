from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.task_status import TaskStatusEnum, TaskTriggerEnum
from database.repositories.task_status import TaskStatusRepository


class TaskStatusDTO(BaseModel):
    """DTO for TaskStatus model."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: int
    status: TaskStatusEnum
    trigger: TaskTriggerEnum
    started_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None
    failed_stage: str | None = None


class TaskStatusServiceError(Exception):
    """Base service error"""


class TaskNotFoundError(TaskStatusServiceError):
    """Not found task_id error"""

    def __init__(self, task_id: int) -> None:
        self.task_id = task_id
        super().__init__(f"task_status id={task_id} not found")


class TaskStatusService:
    """Service for managing task statuses."""

    @staticmethod
    async def create_new_task(session: AsyncSession, trigger: TaskTriggerEnum) -> TaskStatusDTO:
        """Create a new task with the given trigger and return its DTO."""

        task = await TaskStatusRepository.add_task(session, trigger)
        await session.flush()
        await session.refresh(task)
        return TaskStatusDTO.model_validate(task)

    @staticmethod
    async def mark_download(session: AsyncSession, task_id: int) -> TaskStatusDTO:
        """Mark a task as downloading."""
        try:
            task = await TaskStatusRepository.change_status(
                session, task_id, TaskStatusEnum.download
            )
        except NoResultFound as exc:
            raise TaskNotFoundError(task_id) from exc
        return TaskStatusDTO.model_validate(task)

    @staticmethod
    async def mark_staged(session: AsyncSession, task_id: int) -> TaskStatusDTO:
        """Mark a task as staged."""
        try:
            task = await TaskStatusRepository.mark_staged(session, task_id)
        except NoResultFound as exc:
            raise TaskNotFoundError(task_id) from exc
        return TaskStatusDTO.model_validate(task)

    @staticmethod
    async def mark_failed(session: AsyncSession, task_id: int, failed_stage: str) -> TaskStatusDTO:
        """Mark a task as failed."""
        try:
            task = await TaskStatusRepository.mark_failed(session, task_id, failed_stage[:32])
        except NoResultFound as exc:
            raise TaskNotFoundError(task_id) from exc
        return TaskStatusDTO.model_validate(task)

    @staticmethod
    async def get_task(session: AsyncSession, task_id: int) -> TaskStatusDTO:
        task = await TaskStatusRepository.get_task(session, task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        return TaskStatusDTO.model_validate(task)
