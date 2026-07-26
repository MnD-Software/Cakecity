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
    cookie_samesite: str = "lax"
    cookie_domain: str | None = None
    public_api_url: str = "http://127.0.0.1:8000"
    storefront_url: str = "http://localhost:3000"
    mpesa_base_url: str = "https://sandbox.safaricom.co.ke"
    mpesa_consumer_key: str = ""
    mpesa_consumer_secret: str = ""
    mpesa_shortcode: str = ""
    mpesa_passkey: str = ""
    mpesa_callback_secret: str = ""
    flutterwave_base_url: str = "https://api.flutterwave.com"
    flutterwave_secret_key: str = ""
    flutterwave_webhook_secret: str = ""
    woocommerce_url: str = ""
    woocommerce_consumer_key: str = ""
    woocommerce_consumer_secret: str = ""
    brevo_api_key: str = ""
    brevo_sender_email: str = ""
    brevo_sender_name: str = "Cake City"
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:hello@cakecity.co.ke"
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url", mode="before")
    @classmethod
    def async_postgres_driver(cls, value: str) -> str:
        # Managed providers expose postgresql://; SQLAlchemy async requires the driver.
        return value.replace("postgresql://", "postgresql+asyncpg://", 1)

    @field_validator("cookie_samesite")
    @classmethod
    def valid_cookie_samesite(cls, value: str) -> str:
        value = value.lower()
        if value not in {"lax", "strict", "none"}:
            raise ValueError("COOKIE_SAMESITE must be lax, strict or none")
        return value

    def validate_production_secrets(self) -> None:
        if self.environment == "production" and (
            len(self.jwt_secret) < 32 or self.jwt_secret.startswith("local-development")
        ):
            raise RuntimeError("JWT_SECRET must be a strong production secret")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
