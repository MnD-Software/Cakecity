from app.settings import Settings
import pytest


def test_render_postgres_url_uses_async_driver():
    settings = Settings(database_url="postgresql://user:pass@host:5432/cakecity")
    assert settings.database_url.startswith("postgresql+asyncpg://")


def test_production_rejects_default_jwt_secret():
    with pytest.raises(RuntimeError):
        Settings(environment="production").validate_production_secrets()


def test_production_accepts_complete_managed_boundary():
    settings = Settings(
        environment="production",
        database_url="postgresql://cakecity:secret@db.internal:5432/cakecity",
        redis_url="rediss://cache.internal:6379/0",
        jwt_secret="a-strong-production-secret-with-entropy-12345",
        woocommerce_url="https://shop.cakecity.co.ke",
        woocommerce_consumer_key="ck_test",
        woocommerce_consumer_secret="cs_test",
        woocommerce_webhook_secret="webhook-secret",
        secure_cookies=True,
        cookie_samesite="none",
        allowed_origins=["https://app.cakecity.co.ke"],
    )
    settings.validate_production_secrets()
