import asyncio
import logging

from app.core.es_client import close_es_client, get_es_client
from app.core.logging import configure_logging

logger = logging.getLogger("bootstrap_index")

INDEX_NAME = "books"

SETTINGS = {
    "analysis": {
        "analyzer": {
            "korean": {
                "type": "custom",
                "tokenizer": "nori_tokenizer",
                "filter": ["nori_readingform", "lowercase"],
            }
        }
    }
}

MAPPINGS = {
    "properties": {
        "id": {"type": "long"},
        "title": {"type": "text", "analyzer": "korean"},
        "author": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
        "publisher": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
        "category": {"type": "keyword"},
        "published_date": {"type": "date"},
        "isbn": {"type": "keyword"},
        "price": {"type": "integer"},
        "stock": {"type": "integer"},
    }
}


async def run() -> None:
    client = get_es_client()
    if await client.indices.exists(index=INDEX_NAME):
        logger.info("index '%s' already exists, skipping", INDEX_NAME)
    else:
        await client.indices.create(index=INDEX_NAME, settings=SETTINGS, mappings=MAPPINGS)
        logger.info("created index '%s'", INDEX_NAME)
    await close_es_client()


def main() -> None:
    configure_logging()
    asyncio.run(run())


if __name__ == "__main__":
    main()
