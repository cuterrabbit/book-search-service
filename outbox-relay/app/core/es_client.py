from elasticsearch import AsyncElasticsearch

from app.core.config import get_settings

settings = get_settings()

_client: AsyncElasticsearch | None = None


def get_es_client() -> AsyncElasticsearch:
    global _client
    if _client is None:
        _client = AsyncElasticsearch(hosts=[f"http://{settings.es_host}:{settings.es_port}"])
    return _client


async def close_es_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
