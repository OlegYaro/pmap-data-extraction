from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core import settings

engine = create_async_engine(settings.DB_URL, echo=False)

SessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
