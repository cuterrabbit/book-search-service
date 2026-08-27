from app.core.es_client import get_es_client
from app.schemas.search_params import BookSearchParams

INDEX_NAME = "books"


def _build_query(params: BookSearchParams) -> dict:
    must = []
    if params.title:
        must.append({"match": {"title": params.title}})
    if params.author:
        must.append({"match": {"author": params.author}})
    if params.publisher:
        must.append({"match": {"publisher": params.publisher}})

    filter_ = []
    if params.category:
        filter_.append({"term": {"category": params.category}})

    if not must and not filter_:
        return {"match_all": {}}
    return {"bool": {"must": must, "filter": filter_}}


async def search(params: BookSearchParams) -> tuple[list[dict], int]:
    client = get_es_client()
    response = await client.search(
        index=INDEX_NAME,
        query=_build_query(params),
        from_=params.page * params.size,
        size=params.size,
        track_total_hits=True,
    )
    hits = response["hits"]["hits"]
    total = response["hits"]["total"]["value"]
    documents = [hit["_source"] for hit in hits]
    return documents, total
