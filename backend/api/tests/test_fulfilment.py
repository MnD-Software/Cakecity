from types import SimpleNamespace
from uuid import uuid4

from app.main import app
from app.services.fulfilment import NEXT_STAGE, hash_delivery_otp, verify_delivery_otp


def test_fulfilment_stage_machine_is_strict_and_complete():
    assert list(NEXT_STAGE.items())[-3:] == [
        ("packaging", "driver_assigned"),
        ("driver_assigned", "out_for_delivery"),
        ("out_for_delivery", "delivered"),
    ]


def test_delivery_otp_is_hashed_and_verified():
    assignment = SimpleNamespace(id=uuid4())
    assignment.delivery_otp_hash = hash_delivery_otp(assignment.id, "418209")
    assert assignment.delivery_otp_hash != "418209"
    assert verify_delivery_otp(assignment, "418209")
    assert not verify_delivery_otp(assignment, "418208")


def test_operational_routes_are_published():
    paths = app.openapi()["paths"]
    assert "/v1/kitchen/queue" in paths
    assert "/v1/driver/dispatch/overview" in paths
    assert "/v1/driver/assignments/{assignment_id}/proof" in paths
    assert "/v1/auth/mobile/refresh" in paths
