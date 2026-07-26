from decimal import Decimal
from types import SimpleNamespace
from app.worker import build_woo_order_payload


def test_paid_order_payload_preserves_authority_reference_and_configuration():
    order = SimpleNamespace(
        reference="CC-ABC123", customer_name="Amani", customer_email="a@example.com",
        customer_phone="0712345678", delivery_address={"line1": "12 Rose Lane", "city": "Nairobi"},
        delivery_fee=Decimal("350"), fulfilment="delivery", delivery_slot="3:30-4:00 PM",
    )
    line = SimpleNamespace(
        woo_product_id=901, quantity=2, line_total=Decimal("8200.00"),
        configuration={"size": "1.5kg", "message": "Happy birthday"},
    )
    intent = SimpleNamespace(
        method="mpesa", provider_reference="ws_CO_1",
        provider_payload={"callback": {"receipt": "SAMPLE123"}},
    )
    payload = build_woo_order_payload(order, [line], intent)
    assert payload["set_paid"] is True
    assert payload["transaction_id"] == "SAMPLE123"
    assert payload["line_items"][0]["product_id"] == 901
    assert {"key": "_cakecity_reference", "value": "CC-ABC123"} in payload["meta_data"]


def test_wallet_orders_are_identified_in_woocommerce():
    order = SimpleNamespace(
        reference="CC-WALLET", customer_name="Amani", customer_email="a@example.com",
        customer_phone="0712345678", delivery_address={}, delivery_fee=Decimal("0"),
        fulfilment="pickup", delivery_slot=None,
    )
    line = SimpleNamespace(woo_product_id=1, quantity=1, line_total=Decimal("3200"), configuration={})
    intent = SimpleNamespace(method="wallet", provider_reference="WALLET-CC-WALLET", provider_payload={})
    payload = build_woo_order_payload(order, [line], intent)
    assert payload["payment_method_title"] == "Cake City Wallet"
