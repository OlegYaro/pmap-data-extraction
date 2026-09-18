import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base_class import Base


class TaskStatusEnum(enum.StrEnum):
    """Enum class for status."""

    queued = "queued"
    download = "download"
    staged = "staged"
    failed = "failed"


class TaskTriggerEnum(enum.StrEnum):
    """Enum class for triggers."""

    manual = "manual"
    schedule = "schedule"


class DataExtractionTask(Base):
    """SQLAlchemy model for the task_status table."""

    __tablename__ = "task_status"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(Enum(TaskStatusEnum), default=TaskStatusEnum.queued)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trigger: Mapped[str] = mapped_column(Enum(TaskTriggerEnum))
    failed_stage: Mapped[str | None] = mapped_column(String(255), nullable=True)
