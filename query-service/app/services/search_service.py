import math

from app.repositories import book_search_repository
from app.schemas.book import BookSearchItem, BookSearchResponse
from app.schemas.search_params import BookSearchParams


async def search_books(params: BookSearchParams) -> BookSearchResponse:
    documents, total = await book_search_repository.search(params)
    content = [BookSearchItem(**doc) for doc in documents]
    total_pages = math.ceil(total / params.size) if total > 0 else 0

    return BookSearchResponse(
        content=content,
        page=params.page,
        size=params.size,
        total_elements=total,
        total_pages=total_pages,
    )
