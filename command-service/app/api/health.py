from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.database import SessionLocal

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict:
    return {"status": "UP"}


@router.get("/ready")
async def ready(response: Response) -> dict:
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "UP"}
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "DOWN"}
