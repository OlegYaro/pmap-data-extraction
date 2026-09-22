import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Annotated

from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import TaskiqDepends

from database.models.task_status import TaskTriggerEnum
from database.session import SessionFactory
from jobs import pipeline
from jobs.broker import broker
from polish_national_registry.status_service import ExtractionTaskStateService

log = logging.getLogger(__name__)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Generate a database session one per task execution."""
    async with SessionFactory() as session:
        yield session


Session = Annotated[AsyncSession, TaskiqDepends(get_session)]


@broker.task(task_name="start_pipeline")
async def orchestrate_run(
    session: Session, run_id: str, territory_code: str | None, trigger: TaskTriggerEnum
) -> None:
    """Create a task per powiat of the run and queue a pipeline for each."""
    territory_codes = await pipeline.resolve_territories(session, territory_code)
    if not territory_codes:
        raise RuntimeError("prefix_map is empty - load PRG first")

    tasks = [
        await ExtractionTaskStateService.initialize(session, trigger, uuid.UUID(run_id), code)
        for code in territory_codes
    ]
    await session.commit()

    for task in tasks:
        await process_territory.kiq(task_id=task.id)
    log.info("run_queued run_id=%s powiats=%d", run_id, len(tasks))


@broker.task(task_name="process_territory")
async def process_territory(session: Session, task_id: int) -> None:
    """Start the pipeline for a manual call one powiat of a run."""
    await pipeline.run_territory(session, task_id)


@broker.task(schedule=[{"cron": "0 3 1,15 * *"}])
async def start_pipeline_schedule() -> None:
    """Start the pipeline for all powiats schedule."""
    await orchestrate_run.kiq(
        run_id=str(uuid.uuid4()), territory_code=None, trigger=TaskTriggerEnum.schedule
    )
