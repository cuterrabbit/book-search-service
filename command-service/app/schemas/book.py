from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class BookBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    author: str = Field(min_length=1, max_length=255)
    publisher: str = Field(min_length=1, max_length=255)
    category: str
    published_date: date
    isbn: str = Field(min_length=1, max_length=20)
    price: int = Field(ge=0)
    stock: int = Field(ge=0)


class BookCreate(BookBase):
    pass


class BookUpdate(BookBase):
    pass


class BookResponse(BookBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
