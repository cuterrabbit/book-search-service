import argparse
import asyncio
import csv
import logging
from datetime import date
from pathlib import Path

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.models.book import Book
from app.models.category import Category
from app.models.outbox import BookOutbox, EventType

logger = logging.getLogger("load_csv")

DEFAULT_CSV_PATH = Path(__file__).resolve().parents[3] / "data" / "books.csv"
DEFAULT_BATCH_SIZE = 1000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load books.csv into MariaDB")
    parser.add_argument("--csv-path", type=Path, default=DEFAULT_CSV_PATH)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    return parser.parse_args()


def read_rows(csv_path: Path) -> list[dict]:
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


async def load_categories(session: AsyncSession, rows: list[dict]) -> dict[str, int]:
    names = sorted({row["category"] for row in rows})
    existing = {
        c.name: c.id for c in (await session.execute(select(Category))).scalars().all()
    }
    new_names = [name for name in names if name not in existing]
    if new_names:
        await session.execute(insert(Category), [{"name": name} for name in new_names])
        await session.commit()
        existing = {
            c.name: c.id for c in (await session.execute(select(Category))).scalars().all()
        }
    return existing


async def load_books(
    session: AsyncSession,
    rows: list[dict],
    category_ids: dict[str, int],
    batch_size: int,
) -> int:
    total = 0
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]

        book_values = []
        outbox_values = []
        for row in batch:
            book_id = int(row["id"])
            published_date = date.fromisoformat(row["published_date"])
            title = row["title"]
            author = row["author"]
            publisher = row["publisher"]
            isbn = row["isbn"]
            price = int(row["price"])
            stock = int(row["stock"])

            book_values.append(
                {
                    "id": book_id,
                    "title": title,
                    "author": author,
                    "publisher": publisher,
                    "category_id": category_ids[row["category"]],
                    "published_date": published_date,
                    "isbn": isbn,
                    "price": price,
                    "stock": stock,
                }
            )
            outbox_values.append(
                {
                    "book_id": book_id,
                    "event_type": EventType.CREATED,
                    "payload": {
                        "id": book_id,
                        "title": title,
                        "author": author,
                        "publisher": publisher,
                        "category": row["category"],
                        "published_date": published_date.isoformat(),
                        "isbn": isbn,
                        "price": price,
                        "stock": stock,
                    },
                }
            )

        await session.execute(insert(Book), book_values)
        await session.execute(insert(BookOutbox), outbox_values)
        await session.commit()

        total += len(batch)
        logger.info("loaded %d/%d books", total, len(rows))
    return total


async def run(csv_path: Path, batch_size: int) -> None:
    rows = read_rows(csv_path)
    logger.info("read %d rows from %s", len(rows), csv_path)

    async with SessionLocal() as session:
        category_ids = await load_categories(session, rows)
        logger.info("categories ready: %d (%s)", len(category_ids), sorted(category_ids))
        total = await load_books(session, rows, category_ids, batch_size)

    logger.info("done: %d books loaded", total)


def main() -> None:
    configure_logging()
    args = parse_args()
    asyncio.run(run(args.csv_path, args.batch_size))


if __name__ == "__main__":
    main()
