from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.catalog import router as catalog_router
from .routes.webhooks import router as webhook_router
from .settings import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Database migrations run as a deployment step, never implicitly at request time.
    yield


app = FastAPI(
    title="Cake City Platform API",
    version="0.2.0",
    docs_url="/docs" if settings.environment != "production" else None,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-WC-Webhook-Signature", "X-WC-Webhook-ID",
                   "X-WC-Webhook-Topic", "X-WC-Webhook-Resource"],
)
app.include_router(catalog_router)
app.include_router(webhook_router)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "service": "cakecity-api", "version": app.version}
