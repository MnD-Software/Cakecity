from app.settings import Settings
import pytest


def test_render_postgres_url_uses_async_driver():
    settings = Settings(database_url="postgresql://user:pass@host:5432/cakecity")
    assert settings.database_url.startswith("postgresql+asyncpg://")


def test_production_rejects_default_jwt_secret():
    with pytest.raises(RuntimeError):
        Settings(environment="production").validate_production_secrets()
