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


class ExtractionTaskStateService:
    """Service for managing task statuses."""

    @staticmethod
    async def initialize(session: AsyncSession, trigger: TaskTriggerEnum) -> DataExtractionTaskDTO:
        """Create a new task with the given trigger and return its DTO."""

        task = await DataExtractionTaskRepository.create(session, trigger)
        await session.flush()
        await session.refresh(task)
        return DataExtractionTaskDTO.model_validate(task)

    @staticmethod
    async def get(session: AsyncSession, task_id: int) -> DataExtractionTaskDTO:
        task = await DataExtractionTaskRepository.get_by_id(session, task_id)
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
    async def fail(session: AsyncSession, task_id: int) -> DataExtractionTaskDTO:
        """Close a task as failed at the stage where it failed."""

        try:
            failed_stage = (await DataExtractionTaskRepository.get_by_id(session, task_id)).status
            task = await DataExtractionTaskRepository.update_failure(
                session, task_id=task_id, failed_stage=failed_stage
            )
            dto = DataExtractionTaskDTO.model_validate(task)
            await session.commit()
        except NoResultFound as exc:
            await session.rollback()
            raise TaskNotFoundError(task_id) from exc
        return dto
