from datetime import datetime, timezone
from types import SimpleNamespace
from decimal import Decimal

from app.main import app
from app.models import CorporateMember, CorporateOrderRequest
from app.routes.corporate import next_recurring_run, slugify
from app.worker import build_woo_order_payload


def test_corporate_slug_and_recurring_calendar_are_deterministic():
    assert slugify("  Acme Kenya & East Africa! ") == "acme-kenya-east-africa"
    january_end = datetime(2027, 1, 31, 9, 30, tzinfo=timezone.utc)
    assert next_recurring_run(january_end, "monthly") == datetime(2027, 2, 28, 9, 30, tzinfo=timezone.utc)
    assert next_recurring_run(january_end, "weekly") == datetime(2027, 2, 7, 9, 30, tzinfo=timezone.utc)


def test_corporate_invoice_order_is_not_falsely_marked_paid_in_woocommerce():
    order = SimpleNamespace(
        delivery_address={"line1": "Westlands", "city": "Nairobi"},
        customer_name="Acme Kenya", customer_email="finance@acme.test", customer_phone="+254700000000",
        delivery_fee=Decimal("0"), fulfilment="delivery", delivery_slot="Friday 3 PM",
        reference="CC-CORPORATE",
    )
    line = SimpleNamespace(
        woo_product_id=42, quantity=10, line_total=Decimal("25000"),
        configuration={"size": "1kg"},
    )
    intent = SimpleNamespace(
        method="invoice", provider_reference="CCI-202701-001", provider_payload={},
    )
    payload = build_woo_order_payload(order, [line], intent)
    assert payload["payment_method"] == "invoice"
    assert payload["payment_method_title"] == "Corporate Invoice"
    assert payload["set_paid"] is False


def test_corporate_contracts_are_published():
    paths = app.openapi()["paths"]
    for path in (
        "/v1/corporate/me", "/v1/corporate/requests",
        "/v1/corporate/requests/{request_id}/approve",
        "/v1/corporate/invoices", "/v1/corporate/statements",
        "/v1/corporate/recurring", "/v1/corporate/admin/accounts",
        "/v1/corporate/admin/invoices/{invoice_id}/payments",
    ):
        assert path in paths
    assert CorporateOrderRequest.__table__.c.idempotency_key.unique
    assert CorporateMember.__table__.c.customer_id.unique
