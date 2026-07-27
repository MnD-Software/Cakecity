from app.settings import Settings
import pytest
from sqlalchemy.engine import make_url


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


def test_render_accepts_json_or_plain_origin_lists(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://one.vercel.app, https://two.vercel.app")
    monkeypatch.setenv("ALLOWED_HOSTS", '["cakecity-api.onrender.com"]')
    settings = Settings(_env_file=None)
    assert settings.allowed_origins == [
        "https://one.vercel.app",
        "https://two.vercel.app",
    ]
    assert settings.allowed_hosts == ["cakecity-api.onrender.com"]


def test_neon_ssl_query_can_be_removed_for_asyncpg():
    url = make_url(
        "postgresql+asyncpg://user:pass@ep-example.neon.tech/db"
        "?sslmode=require&channel_binding=require"
    )
    normalized = url.difference_update_query(["sslmode", "channel_binding"])
    assert "sslmode" not in normalized.query
    assert "channel_binding" not in normalized.query
