from decimal import Decimal
import pytest
from app.services.product_sync import map_woo_product, money


def test_maps_woocommerce_product_into_browse_model():
    result = map_woo_product({
        "id": 901, "slug": "red-velvet", "name": "Red Velvet", "price": "3200",
        "regular_price": "3500", "stock_status": "instock", "stock_quantity": 8,
        "status": "publish", "images": [{"src": "https://cdn.example/cake.webp"}],
    })
    assert result["woo_id"] == 901
    assert result["price_kes"] == Decimal("3200.00")
    assert result["in_stock"] is True
    assert result["image_url"].endswith("cake.webp")


def test_rejects_incomplete_product():
    with pytest.raises(ValueError):
        map_woo_product({"id": 1})


def test_rejects_negative_price():
    with pytest.raises(ValueError):
        money("-1")
