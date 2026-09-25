import logging
import uuid

from fastapi import APIRouter, HTTPException, Query, status

from api.schemas.runs import RunStartedResponse, RunStatusResponse
from database.models.task_status import TaskTriggerEnum
from database.session import DbSession
from jobs.tasks import orchestrate_run
from polish_national_registry.status_service import ExtractionTaskStateService

log = logging.getLogger(__name__)

router = APIRouter(tags=["runs"])


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
async def start_pipeline(territory_code: str | None = Query(default=None)) -> RunStartedResponse:
    """Manual start of the pipeline for a given powiat (or all powiats if not specified)."""
    run_id = uuid.uuid4()
    await orchestrate_run.kiq(
        run_id=str(run_id), territory_code=territory_code, trigger=TaskTriggerEnum.manual
    )
    log.info("run_requested run_id=%s territory_code=%s", run_id, territory_code)
    return RunStartedResponse(run_id=run_id)


@router.get("/runs/{run_id}", status_code=status.HTTP_200_OK)
async def get_run(db: DbSession, run_id: uuid.UUID) -> RunStatusResponse:
    """Downloaded ,not published,failed,in progress of a run, failed with traces."""
    run = await ExtractionTaskStateService.get_run(db, run_id)
    if run.total == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return RunStatusResponse.model_validate(run)
