import logging
import uuid
from datetime import datetime

import taskiq_fastapi
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from core import setup_logging
from database.models.task_status import TaskStatusEnum, TaskTriggerEnum
from database.session import DbSession
from jobs.broker import broker
from jobs.tasks import orchestrate_run
from polish_national_registry.status_service import ExtractionTaskStateService

setup_logging()
log = logging.getLogger(__name__)


class FailedTaskResponse(BaseModel):
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


class RunStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: uuid.UUID
    total: int
    downloaded: int
    not_published: int
    failed: int
    in_progress: int
    failed_tasks: list[FailedTaskResponse]


app = FastAPI(title="RCN Extraction")
taskiq_fastapi.init(broker, "api.main:app")


@app.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/tasks", status_code=status.HTTP_202_ACCEPTED)
async def start_pipeline(territory_code: str | None = Query(default=None)) -> dict[str, uuid.UUID]:
    """Manual start of the pipeline for a given powiat (or all powiats if not specified)."""
    run_id = uuid.uuid4()
    await orchestrate_run.kiq(
        run_id=str(run_id), territory_code=territory_code, trigger=TaskTriggerEnum.manual
    )
    log.info("run_requested run_id=%s territory_code=%s", run_id, territory_code)
    return {"run_id": run_id}


@app.get("/runs/{run_id}", status_code=status.HTTP_200_OK)
async def get_run(db: DbSession, run_id: uuid.UUID) -> RunStatusResponse:
    """Downloaded ,not published,failed,in progress of a run, failed with traces."""
    run = await ExtractionTaskStateService.get_run(db, run_id)
    if run.total == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return RunStatusResponse.model_validate(run)
