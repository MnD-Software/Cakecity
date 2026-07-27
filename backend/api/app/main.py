from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import text

from .routes.catalog import router as catalog_router
from .routes.webhooks import router as webhook_router
from .routes.auth import router as auth_router
from .routes.addresses import router as addresses_router
from .routes.carts import router as carts_router
from .routes.checkout import router as checkout_router
from .routes.payments import router as payments_router
from .routes.orders import router as orders_router
from .routes.notifications import router as notifications_router
from .routes.rewards import router as rewards_router
from .routes.moments import router as moments_router
from .routes.admin import router as admin_router
from .routes.kitchen import router as kitchen_router
from .routes.driver import router as driver_router
from .routes.corporate import router as corporate_router
from .routes.discovery import router as discovery_router
from .routes.saved import router as saved_router
from .routes.subscriptions import router as subscriptions_router
from .settings import settings
from .database import engine
from .middleware import platform_guard, redis as rate_limit_redis


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Database migrations run as a deployment step, never implicitly at request time.
    settings.validate_production_secrets()
    yield


app = FastAPI(
    title="Cake City Platform API",
    version="1.5.4",
    docs_url="/docs" if settings.environment != "production" else None,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "Idempotency-Key", "X-Payment-Secret", "X-WC-Webhook-Signature", "X-WC-Webhook-ID",
                   "X-WC-Webhook-Topic", "X-WC-Webhook-Resource", "X-Request-ID",
                   "X-Discovery-Session"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.middleware("http")(platform_guard)
app.include_router(catalog_router)
app.include_router(webhook_router)
app.include_router(auth_router)
app.include_router(addresses_router)
app.include_router(carts_router)
app.include_router(checkout_router)
app.include_router(payments_router)
app.include_router(orders_router)
app.include_router(notifications_router)
app.include_router(rewards_router)
app.include_router(moments_router)
app.include_router(admin_router)
app.include_router(kitchen_router)
app.include_router(driver_router)
app.include_router(corporate_router)
app.include_router(discovery_router)
app.include_router(saved_router)
app.include_router(subscriptions_router)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "service": "cakecity-api", "version": app.version}


@app.get("/ready", tags=["system"])
async def ready():
    checks = {"database": False, "redis": False}
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        pass
    try:
        checks["redis"] = bool(await rate_limit_redis.ping())
    except Exception:
        pass
    status = "ready" if all(checks.values()) else "degraded"
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=200 if status == "ready" else 503,
        content={"status": status, "service": "cakecity-api", "version": app.version, "checks": checks},
    )
