from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.task_status import TaskStatus, TaskStatusEnum, TaskTriggerEnum


class TaskStatusRepository:
    @staticmethod
    async def add_task(session: AsyncSession, trigger: TaskTriggerEnum) -> TaskStatus:
        """Add a new task with the given trigger and return the created task."""

        task = TaskStatus(trigger=trigger)
        session.add(task)
        await session.flush

        return task

    @staticmethod
    async def change_status(
        session: AsyncSession, task_id: int, status: TaskStatusEnum
    ) -> TaskStatus:
        """Update the status of a task and return the updated task."""

        stmt = (
            update(TaskStatus)
            .where(TaskStatus.id == task_id)
            .values(status=status)
            .returning(TaskStatus)
        )

        result = await session.execute(stmt)
        return result.scalar_one()

    @staticmethod
    async def update_finished_at(session: AsyncSession, task_id: int, finished_at) -> TaskStatus:
        """Update the finished_at timestamp of a task and return the updated task."""

        stmt = (
            update(TaskStatus)
            .where(TaskStatus.id == task_id)
            .values(finished_at=finished_at)
            .returning(TaskStatus)
        )

        result = await session.execute(stmt)
        return result.scalar_one()

    @staticmethod
    async def get_task(session: AsyncSession, task_id: int) -> TaskStatus:
        """Retrieve a task by its ID and return the task object or None if not found."""
        stmt = select(TaskStatus).where(TaskStatus.id == task_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_failed_stage(
        session: AsyncSession, task_id: int, failed_stage: str
    ) -> TaskStatus:
        """Update the failed_stage of a task and return the updated task."""

        stmt = (
            update(TaskStatus)
            .where(TaskStatus.id == task_id)
            .values(failed_stage=failed_stage)
            .values(finished_at=text("NOW()"))
            .returning(TaskStatus)
        )

        result = await session.execute(stmt)
        return result.scalar_one()
