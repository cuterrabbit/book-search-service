from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.book import Book
from app.models.outbox import EventType
from app.repositories import book_repository, category_repository, outbox_repository
from app.schemas.book import BookCreate, BookUpdate


@dataclass
class BookWithCategory:
    book: Book
    category_name: str


def _payload(book: Book, category_name: str) -> dict:
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "publisher": book.publisher,
        "category": category_name,
        "published_date": book.published_date.isoformat(),
        "isbn": book.isbn,
        "price": book.price,
        "stock": book.stock,
    }


async def _resolve_category_id(session: AsyncSession, category_name: str) -> int:
    category = await category_repository.get_by_name(session, category_name)
    if category is None:
        raise AppException(400, "INVALID_PARAMETER", f"unknown category: {category_name}")
    return category.id


async def _flush_or_conflict(session: AsyncSession, isbn: str) -> None:
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise AppException(409, "DUPLICATE_ISBN", f"isbn already exists: {isbn}") from exc


async def create_book(session: AsyncSession, data: BookCreate) -> BookWithCategory:
    category_id = await _resolve_category_id(session, data.category)

    existing = await book_repository.get_by_isbn(session, data.isbn)
    if existing is not None:
        raise AppException(409, "DUPLICATE_ISBN", f"isbn already exists: {data.isbn}")

    book = Book(
        title=data.title,
        author=data.author,
        publisher=data.publisher,
        category_id=category_id,
        published_date=data.published_date,
        isbn=data.isbn,
        price=data.price,
        stock=data.stock,
    )
    book_repository.add(session, book)
    await _flush_or_conflict(session, data.isbn)

    outbox_repository.add_event(session, book.id, EventType.CREATED, _payload(book, data.category))
    await session.commit()
    await session.refresh(book)
    return BookWithCategory(book=book, category_name=data.category)


async def update_book(session: AsyncSession, book_id: int, data: BookUpdate) -> BookWithCategory:
    book = await book_repository.get_by_id(session, book_id)
    if book is None:
        raise AppException(404, "NOT_FOUND", f"book not found: {book_id}")

    category_id = await _resolve_category_id(session, data.category)

    if data.isbn != book.isbn:
        existing = await book_repository.get_by_isbn(session, data.isbn)
        if existing is not None:
            raise AppException(409, "DUPLICATE_ISBN", f"isbn already exists: {data.isbn}")

    book.title = data.title
    book.author = data.author
    book.publisher = data.publisher
    book.category_id = category_id
    book.published_date = data.published_date
    book.isbn = data.isbn
    book.price = data.price
    book.stock = data.stock

    await _flush_or_conflict(session, data.isbn)

    outbox_repository.add_event(session, book.id, EventType.UPDATED, _payload(book, data.category))
    await session.commit()
    await session.refresh(book)
    return BookWithCategory(book=book, category_name=data.category)


async def delete_book(session: AsyncSession, book_id: int) -> None:
    book = await book_repository.get_by_id(session, book_id)
    if book is None:
        raise AppException(404, "NOT_FOUND", f"book not found: {book_id}")

    outbox_repository.add_event(session, book.id, EventType.DELETED, {"id": book.id})
    await book_repository.delete(session, book)
    await session.commit()
