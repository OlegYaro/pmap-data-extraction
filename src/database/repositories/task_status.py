import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.task_status import DataExtractionTask, TaskStatusEnum, TaskTriggerEnum


class DataExtractionTaskRepository:
    @staticmethod
    async def create(
        session: AsyncSession, trigger: TaskTriggerEnum, run_id: uuid.UUID, territory_code: str
    ) -> DataExtractionTask:
        """Add a new task for one powiat of a run and return the created task."""

        task = DataExtractionTask(trigger=trigger, run_id=run_id, territory_code=territory_code)
        session.add(task)
        await session.flush()

        return task

    @staticmethod
    async def get_by_id(session: AsyncSession, task_id: int) -> DataExtractionTask:
        """Retrieve a task by its ID and return the task object or None if not found."""
        stmt = select(DataExtractionTask).where(DataExtractionTask.id == task_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_failure(
        session: AsyncSession, task_id: int, failed_stage: str, error_trace: str | None
    ) -> DataExtractionTask:
        """Update the failed_stage and error_trace of a task and return the updated task."""

        stmt = (
            update(DataExtractionTask)
            .where(DataExtractionTask.id == task_id)
            .values(
                status=TaskStatusEnum.failed,
                failed_stage=failed_stage,
                error_trace=error_trace,
                finished_at=func.now(),
            )
            .returning(DataExtractionTask)
        )

        result = await session.execute(stmt)
        return result.scalar_one()

    @staticmethod
    async def update_status(
        session: AsyncSession, task_id: int, status: TaskStatusEnum
    ) -> DataExtractionTask:
        """Update the status of a task and return the updated task."""

        stmt = (
            update(DataExtractionTask)
            .where(DataExtractionTask.id == task_id)
            .values(status=status)
            .returning(DataExtractionTask)
        )

        result = await session.execute(stmt)
        return result.scalar_one()

    @staticmethod
    async def list_by_run(session: AsyncSession, run_id: uuid.UUID) -> list[DataExtractionTask]:
        """All tasks one per powiat of a run."""

        stmt = select(DataExtractionTask).where(DataExtractionTask.run_id == run_id)
        result = await session.scalars(stmt)
        return list(result)
