# 도서 검색 서비스 — 설계 문서

## 1. 개요

`data/books.csv`(약 3만 건, 컬럼: `id,title,author,publisher,category,published_date,isbn,price,stock`)를 이용해 도서 검색 서비스를 구현한다.

- **백엔드 중심**: CRUD API, 스키마 설계, 검색 API, Pagination, 잘못된 파라미터 처리를 핵심으로 본다.
- **프론트엔드**: 검색/목록/페이지 이동/빈 결과 처리만 되는 최소 정적 페이지.
- **아키텍처**: CQRS — 쓰기(MariaDB)와 읽기(Elasticsearch)를 완전히 분리된 서비스로 배포한다.
- **라우팅**: nginx가 단일 진입점 역할을 하며 정적 프론트엔드 서빙 + API 라우팅을 담당한다.

CSV 데이터 특성 확인 결과: `category`는 10종 고정값(IT/경제경영/과학/소설/에세이/여행/역사/예술/인문/자기계발), `isbn`은 중복 없음, `title`은 중복 4,634건 존재(검색 테스트에 유리).

## 2. 아키텍처

```
[Browser] → [nginx :80]
              ├─ /                              → 정적 프론트엔드 (HTML/JS)
              ├─ GET  /api/books/search          ─┐
              ├─ GET  /api/books/{id}             ├─→ query-service (FastAPI) ──→ Elasticsearch
              ├─ POST /api/books                  │
              ├─ PUT  /api/books/{id}             ├─→ command-service (FastAPI) ──→ MariaDB
              └─ DELETE /api/books/{id}           ┘        │
                                                            │ (같은 트랜잭션으로 book_outbox insert)
                                                            ▼
                                                    outbox-relay (FastAPI + polling loop)
                                                            │ PENDING 이벤트 폴링
                                                            ▼
                                                       Elasticsearch 색인 반영
```

## 3. 결정 사항 요약

| 항목 | 결정 | 이유 |
|---|---|---|
| 서비스 분리 수준 | command-service / query-service 완전 분리(독립 배포) | 인프라 레벨에서 CQRS 강제 — query-service는 MariaDB 접근 권한 자체가 없음 |
| MariaDB→ES 동기화 | Transactional Outbox + Polling Relay | dual-write 원자성 문제 회피, at-least-once 전달 |
| 한국어 검색 분석기 | Nori (analysis-nori 플러그인) | 조사/어미 처리로 관련도 높은 검색 |
| MariaDB 정규화 범위 | `category`만 정규화(FK), `author`/`publisher`는 컬럼으로 유지 | category는 10종 고정 enum성 데이터, author/publisher는 CSV 적재 시 find-or-create 매칭 리스크만 늘림 |
| 언어/프레임워크 | Python 3.12 + FastAPI | Swagger(OpenAPI)가 내장 제공됨 |
| 패키지 관리 | 서비스별 `requirements.txt` | 3개 서비스가 독립 배포되므로 각자 최소 의존성만 유지 |
| DB 드라이버 | SQLAlchemy 2.0(async) + `asyncmy` | 비동기 MariaDB 접근 |
| ES 클라이언트 | `elasticsearch` 공식 파이썬 클라이언트(async) | 클러스터 버전과 매치 |
| 공유 코드 | 없음 (category 목록도 서비스별로 중복 유지) | 서비스 간 빌드 의존성을 만들지 않기 위해 — 10개 고정값 중복은 실질적 드리프트 위험이 없음 |

## 4. 서비스별 책임과 저장소 접근 권한

| 서비스 | 역할 | MariaDB | Elasticsearch |
|---|---|---|---|
| `command-service` | 도서 등록/수정/삭제, CSV 최초 적재 | 읽기/쓰기 | 접근 안 함 |
| `query-service` | 도서 검색 | 접근 안 함 (계정 자체를 안 줌) | 읽기 |
| `outbox-relay` | MariaDB→ES 동기화 | 읽기 | 쓰기 |

## 5. 데이터 모델

### 5.1 MariaDB

```sql
CREATE TABLE categories (
    id   BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE books (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    title           VARCHAR(255) NOT NULL,
    author          VARCHAR(255) NOT NULL,
    publisher       VARCHAR(255) NOT NULL,
    category_id     BIGINT NOT NULL,
    published_date  DATE NOT NULL,
    isbn            VARCHAR(20) NOT NULL UNIQUE,
    price           INT NOT NULL,
    stock           INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    INDEX idx_category (category_id)
);

CREATE TABLE book_outbox (
    id            BIGINT PRIMARY KEY AUTO_INCREMENT,
    book_id       BIGINT NOT NULL,
    event_type    ENUM('CREATED','UPDATED','DELETED') NOT NULL,
    payload       JSON NOT NULL,
    status        ENUM('PENDING','SENT','FAILED') NOT NULL DEFAULT 'PENDING',
    retry_count   INT NOT NULL DEFAULT 0,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at  TIMESTAMP NULL,
    INDEX idx_status_created (status, created_at)
);
```

- `books` 변경과 `book_outbox` insert는 같은 트랜잭션.
- ISBN 중복은 UNIQUE 제약 위반 → command-service가 409로 매핑.
- outbox-relay는 단일 인스턴스로만 운영하므로 동시 폴링 잠금(`FOR UPDATE SKIP LOCKED` 등)은 불필요.

### 5.2 Elasticsearch (`books` 인덱스)

```json
{
  "settings": {
    "analysis": {
      "analyzer": {
        "korean": {
          "type": "custom",
          "tokenizer": "nori_tokenizer",
          "filter": ["nori_readingform", "lowercase"]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "id":             { "type": "long" },
      "title":          { "type": "text", "analyzer": "korean" },
      "author":         { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
      "publisher":      { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
      "category":       { "type": "keyword" },
      "published_date": { "type": "date" },
      "isbn":           { "type": "keyword" },
      "price":          { "type": "integer" },
      "stock":          { "type": "integer" }
    }
  }
}
```

Nori 플러그인은 커스텀 Dockerfile에서 `bin/elasticsearch-plugin install analysis-nori`로 이미지 빌드 시 설치.

## 6. API 명세

### 6.1 Command API (`command-service`)

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/books` | 도서 등록 |
| PUT | `/api/books/{id}` | 도서 수정 |
| DELETE | `/api/books/{id}` | 도서 삭제 |

- 검증: `title`/`author`/`publisher` 필수, `category`는 존재하는 값이어야 함(400), `price`/`stock` ≥ 0.
- ISBN 중복 → 409.
- 존재하지 않는 id 수정/삭제 → 404.

### 6.2 Query API (`query-service`)

`GET /api/books/search`

| 파라미터 | 기본값 | 검증 규칙 |
|---|---|---|
| `title` | 없음 | 없으면 전체 목록(match_all)로 동작, nori 분석기로 매칭 |
| `category` | 없음 | 10종 값 밖이면 400 (`AppException`, 도메인 규칙 위반) |
| `author`, `publisher` | 없음 | 부분 일치(match) |
| `page` | 0 | 정수 아니거나 <0이면 422 (FastAPI `Query(ge=0)` 제약 위반) |
| `size` | 20 | 정수 아니거나 1~100 벗어나면 422 (FastAPI `Query(ge=1,le=100)` 제약 위반) |

category처럼 값 목록을 조회해야 확인 가능한 "의미론적" 오류는 400, page/size처럼 타입·범위만으로 판별 가능한 "구문적" 오류는 422로 구분한다(command-service의 가격/재고 음수 검증과 동일한 원칙).

응답 예 (필드는 snake_case — Python/FastAPI 컨벤션에 맞춤):
```json
{
  "content": [ { "id": 1, "title": "...", "author": "...", "category": "...", "published_date": "2020-02-03", "isbn": "...", "price": 18000, "stock": 45 } ],
  "page": 0,
  "size": 20,
  "total_elements": 0,
  "total_pages": 0
}
```
결과가 0건이어도 200 + 빈 `content` 배열(조건은 유효하나 결과 없음 — 404와 구분).

### 6.3 공통 에러 포맷

```json
{ "status": 400, "error": "INVALID_PARAMETER", "message": "size must be between 1 and 100", "path": "/api/books/search" }
```
FastAPI의 `RequestValidationError` 핸들러와 커스텀 `AppException` 핸들러를 통해 위 포맷으로 통일한다.

## 7. Outbox Relay

- `book_outbox`에서 `status='PENDING'`인 행을 배치(예: 500건)로 폴링.
- 이벤트 타입에 따라 ES에 index/update/delete 반영 후 `SENT`로 갱신, 실패 시 `retry_count` 증가(임계치 초과 시 `FAILED`).
- 폴링 주기: 1초 간격 asyncio 루프.

## 8. 초기 CSV 적재

`command-service`에 배치 진입점(`python -m app.cli.load_csv`)을 둔다:
CSV 읽기 → `categories` 10종 upsert → `books` 벌크 insert → 각 행마다 `book_outbox`에 `CREATED` 이벤트 적재.
평소 쓰기 경로(outbox)를 그대로 재사용해서, 초기 적재 자체가 파이프라인 정합성 검증이 되게 한다.

## 9. nginx 라우팅

경로만으로는 `/api/books/{id}`가 command(PUT/DELETE)와 query(GET)에서 겹치므로 method 기반으로 업스트림을 나눈다:

```nginx
map $request_method $books_upstream {
    default command_service;
    GET     query_service;
}

server {
    listen 80;

    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    location /api/books {
        proxy_pass http://$books_upstream;
    }
}
```

## 10. 개발 환경 (Swagger / Actuator / Test)

각 FastAPI 서비스는 동일한 패턴을 따른다.

- **Swagger**: FastAPI 기본 제공 — `/docs`(Swagger UI), `/redoc`, `/openapi.json`. 별도 설정 불필요.
- **Actuator에 대응하는 엔드포인트**:
  - `GET /health/live` — 프로세스 생존 여부만 확인, 항상 200
  - `GET /health/ready` — 의존 저장소 연결 확인 (command-service: `SELECT 1`, query-service: ES `ping()`), 실패 시 503
  - `GET /metrics` — `prometheus-fastapi-instrumentator`로 자동 계측된 Prometheus 포맷 메트릭
- **테스트**: `pytest` + `pytest-asyncio` + `httpx`(FastAPI `TestClient`). command-service는 SQLite in-memory(`aiosqlite`, `StaticPool`)로 `get_db` 의존성을 오버라이드해서 실제 API 엔드포인트를 빠르게 검증(단위 테스트). 저장소 의존성이 필요한 통합 테스트는 `testcontainers-python`으로 MariaDB/Elasticsearch를 임시로 띄워 검증 가능(아직 미작성, 필요 시 `@pytest.mark.integration`으로 분리).
- **주의**: `elasticsearch` 파이썬 클라이언트는 서버(8.15.0)와 메이저 버전을 맞춰야 함 — `pip install elasticsearch`로 최신(9.x)을 설치하면 클라이언트/서버 프로토콜 불일치로 모든 요청이 400을 반환한다. `elasticsearch>=8.15,<9`로 고정. `AsyncElasticsearch`는 `aiohttp`도 별도로 설치해야 동작함.

## 11. 디렉토리 구조

```
과제테스트/
├── data/
│   └── books.csv
├── command-service/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── exceptions.py
│   │   │   └── logging.py
│   │   ├── models/
│   │   │   ├── category.py
│   │   │   ├── book.py
│   │   │   └── outbox.py
│   │   ├── schemas/
│   │   │   ├── book.py
│   │   │   └── error.py
│   │   ├── repositories/
│   │   │   ├── book_repository.py
│   │   │   ├── category_repository.py
│   │   │   └── outbox_repository.py
│   │   ├── services/
│   │   │   └── book_service.py
│   │   ├── api/
│   │   │   ├── books.py
│   │   │   └── health.py
│   │   └── cli/
│   │       └── load_csv.py
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   ├── alembic.ini
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_health.py
│   │   └── test_books.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── Dockerfile
│   ├── pytest.ini
│   └── .env.example
├── query-service/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── es_client.py
│   │   │   ├── exceptions.py
│   │   │   └── logging.py
│   │   ├── schemas/
│   │   │   ├── book.py
│   │   │   ├── search_params.py
│   │   │   └── error.py
│   │   ├── repositories/
│   │   │   └── book_search_repository.py
│   │   ├── services/
│   │   │   └── search_service.py
│   │   ├── api/
│   │   │   ├── books.py
│   │   │   └── health.py
│   │   └── cli/
│   │       └── bootstrap_index.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_health.py
│   │   └── test_search.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── Dockerfile
│   ├── pytest.ini
│   └── .env.example
├── outbox-relay/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── es_client.py
│   │   │   └── logging.py
│   │   ├── models/
│   │   │   └── outbox.py
│   │   ├── relay/
│   │   │   └── poller.py
│   │   └── api/
│   │       └── health.py
│   ├── tests/
│   │   ├── test_health.py
│   │   └── test_poller.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── Dockerfile
│   ├── pytest.ini
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── nginx/
│   └── conf.d/default.conf
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
└── DESIGN.md
```

## 12. 구현 순서

1. **리포지토리 스캐폴딩** — 위 디렉토리 구조 생성, 각 서비스 FastAPI 골격(`/health/live`, `/health/ready`, `/metrics`, Swagger 확인), `docker-compose.yml`에 mariadb/elasticsearch/3개 서비스 배선, pytest 샘플 테스트 통과 확인.
2. **MariaDB 스키마 & command-service 골격** — SQLAlchemy 모델, Alembic 첫 마이그레이션 적용, DB 연결 확인.
3. **CSV 적재 배치** — `load_csv.py` 구현, MariaDB에 3만 건 적재 검증.
4. **Command API 구현** — 등록/수정/삭제 + 검증/예외 처리 + outbox 기록, 단위 테스트.
5. **Elasticsearch 인덱스 준비** — nori 포함 커스텀 이미지 빌드, 매핑 생성 스크립트.
6. **Outbox Relay 구현** — 폴링 루프, ES 반영, 초기 3만 건이 ES까지 흘러가는지 end-to-end 확인.
7. **Query API 구현** — 검색/페이지네이션/파라미터 검증/빈 결과 처리, 단위·통합 테스트.
8. **프론트엔드 구현** — 검색창/목록/페이지 이동/빈 상태 UI.
9. **nginx 라우팅 & docker-compose 통합** — method 기반 라우팅 적용, 전체 스택 기동 후 nginx 경유 e2e 검증.
10. **테스트/문서 마무리** — `pytest` 전체 실행, README 정리.

현재 상태: 1~6단계 완료.
- 4단계: Command API(등록/수정/삭제) 구현 + 단위 테스트(SQLite in-memory) 8건 통과.
- 5단계: nori 플러그인 포함 커스텀 Elasticsearch 이미지 빌드, `books` 인덱스 매핑 생성 스크립트(query-service `app/cli/bootstrap_index.py`) 구현 및 실제 적용 확인.
- 6단계: Outbox Relay 폴링 루프(ES bulk API 사용) 구현 + 단위 테스트 통과, 실제 3만 건이 MariaDB→ES로 전량 동기화되는 것까지 end-to-end 검증 완료(ES 문서 수 30,000, outbox 전부 SENT).

7단계(Query API) 완료: `GET /api/books/search` 구현(title/category/author/publisher 필터 + page/size 페이지네이션). 리포지토리 계층을 monkeypatch로 대체한 단위 테스트 8건 통과, 실제 30,001건 규모의 ES에 대해서도 검증 완료(제목 "사전" 검색 840건 정확히 반환, 카테고리 필터+페이지네이션 수식 정확, 빈 category/과도한 size 등 잘못된 파라미터 처리 정상).

8단계(프론트엔드) 완료: 검색/등록/수정/삭제(CRUD)가 되는 단일 페이지(`frontend/`, 프레임워크 없는 순수 HTML/CSS/JS) 구현. Playwright로 실제 브라우저에서 검색·페이지네이션·등록·수정·삭제·빈 결과 화면까지 전부 검증.

9단계(nginx & docker-compose 통합) 완료: `nginx/conf.d/default.conf`에서 `map $request_method`로 GET은 query-service, 나머지는 command-service로 라우팅 + 정적 프론트엔드 서빙. 3개 Python 서비스를 `docker compose build`로 컨테이너화하고 전체 스택(`mariadb/elasticsearch/command-service/query-service/outbox-relay/nginx`, 총 6개 컨테이너) 기동 후 nginx 경유로 검색(200)·등록(201)·삭제(204) e2e 검증 완료. 프론트엔드는 nginx 단일 origin 기준 상대경로(`/api/books/...`)로 전환.

구현 중 발견/수정한 이슈: `command-service`의 Docker 이미지에 `data/`(CSV)가 포함되지 않아 컨테이너 안에서 `load_csv.py`가 실행되지 않던 문제 — `docker-compose.yml`에 `./data:/data:ro` 볼륨을 추가해 해결(마운트 경로는 `load_csv.py`의 자동 경로 탐지 로직이 컨테이너 안에서 계산하는 `/data`와 정확히 맞춰야 함 — `/app/data`로 마운트하면 안 됨).

10단계(테스트/문서 마무리) 완료: `README.md`(목차/아키텍처 다이어그램/실행방법/기술스택/구현범위 체크리스트/생략한 부분/개선하고 싶은 부분) 작성.

**전체 로드맵 1~10단계 완료.**
