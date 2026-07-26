from app.services.order_tracking import STAGES, stage_from_woo, woo_meta


def test_tracking_stages_cover_kitchen_and_delivery_journey():
    assert STAGES[0] == "received"
    assert "baking" in STAGES
    assert "quality_check" in STAGES
    assert STAGES[-1] == "delivered"


def test_explicit_woocommerce_stage_takes_precedence():
    payload = {"status": "processing", "meta_data": [{"key": "_cakecity_stage", "value": "decorating"}]}
    assert woo_meta(payload, "_cakecity_stage") == "decorating"
    assert stage_from_woo(payload) == "decorating"


def test_standard_woocommerce_status_maps_to_customer_stage():
    assert stage_from_woo({"status": "processing"}) == "confirmed"
    assert stage_from_woo({"status": "completed"}) == "delivered"
    assert stage_from_woo({"status": "cancelled"}) is None
