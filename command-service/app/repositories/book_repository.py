from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book


async def get_by_id(session: AsyncSession, book_id: int) -> Book | None:
    return await session.get(Book, book_id)


async def get_by_isbn(session: AsyncSession, isbn: str) -> Book | None:
    result = await session.execute(select(Book).where(Book.isbn == isbn))
    return result.scalar_one_or_none()


def add(session: AsyncSession, book: Book) -> None:
    session.add(book)


async def delete(session: AsyncSession, book: Book) -> None:
    await session.delete(book)
