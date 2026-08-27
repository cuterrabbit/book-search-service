def _payload(isbn: str, **overrides) -> dict:
    base = {
        "title": "테스트 도서",
        "author": "테스트 저자",
        "publisher": "테스트 출판사",
        "category": "IT",
        "published_date": "2024-01-01",
        "isbn": isbn,
        "price": 10000,
        "stock": 5,
    }
    base.update(overrides)
    return base


async def test_create_book_success(client) -> None:
    response = await client.post("/api/books", json=_payload("9791100000001"))
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "테스트 도서"
    assert body["category"] == "IT"
    assert body["id"] > 0


async def test_create_book_unknown_category(client) -> None:
    response = await client.post(
        "/api/books", json=_payload("9791100000002", category="없는카테고리")
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "INVALID_PARAMETER"


async def test_create_book_duplicate_isbn(client) -> None:
    payload = _payload("9791100000003")
    first = await client.post("/api/books", json=payload)
    assert first.status_code == 201

    second = await client.post("/api/books", json=payload)
    assert second.status_code == 409
    assert second.json()["error"] == "DUPLICATE_ISBN"


async def test_create_book_negative_price(client) -> None:
    response = await client.post("/api/books", json=_payload("9791100000004", price=-100))
    assert response.status_code == 422


async def test_update_book_not_found(client) -> None:
    response = await client.put("/api/books/9999", json=_payload("9791100000005"))
    assert response.status_code == 404
    assert response.json()["error"] == "NOT_FOUND"


async def test_update_book_success(client) -> None:
    create_resp = await client.post("/api/books", json=_payload("9791100000006"))
    book_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/books/{book_id}", json=_payload("9791100000006", price=20000, stock=1)
    )
    assert update_resp.status_code == 200
    body = update_resp.json()
    assert body["price"] == 20000
    assert body["stock"] == 1


async def test_delete_book(client) -> None:
    create_resp = await client.post("/api/books", json=_payload("9791100000007"))
    book_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/books/{book_id}")
    assert delete_resp.status_code == 204

    second_delete = await client.delete(f"/api/books/{book_id}")
    assert second_delete.status_code == 404
