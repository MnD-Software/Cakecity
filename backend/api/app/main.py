from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.catalog import router as catalog_router
from .routes.webhooks import router as webhook_router
from .routes.auth import router as auth_router
from .routes.addresses import router as addresses_router
from .routes.carts import router as carts_router
from .routes.checkout import router as checkout_router
from .settings import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Database migrations run as a deployment step, never implicitly at request time.
    settings.validate_production_secrets()
    yield


app = FastAPI(
    title="Cake City Platform API",
    version="0.3.0",
    docs_url="/docs" if settings.environment != "production" else None,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "Idempotency-Key", "X-WC-Webhook-Signature", "X-WC-Webhook-ID",
                   "X-WC-Webhook-Topic", "X-WC-Webhook-Resource"],
)
app.include_router(catalog_router)
app.include_router(webhook_router)
app.include_router(auth_router)
app.include_router(addresses_router)
app.include_router(carts_router)
app.include_router(checkout_router)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "service": "cakecity-api", "version": app.version}
