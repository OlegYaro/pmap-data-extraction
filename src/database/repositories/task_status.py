import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.property_transaction import PropertyTransaction
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

        values = {"status": status}
        if status in (TaskStatusEnum.done, TaskStatusEnum.not_published):
            values["finished_at"] = func.now()
        stmt = (
            update(DataExtractionTask)
            .where(DataExtractionTask.id == task_id)
            .values(**values)
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

    @staticmethod
    async def run_summary(session: AsyncSession, run_id: uuid.UUID) -> list:
        """Rows written by a run, by exclusion reason and inserted or updated."""
        inserted = (PropertyTransaction.created_at == PropertyTransaction.updated_at).label(
            "inserted"
        )
        stmt = (
            select(PropertyTransaction.exclusion_reason, inserted, func.count().label("count"))
            .where(PropertyTransaction.run_id == run_id)
            .group_by(PropertyTransaction.exclusion_reason, inserted)
        )
        return list((await session.execute(stmt)).mappings())

    @staticmethod
    async def list_runs(session: AsyncSession, limit: int) -> list:
        """The latest runs, newest first, with task counts by status."""
        task = DataExtractionTask

        def count(status: TaskStatusEnum):
            return func.count().filter(task.status == status)

        stmt = (
            select(
                task.run_id,
                task.trigger,
                func.min(task.started_at).label("started_at"),
                func.max(task.finished_at).label("finished_at"),
                func.count().label("total"),
                count(TaskStatusEnum.done).label("done"),
                count(TaskStatusEnum.not_published).label("not_published"),
                count(TaskStatusEnum.failed).label("failed"),
            )
            .where(task.run_id.is_not(None))
            .group_by(task.run_id, task.trigger)
            .order_by(func.min(task.started_at).desc())
            .limit(limit)
        )
        return list((await session.execute(stmt)).mappings())
