# tasks.py
from collections.abc import AsyncGenerator
from typing import Annotated

from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import Context, TaskiqDepends

from database.models.task_status import TaskTriggerEnum
from database.session import SessionFactory
from jobs import pipeline
from jobs.broker import broker


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Generate a database session one per task execution."""
    async with SessionFactory() as session:
        yield session


Session = Annotated[AsyncSession, TaskiqDepends(get_session)]


@broker.task(task_name="start_pipeline")
async def start_pipeline_manual(
    session: Session,
    teryt: str | None,
    task_id: int | None = None,
    context: Context = TaskiqDepends(),
):
    """Start the pipeline (hole service) for a manual call"""
    return await pipeline.start_pipeline(
        session, teryt, trigger=TaskTriggerEnum.manual, task_id=task_id
    )


@broker.task(schedule=[{"cron": "0 3 * * *"}])
async def start_pipeline_schedule(session: Session):
    """Start the pipeline for all powiats schedule."""

    return await pipeline.start_pipeline(session, teryt=None, trigger=TaskTriggerEnum.schedule)
