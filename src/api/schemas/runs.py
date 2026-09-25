import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from database.models.task_status import TaskStatusEnum, TaskTriggerEnum


class RunStartedResponse(BaseModel):
    run_id: uuid.UUID


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
