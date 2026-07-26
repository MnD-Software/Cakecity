from decimal import Decimal
import pytest
from app.services.product_sync import map_woo_product, money


def test_maps_woocommerce_product_into_browse_model():
    result = map_woo_product({
        "id": 901, "slug": "red-velvet", "name": "Red Velvet", "price": "3200",
        "regular_price": "3500", "stock_status": "instock", "stock_quantity": 8,
        "status": "publish", "images": [{"src": "https://cdn.example/cake.webp"}],
        "categories": [{"name": "Birthday Cakes"}],
        "average_rating": "4.8", "rating_count": 24,
        "upsell_ids": [902], "cross_sell_ids": [903],
        "attributes": [{"name": "Flavour", "options": ["Vanilla", "Chocolate"]}],
        "meta_data": [
            {"key": "_cakecity_allergens", "value": '["Milk","Gluten"]'},
            {"key": "_cakecity_nutrition", "value": '{"serving":"100g","energy":"380 kcal"}'},
            {"key": "_cakecity_preparation_minutes", "value": "240"},
            {"key": "_cakecity_video_url", "value": "https://cdn.example/cake.mp4"},
        ],
    })
    assert result["woo_id"] == 901
    assert result["price_kes"] == Decimal("3200.00")
    assert result["in_stock"] is True
    assert result["image_url"].endswith("cake.webp")
    assert result["gallery"][0]["alt"] == "Red Velvet"
    assert result["categories"] == ["Birthday Cakes"]
    assert result["attributes"][0]["options"] == ["Vanilla", "Chocolate"]
    assert result["allergens"] == ["Milk", "Gluten"]
    assert result["nutrition"]["energy"] == "380 kcal"
    assert result["preparation_minutes"] == 240
    assert result["average_rating"] == Decimal("4.80")


def test_rejects_incomplete_product():
    with pytest.raises(ValueError):
        map_woo_product({"id": 1})


def test_rejects_negative_price():
    with pytest.raises(ValueError):
        money("-1")
