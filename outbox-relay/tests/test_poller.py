from types import SimpleNamespace

from app.models.outbox import EventType
from app.relay.poller import _failed_book_ids, _to_bulk_action


def test_to_bulk_action_for_created_event() -> None:
    event = SimpleNamespace(event_type=EventType.CREATED, book_id=1, payload={"title": "t"})
    action = _to_bulk_action(event)
    assert action == {
        "_op_type": "index",
        "_index": "books",
        "_id": "1",
        "_source": {"title": "t"},
    }


def test_to_bulk_action_for_deleted_event() -> None:
    event = SimpleNamespace(event_type=EventType.DELETED, book_id=2, payload={})
    action = _to_bulk_action(event)
    assert action == {"_op_type": "delete", "_index": "books", "_id": "2"}


def test_failed_book_ids_ignores_404_on_delete() -> None:
    errors = [{"delete": {"_id": "5", "status": 404}}]
    assert _failed_book_ids(errors) == set()


def test_failed_book_ids_collects_other_failures() -> None:
    errors = [
        {"index": {"_id": "7", "status": 400, "error": {"type": "mapper_parsing_exception"}}},
        {"delete": {"_id": "8", "status": 500}},
    ]
    assert _failed_book_ids(errors) == {"7", "8"}
