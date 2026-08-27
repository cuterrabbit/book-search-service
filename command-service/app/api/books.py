from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.book import BookCreate, BookResponse, BookUpdate
from app.schemas.error import ErrorResponse
from app.services import book_service
from app.services.book_service import BookWithCategory

router = APIRouter(prefix="/api/books", tags=["books"])

_ERROR_RESPONSES = {
    400: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}


def _to_response(result: BookWithCategory) -> BookResponse:
    return BookResponse(
        id=result.book.id,
        title=result.book.title,
        author=result.book.author,
        publisher=result.book.publisher,
        category=result.category_name,
        published_date=result.book.published_date,
        isbn=result.book.isbn,
        price=result.book.price,
        stock=result.book.stock,
        created_at=result.book.created_at,
        updated_at=result.book.updated_at,
    )


@router.post(
    "",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_ERROR_RESPONSES,
)
async def create_book(data: BookCreate, session: AsyncSession = Depends(get_db)) -> BookResponse:
    result = await book_service.create_book(session, data)
    return _to_response(result)


@router.put(
    "/{book_id}",
    response_model=BookResponse,
    responses=_ERROR_RESPONSES,
)
async def update_book(
    book_id: int, data: BookUpdate, session: AsyncSession = Depends(get_db)
) -> BookResponse:
    result = await book_service.update_book(session, book_id, data)
    return _to_response(result)


@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_ERROR_RESPONSES,
)
async def delete_book(book_id: int, session: AsyncSession = Depends(get_db)) -> None:
    await book_service.delete_book(session, book_id)
