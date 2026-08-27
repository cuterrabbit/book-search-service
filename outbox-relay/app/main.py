import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.health import router as health_router
from app.core.es_client import close_es_client
from app.core.logging import configure_logging
from app.relay.poller import run_forever

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = asyncio.Event()
    task = asyncio.create_task(run_forever(stop_event))
    yield
    stop_event.set()
    await task
    await close_es_client()


app = FastAPI(title="Outbox Relay", version="0.1.0", lifespan=lifespan)

app.include_router(health_router)

Instrumentator().instrument(app).expose(app)
