from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core import settings

engine = create_async_engine(settings.DB_URL, echo=False)

SessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def db_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency: session with a transaction."""

    async with SessionFactory.begin() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(db_session)]
