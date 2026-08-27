from app.repositories import book_search_repository

SAMPLE_DOC = {
    "id": 1,
    "title": "테스트 도서",
    "author": "테스트 저자",
    "publisher": "테스트 출판사",
    "category": "IT",
    "published_date": "2024-01-01",
    "isbn": "9791100000001",
    "price": 10000,
    "stock": 5,
}


async def test_search_returns_results(client, monkeypatch) -> None:
    async def fake_search(params):
        return [SAMPLE_DOC], 1

    monkeypatch.setattr(book_search_repository, "search", fake_search)

    response = await client.get("/api/books/search", params={"title": "테스트"})
    assert response.status_code == 200
    body = response.json()
    assert body["total_elements"] == 1
    assert body["total_pages"] == 1
    assert body["content"][0]["title"] == "테스트 도서"


async def test_search_no_results(client, monkeypatch) -> None:
    async def fake_search(params):
        return [], 0

    monkeypatch.setattr(book_search_repository, "search", fake_search)

    response = await client.get("/api/books/search", params={"title": "존재하지않음"})
    assert response.status_code == 200
    body = response.json()
    assert body["content"] == []
    assert body["total_elements"] == 0
    assert body["total_pages"] == 0


async def test_search_without_title_still_succeeds(client, monkeypatch) -> None:
    async def fake_search(params):
        assert params.title is None
        return [SAMPLE_DOC], 1

    monkeypatch.setattr(book_search_repository, "search", fake_search)

    response = await client.get("/api/books/search")
    assert response.status_code == 200


async def test_search_unknown_category(client) -> None:
    response = await client.get("/api/books/search", params={"category": "없는카테고리"})
    assert response.status_code == 400
    assert response.json()["error"] == "INVALID_PARAMETER"


async def test_search_invalid_page(client) -> None:
    response = await client.get("/api/books/search", params={"page": -1})
    assert response.status_code == 422


async def test_search_invalid_size(client) -> None:
    response = await client.get("/api/books/search", params={"size": 1000})
    assert response.status_code == 422


async def test_search_default_pagination(client, monkeypatch) -> None:
    async def fake_search(params):
        assert params.page == 0
        assert params.size == 20
        return [], 0

    monkeypatch.setattr(book_search_repository, "search", fake_search)
    response = await client.get("/api/books/search")
    assert response.status_code == 200
