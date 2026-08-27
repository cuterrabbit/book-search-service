from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.database import SessionLocal
from app.core.es_client import get_es_client

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict:
    return {"status": "UP"}


@router.get("/ready")
async def ready(response: Response) -> dict:
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        client = get_es_client()
        if not await client.ping():
            raise RuntimeError("es ping failed")
        return {"status": "UP"}
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "DOWN"}
