import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base_class import Base


class TaskStatusEnum(enum.StrEnum):
    """Enum class for status."""

    queued = "queued"
    downloading = "downloading"
    cleaning = "cleaning"
    assigning = "assigning"
    staged = "staged"
    done = "done"
    not_published = "not_published"
    failed = "failed"


class TaskTriggerEnum(enum.StrEnum):
    """Enum class for triggers."""

    manual = "manual"
    schedule = "schedule"


class DataExtractionTask(Base):
    """SQLAlchemy model for the task_status table."""

    __tablename__ = "task_status"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    territory_code: Mapped[str | None] = mapped_column(String(4))
    status: Mapped[str] = mapped_column(Enum(TaskStatusEnum), default=TaskStatusEnum.queued)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trigger: Mapped[str] = mapped_column(Enum(TaskTriggerEnum))
    failed_stage: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_trace: Mapped[str | None] = mapped_column(Text, nullable=True)
