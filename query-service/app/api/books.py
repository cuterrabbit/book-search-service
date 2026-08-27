from fastapi import APIRouter, Depends

from app.schemas.book import BookSearchResponse
from app.schemas.error import ErrorResponse
from app.schemas.search_params import BookSearchParams, get_search_params
from app.services import search_service

router = APIRouter(prefix="/api/books", tags=["books"])


@router.get(
    "/search",
    response_model=BookSearchResponse,
    responses={400: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def search(params: BookSearchParams = Depends(get_search_params)) -> BookSearchResponse:
    return await search_service.search_books(params)
