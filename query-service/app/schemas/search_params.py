from dataclasses import dataclass

from fastapi import Query

from app.core.exceptions import AppException

CATEGORIES = {
    "IT",
    "경제경영",
    "과학",
    "소설",
    "에세이",
    "여행",
    "역사",
    "예술",
    "인문",
    "자기계발",
}


@dataclass
class BookSearchParams:
    title: str | None
    category: str | None
    author: str | None
    publisher: str | None
    page: int
    size: int


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def get_search_params(
    title: str | None = Query(None, description="도서명 (부분 일치, 미지정 시 전체 조회)"),
    category: str | None = Query(None, description="카테고리 (완전 일치)"),
    author: str | None = Query(None, description="저자 (부분 일치)"),
    publisher: str | None = Query(None, description="출판사 (부분 일치)"),
    page: int = Query(0, ge=0, description="페이지 번호 (0부터 시작)"),
    size: int = Query(20, ge=1, le=100, description="페이지 크기 (1~100)"),
) -> BookSearchParams:
    category = _clean(category)
    if category is not None and category not in CATEGORIES:
        raise AppException(400, "INVALID_PARAMETER", f"unknown category: {category}")

    return BookSearchParams(
        title=_clean(title),
        category=category,
        author=_clean(author),
        publisher=_clean(publisher),
        page=page,
        size=size,
    )
