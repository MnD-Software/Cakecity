from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


def money(value: object) -> Decimal:
    try:
        amount = Decimal(str(value or "0"))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Invalid WooCommerce price") from exc
    if amount < 0:
        raise ValueError("Price cannot be negative")
    return amount.quantize(Decimal("0.01"))


def map_woo_product(payload: dict) -> dict:
    """Map the WooCommerce contract into the local browse model."""
    if not payload.get("id") or not payload.get("slug") or not payload.get("name"):
        raise ValueError("Product payload is missing id, slug or name")
    images = payload.get("images") or []
    return {
        "woo_id": int(payload["id"]),
        "slug": str(payload["slug"]),
        "name": str(payload["name"]),
        "description": str(payload.get("description") or ""),
        "price_kes": money(payload.get("price")),
        "regular_price_kes": money(payload["regular_price"]) if payload.get("regular_price") else None,
        "stock_quantity": payload.get("stock_quantity"),
        "in_stock": payload.get("stock_status") == "instock",
        "status": str(payload.get("status") or "draft"),
        "image_url": images[0].get("src") if images else None,
        "source_modified_at": payload.get("date_modified_gmt"),
        "synchronized_at": datetime.now(timezone.utc),
    }
