from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.settings import settings

async_postgres_engine = create_async_engine(settings.async_postgres_db_url, echo=False)

AsyncSessionLocal = async_sessionmaker(
	bind=async_postgres_engine,
	expire_on_commit=False,
	autoflush=False,
)

sync_postgres_engine = create_engine(settings.sync_postgres_db_url, echo=False)


async def get_postgres_session() -> AsyncGenerator[AsyncSession, None]:
	async with AsyncSessionLocal() as session:
		yield session
