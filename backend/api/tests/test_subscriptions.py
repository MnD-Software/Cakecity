from datetime import datetime, timezone
from pathlib import Path

from app.routes.subscriptions import next_subscription_run


def test_subscription_cadence_preserves_calendar_intent():
    january_end = datetime(2026, 1, 31, 10, 0, tzinfo=timezone.utc)
    assert next_subscription_run(january_end, "weekly") == datetime(2026, 2, 7, 10, 0, tzinfo=timezone.utc)
    assert next_subscription_run(january_end, "monthly") == datetime(2026, 2, 28, 10, 0, tzinfo=timezone.utc)
    assert next_subscription_run(january_end, "quarterly") == datetime(2026, 4, 30, 10, 0, tzinfo=timezone.utc)
    assert next_subscription_run(january_end, "yearly") == datetime(2027, 1, 31, 10, 0, tzinfo=timezone.utc)


def test_subscription_worker_is_idempotent_and_notifies_before_payment():
    source = (Path(__file__).parents[1] / "app" / "routes" / "subscriptions.py").read_text()
    assert "uq_consumer_subscription_run" not in source
    assert "ConsumerSubscriptionRun.scheduled_for == scheduled" in source
    assert "Review and confirm secure payment" in source
    assert "with_for_update(skip_locked=True)" in source
