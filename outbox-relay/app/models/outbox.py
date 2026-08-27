import enum
from datetime import datetime

from sqlalchemy import JSON, TIMESTAMP, Enum, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EventType(str, enum.Enum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    DELETED = "DELETED"


class OutboxStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class BookOutbox(Base):
    __tablename__ = "book_outbox"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    book_id: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[EventType] = mapped_column(Enum(EventType), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[OutboxStatus] = mapped_column(
        Enum(OutboxStatus), nullable=False, default=OutboxStatus.PENDING
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), index=True)
    processed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
