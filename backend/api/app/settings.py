from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://cakecity:local-only@localhost:5432/cakecity"
    redis_url: str = "redis://localhost:6379/0"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    woocommerce_webhook_secret: str = "local-development-only"
    jwt_secret: str = "local-development-access-secret-change-me"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    secure_cookies: bool = False
    cookie_domain: str | None = None
    allowed_origins: list[str] = ["http://localhost:3000"]
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url", mode="before")
    @classmethod
    def async_postgres_driver(cls, value: str) -> str:
        # Managed providers expose postgresql://; SQLAlchemy async requires the driver.
        return value.replace("postgresql://", "postgresql+asyncpg://", 1)

    def validate_production_secrets(self) -> None:
        if self.environment == "production" and (
            len(self.jwt_secret) < 32 or self.jwt_secret.startswith("local-development")
        ):
            raise RuntimeError("JWT_SECRET must be a strong production secret")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
