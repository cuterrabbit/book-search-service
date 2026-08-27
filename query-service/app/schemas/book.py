from datetime import date

from pydantic import BaseModel


class BookSearchItem(BaseModel):
    id: int
    title: str
    author: str
    publisher: str
    category: str
    published_date: date
    isbn: str
    price: int
    stock: int


class BookSearchResponse(BaseModel):
    content: list[BookSearchItem]
    page: int
    size: int
    total_elements: int
    total_pages: int
