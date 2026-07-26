from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from .settings import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def session():
    async with SessionFactory() as db:
        yield db
