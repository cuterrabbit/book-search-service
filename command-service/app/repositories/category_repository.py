from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category


async def get_by_name(session: AsyncSession, name: str) -> Category | None:
    result = await session.execute(select(Category).where(Category.name == name))
    return result.scalar_one_or_none()
