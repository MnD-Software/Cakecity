from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import session
from ..models import Product
from ..schemas import ProductPage, ProductRead

router = APIRouter(prefix="/v1/catalog", tags=["catalog"])


@router.get("/products", response_model=ProductPage)
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=60),
    search: str | None = Query(None, max_length=120),
    db: AsyncSession = Depends(session),
):
    filters = [Product.status == "publish", Product.in_stock.is_(True)]
    if search:
        filters.append(Product.name.ilike(f"%{search.strip()}%"))
    total = await db.scalar(select(func.count(Product.id)).where(*filters))
    statement = (
        select(Product).where(*filters).order_by(Product.synchronized_at.desc(), Product.name)
        .offset((page - 1) * page_size).limit(page_size)
    )
    items = list((await db.scalars(statement)).all())
    newest = await db.scalar(select(func.max(Product.synchronized_at)))
    return ProductPage(
        items=[ProductRead.model_validate(item) for item in items],
        page=page, page_size=page_size, total=total or 0, synchronized_at=newest,
    )


@router.get("/products/{slug}", response_model=ProductRead)
async def product_detail(slug: str, db: AsyncSession = Depends(session)):
    product = await db.scalar(select(Product).where(Product.slug == slug, Product.status == "publish"))
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductRead.model_validate(product)
