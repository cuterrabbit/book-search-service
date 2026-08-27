from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.books import router as books_router
from app.api.health import router as health_router
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
)
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(title="Command Service", version="0.1.0")

# nginx가 붙기 전(9단계 이전)까지 프론트엔드가 다른 포트에서 직접 호출하므로 허용.
# nginx가 단일 origin으로 프록시하게 되면 제거해도 된다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(health_router)
app.include_router(books_router)

Instrumentator().instrument(app).expose(app)
