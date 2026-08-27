from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import BookOutbox, EventType


def add_event(
    session: AsyncSession, book_id: int, event_type: EventType, payload: dict
) -> None:
    session.add(BookOutbox(book_id=book_id, event_type=event_type, payload=payload))
