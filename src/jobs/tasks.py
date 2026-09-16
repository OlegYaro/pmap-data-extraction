# tasks.py
from taskiq import Context, TaskiqDepends

from database.models.task_status import TaskTriggerEnum
from jobs import pipeline
from jobs.broker import broker


@broker.task(task_name="start_pipeline")
async def start_pipeline_manual(
    teryt: str | None, task_id: int | None = None, context: Context = TaskiqDepends()
):
    """Start the pipeline (hole service) for a manual call"""
    return await pipeline.start_pipeline(teryt, TaskTriggerEnum.manual, task_id=task_id)


@broker.task(schedule=[{"cron": "0 3 * * *"}])
async def start_pipeline_schedule():
    """Start the pipeline for all powiats schedule."""

    return await pipeline.start_pipeline(None, TaskTriggerEnum.schedule)
