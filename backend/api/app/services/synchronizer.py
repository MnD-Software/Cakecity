from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Product
from .product_sync import map_woo_product


async def upsert_product(db: AsyncSession, payload: dict) -> None:
    values = map_woo_product(payload)
    statement = insert(Product).values(**values)
    mutable = {key: getattr(statement.excluded, key) for key in values if key != "woo_id"}
    await db.execute(statement.on_conflict_do_update(index_elements=[Product.woo_id], set_=mutable))


async def synchronize_products(db: AsyncSession, client) -> int:
    synchronized = 0
    async for page in client.product_pages():
        for payload in page:
            await upsert_product(db, payload)
            synchronized += 1
        await db.commit()
    return synchronized
