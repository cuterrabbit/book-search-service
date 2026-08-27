from fastapi import APIRouter, Response, status

from app.core.es_client import get_es_client

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict:
    return {"status": "UP"}


@router.get("/ready")
async def ready(response: Response) -> dict:
    try:
        client = get_es_client()
        if not await client.ping():
            raise RuntimeError("ping failed")
        return {"status": "UP"}
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "DOWN"}
