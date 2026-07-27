from pathlib import Path

from migrate import MIGRATIONS, PACKAGED_MIGRATIONS, SOURCE_MIGRATIONS, source_migrations_for


def test_migration_runner_resolves_the_authoritative_schema() -> None:
    migrations = sorted(MIGRATIONS.glob("*.sql"))
    assert MIGRATIONS.name == "migrations"
    assert MIGRATIONS.parent.name == "database"
    assert MIGRATIONS == SOURCE_MIGRATIONS
    assert PACKAGED_MIGRATIONS.name == "migrations"
    assert [path.name for path in migrations] == [
        "001_catalog_sync.sql",
        "002_identity_checkout.sql",
        "003_payments_orders.sql",
        "004_tracking_notifications.sql",
        "005_loyalty_moments.sql",
        "006_admin_growth.sql",
        "007_fulfilment_operations.sql",
        "008_corporate_commerce.sql",
        "009_product_experience.sql",
        "010_intelligent_discovery.sql",
        "011_saved_celebrations.sql",
        "012_consumer_subscriptions.sql",
        "013_cart_recovery.sql",
    ]


def test_migration_runner_supports_a_shallow_container_path() -> None:
    assert source_migrations_for(Path("/app/migrate.py")).as_posix().endswith(
        "/app/database/migrations"
    )
