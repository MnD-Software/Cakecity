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
