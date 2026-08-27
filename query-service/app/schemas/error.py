from pydantic import BaseModel


class ErrorResponse(BaseModel):
    status: int
    error: str
    message: str
    path: str
