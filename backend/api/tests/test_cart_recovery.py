from pathlib import Path

from app.routes.carts import safe_configuration


def test_cart_configuration_is_bounded_and_canonical():
    first, first_hash = safe_configuration({
        "size": "1.5kg", "message": "  Happy birthday  ",
        "add_ons": ["flowers", "candles", "flowers", "invalid"],
    })
    second, second_hash = safe_configuration({
        "addOns": ["candles", "flowers"], "message": "Happy birthday", "size": "1.5kg",
    })
    assert first == second == {
        "size": "1.5kg", "message": "Happy birthday", "add_ons": ["candles", "flowers"],
    }
    assert first_hash == second_hash


def test_recovery_worker_has_inactivity_checkout_and_idempotency_guards():
    source = (Path(__file__).parents[1] / "app" / "routes" / "carts.py").read_text()
    assert "now - timedelta(hours=2)" in source
    assert "now - timedelta(hours=24)" in source
    assert "Cart.recovery_sent_at.is_(None)" in source
    assert "with_for_update(skip_locked=True)" in source
    assert '"url": "/checkout?recovered=1"' in source
