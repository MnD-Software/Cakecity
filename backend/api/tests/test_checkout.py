from decimal import Decimal
from app.routes.checkout import calculate_unit_price


def test_configuration_price_is_server_calculated():
    assert calculate_unit_price(Decimal("3200"), "1.5kg", ["candles", "gift-wrap"]) == Decimal("4650")


def test_duplicate_add_on_is_charged_once():
    assert calculate_unit_price(Decimal("3200"), "1kg", ["candles", "candles"]) == Decimal("3450")
