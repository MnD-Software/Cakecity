from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    woo_id: int
    slug: str
    name: str
    description: str
    price_kes: Decimal = Field(ge=0)
    regular_price_kes: Decimal | None
    in_stock: bool
    stock_quantity: int | None
    image_url: str | None
    average_rating: Decimal = Decimal("0")
    review_count: int = 0


class ProductDetail(ProductRead):
    description: str
    short_description: str
    gallery: list[dict] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    attributes: list[dict] = Field(default_factory=list)
    ingredients: str | None = None
    allergens: list[str] = Field(default_factory=list)
    nutrition: dict = Field(default_factory=dict)
    preparation_minutes: int = 180
    video_url: str | None = None
    spin_image_urls: list[str] = Field(default_factory=list)
    recommendations: list[ProductRead] = Field(default_factory=list)


class ProductPage(BaseModel):
    items: list[ProductRead]
    page: int
    page_size: int
    total: int
    synchronized_at: datetime | None


class WebhookReceipt(BaseModel):
    accepted: bool
    duplicate: bool
    delivery_key: str
