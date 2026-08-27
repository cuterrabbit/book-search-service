import asyncio
import logging
from datetime import datetime, timezone

from elasticsearch.helpers import async_bulk
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.es_client import get_es_client
from app.models.outbox import BookOutbox, EventType, OutboxStatus

logger = logging.getLogger("relay.poller")

INDEX_NAME = "books"
BATCH_SIZE = 500
MAX_RETRIES = 5


def _to_bulk_action(event: BookOutbox) -> dict:
    if event.event_type == EventType.DELETED:
        return {"_op_type": "delete", "_index": INDEX_NAME, "_id": str(event.book_id)}
    return {
        "_op_type": "index",
        "_index": INDEX_NAME,
        "_id": str(event.book_id),
        "_source": event.payload,
    }


def _failed_book_ids(errors: list[dict]) -> set[str]:
    failed: set[str] = set()
    for err in errors:
        op_type, detail = next(iter(err.items()))
        if op_type == "delete" and detail.get("status") == 404:
            continue  # already gone: treat as a successful delete
        failed.add(str(detail.get("_id")))
    return failed


async def poll_once() -> int:
    client = get_es_client()

    async with SessionLocal() as session:
        result = await session.execute(
            select(BookOutbox)
            .where(BookOutbox.status == OutboxStatus.PENDING)
            .order_by(BookOutbox.created_at)
            .limit(BATCH_SIZE)
        )
        events = result.scalars().all()
        if not events:
            return 0

        actions = [_to_bulk_action(event) for event in events]
        _, errors = await async_bulk(client, actions, raise_on_error=False, stats_only=False)
        failed_ids = _failed_book_ids(errors)

        for event in events:
            if str(event.book_id) in failed_ids:
                event.retry_count += 1
                if event.retry_count >= MAX_RETRIES:
                    event.status = OutboxStatus.FAILED
                logger.warning(
                    "outbox event id=%s book_id=%s failed to relay (retry_count=%d)",
                    event.id,
                    event.book_id,
                    event.retry_count,
                )
            else:
                event.status = OutboxStatus.SENT
                event.processed_at = datetime.now(timezone.utc)

        await session.commit()
        return len(events)


async def run_forever(stop_event: asyncio.Event | None = None) -> None:
    settings = get_settings()
    logger.info("outbox relay started (poll_interval=%.1fs)", settings.poll_interval_seconds)
    while stop_event is None or not stop_event.is_set():
        processed = await poll_once()
        if processed:
            logger.info("relayed %d outbox event(s)", processed)
        else:
            await asyncio.sleep(settings.poll_interval_seconds)
