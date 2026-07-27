from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.engine import make_url
from .settings import settings

database_url = make_url(settings.database_url)
ssl_mode = database_url.query.get("sslmode")
database_url = database_url.difference_update_query(["sslmode", "channel_binding"])
connect_args = {"ssl": True} if ssl_mode in {"require", "verify-ca", "verify-full"} else {}

engine = create_async_engine(
    database_url, pool_pre_ping=True, connect_args=connect_args,
    pool_size=settings.database_pool_size, max_overflow=settings.database_max_overflow,
    pool_recycle=1800,
)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def session():
    async with SessionFactory() as db:
        yield db
