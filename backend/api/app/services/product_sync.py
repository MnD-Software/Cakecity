from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json


def money(value: object) -> Decimal:
    try:
        amount = Decimal(str(value or "0"))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Invalid WooCommerce price") from exc
    if amount < 0:
        raise ValueError("Price cannot be negative")
    return amount.quantize(Decimal("0.01"))


def meta_value(payload: dict, key: str, default=None):
    for item in payload.get("meta_data") or []:
        if item.get("key") == key:
            return item.get("value")
    return default


def list_value(value: object) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
        return [item.strip() for item in text.split(",") if item.strip()]
    return []


def dict_value(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def map_woo_product(payload: dict) -> dict:
    """Map the WooCommerce contract into the local browse model."""
    if not payload.get("id") or not payload.get("slug") or not payload.get("name"):
        raise ValueError("Product payload is missing id, slug or name")
    images = payload.get("images") or []
    preparation = meta_value(payload, "_cakecity_preparation_minutes", 180)
    try:
        preparation_minutes = min(10080, max(15, int(preparation)))
    except (TypeError, ValueError):
        preparation_minutes = 180
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
        "short_description": str(payload.get("short_description") or ""),
        "gallery": [
            {"src": str(image.get("src")), "alt": str(image.get("alt") or payload["name"])}
            for image in images[:12] if image.get("src")
        ],
        "categories": [
            str(category.get("name")) for category in (payload.get("categories") or [])
            if category.get("name")
        ],
        "attributes": [
            {"name": str(attribute.get("name")), "options": list_value(attribute.get("options"))}
            for attribute in (payload.get("attributes") or []) if attribute.get("name")
        ],
        "ingredients": str(meta_value(payload, "_cakecity_ingredients", "")).strip() or None,
        "allergens": [str(item) for item in list_value(meta_value(payload, "_cakecity_allergens"))],
        "nutrition": dict_value(meta_value(payload, "_cakecity_nutrition")),
        "preparation_minutes": preparation_minutes,
        "average_rating": money(payload.get("average_rating") or "0"),
        "review_count": max(0, int(payload.get("rating_count") or 0)),
        "upsell_woo_ids": [int(item) for item in (payload.get("upsell_ids") or [])],
        "cross_sell_woo_ids": [int(item) for item in (payload.get("cross_sell_ids") or [])],
        "video_url": str(meta_value(payload, "_cakecity_video_url", "")).strip() or None,
        "spin_image_urls": [
            str(item) for item in list_value(meta_value(payload, "_cakecity_360_images"))
            if str(item).startswith("https://")
        ][:36],
        "source_modified_at": payload.get("date_modified_gmt"),
        "synchronized_at": datetime.now(timezone.utc),
    }
