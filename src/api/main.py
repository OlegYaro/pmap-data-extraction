import logging
from datetime import datetime

import taskiq_fastapi
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from core import setup_logging
from database.models.task_status import TaskStatusEnum, TaskTriggerEnum
from database.session import DbSession
from jobs.broker import broker
from jobs.tasks import start_pipeline_manual
from polish_national_registry.status_service import ExtractionTaskStateService, TaskNotFoundError

setup_logging()
log = logging.getLogger(__name__)


class TaskStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: TaskStatusEnum
    trigger: TaskTriggerEnum
    started_at: datetime
    finished_at: datetime | None = None
    failed_stage: str | None = None


app = FastAPI(title="RCN Extraction")
taskiq_fastapi.init(broker, "api.main:app")


@app.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/tasks", status_code=status.HTTP_202_ACCEPTED)
async def start_pipeline(
    db: DbSession,
    territory_code: str | None = Query(default=None),
) -> TaskStatusResponse:
    """Manual start of the pipeline for a given powiat (or all powiats if not specified)."""
    task = await ExtractionTaskStateService.initialize(db, TaskTriggerEnum.manual)
    await start_pipeline_manual.kiq(territory_code=territory_code, task_id=task.id)
    log.info("run_requested task_id=%d territory_code=%s", task.id, territory_code)
    return TaskStatusResponse.model_validate(task)


@app.get("/tasks/{task_id}", status_code=status.HTTP_200_OK)
async def get_task_status(db: DbSession, task_id: int) -> TaskStatusResponse:
    """Status of a run by its id."""
    try:
        task = await ExtractionTaskStateService.get(db, task_id)
    except TaskNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found") from e

    return TaskStatusResponse.model_validate(task)
