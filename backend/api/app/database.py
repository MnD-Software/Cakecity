from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from .settings import settings

engine = create_async_engine(
    settings.database_url, pool_pre_ping=True,
    pool_size=settings.database_pool_size, max_overflow=settings.database_max_overflow,
    pool_recycle=1800,
)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def session():
    async with SessionFactory() as db:
        yield db
