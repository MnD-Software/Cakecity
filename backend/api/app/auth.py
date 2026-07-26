import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .database import session
from .models import Customer
from .settings import settings

bearer = HTTPBearer(auto_error=False)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def hash_password(password: str, salt: bytes | None = None) -> str:
    if len(password) < 10:
        raise ValueError("Password must be at least 10 characters")
    salt = salt or os.urandom(16)
    derived = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt$16384$8$1${_b64(salt)}${_b64(derived)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$")
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(password.encode(), salt=_unb64(salt), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(actual, _unb64(expected))
    except (ValueError, TypeError):
        return False


def create_access_token(customer_id: UUID, role: str, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64(json.dumps({
        "sub": str(customer_id), "role": role, "type": "access",
        "iat": int(now.timestamp()), "exp": int((now + timedelta(minutes=settings.access_token_minutes)).timestamp()),
        "jti": secrets.token_hex(12),
    }, separators=(",", ":")).encode())
    signature = _b64(hmac.new(settings.jwt_secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def decode_access_token(token: str, now: datetime | None = None) -> dict:
    try:
        header, payload, signature = token.split(".")
        token_header = json.loads(_unb64(header))
        if token_header != {"alg": "HS256", "typ": "JWT"}:
            raise ValueError("Unsupported token header")
        expected = _b64(hmac.new(settings.jwt_secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, signature):
            raise ValueError("Signature mismatch")
        claims = json.loads(_unb64(payload))
        current = int((now or datetime.now(timezone.utc)).timestamp())
        if claims.get("type") != "access" or int(claims.get("exp", 0)) <= current:
            raise ValueError("Token expired")
        UUID(claims["sub"])
        return claims
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token") from exc


def new_refresh_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(48)
    return token, hashlib.sha256(token.encode()).hexdigest()


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def current_customer(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(session),
) -> Customer:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    claims = decode_access_token(credentials.credentials)
    customer = await db.scalar(select(Customer).where(Customer.id == UUID(claims["sub"]), Customer.is_active.is_(True)))
    if not customer:
        raise HTTPException(status_code=401, detail="Customer session is no longer active")
    return customer


def require_roles(*allowed_roles: str):
    async def dependency(customer: Customer = Depends(current_customer)) -> Customer:
        if customer.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="You do not have permission to access this resource")
        return customer
    return dependency


async def optional_customer(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(session),
) -> Customer | None:
    if not credentials:
        return None
    claims = decode_access_token(credentials.credentials)
    return await db.scalar(select(Customer).where(
        Customer.id == UUID(claims["sub"]), Customer.is_active.is_(True)
    ))


def request_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    return (forwarded.split(",")[0].strip() if forwarded else request.client.host if request.client else None)
