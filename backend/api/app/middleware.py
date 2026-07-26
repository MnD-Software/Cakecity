import hashlib
import secrets
import time

from fastapi import Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from .settings import settings

redis = Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)
AUTH_PREFIXES = ("/v1/auth/login", "/v1/auth/register", "/v1/auth/mobile/login", "/v1/auth/refresh", "/v1/auth/mobile/refresh")


def client_fingerprint(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    address = forwarded.split(",")[0].strip() if forwarded else request.client.host if request.client else "unknown"
    return hashlib.sha256(f"{address}:{request.url.path}".encode()).hexdigest()[:32]


def limit_for(path: str) -> int:
    return settings.auth_rate_limit_per_minute if path.startswith(AUTH_PREFIXES) else settings.rate_limit_per_minute


async def platform_guard(request: Request, call_next):
    request_id = request.headers.get("x-request-id", "")[:100] or secrets.token_hex(12)
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > settings.max_request_bytes:
                return JSONResponse(
                    status_code=413, content={"detail": "Request body is too large"},
                    headers={"X-Request-ID": request_id},
                )
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})

    limit = limit_for(request.url.path)
    remaining = limit
    rate_status = "active"
    if request.url.path not in ("/health", "/ready"):
        bucket = int(time.time() // 60)
        key = f"ratelimit:{bucket}:{client_fingerprint(request)}"
        try:
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, 70)
            remaining = max(0, limit - count)
            if count > limit:
                retry = 60 - int(time.time() % 60)
                return JSONResponse(
                    status_code=429, content={"detail": "Too many requests; please try again shortly"},
                    headers={
                        "Retry-After": str(retry), "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0", "X-Request-ID": request_id,
                    },
                )
        except Exception:
            # Availability wins during an isolated cache outage; readiness exposes degradation.
            rate_status = "degraded"

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Status"] = rate_status
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith(("/v1/auth", "/v1/account", "/v1/admin", "/v1/corporate", "/v1/driver", "/v1/kitchen")) else response.headers.get("Cache-Control", "private, max-age=0")
    return response
