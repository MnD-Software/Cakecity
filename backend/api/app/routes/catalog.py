from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import session
from ..models import Product
from ..schemas import ProductDetail, ProductPage, ProductRead

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


@router.get("/products/{slug}", response_model=ProductDetail)
async def product_detail(slug: str, db: AsyncSession = Depends(session)):
    product = await db.scalar(select(Product).where(Product.slug == slug, Product.status == "publish"))
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    priority_ids = [*product.upsell_woo_ids, *product.cross_sell_woo_ids]
    ranking = [Product.average_rating.desc(), Product.name]
    if priority_ids:
        ranking.insert(0, case((Product.woo_id.in_(priority_ids), 0), else_=1))
    recommendations = list((await db.scalars(
        select(Product).where(
            Product.id != product.id, Product.status == "publish", Product.in_stock.is_(True)
        ).order_by(*ranking).limit(6)
    )).all())
    return ProductDetail.model_validate(product).model_copy(update={
        "recommendations": [ProductRead.model_validate(item) for item in recommendations]
    })
