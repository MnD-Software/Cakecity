from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from ..auth import (
    create_access_token, current_customer, hash_password, hash_refresh_token,
    new_refresh_token, request_ip, verify_password,
)
from ..database import session
from ..models import Customer, RefreshSession
from ..settings import settings

router = APIRouter(prefix="/v1/auth", tags=["identity"])
COOKIE = "cakecity_refresh"


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=10, max_length=128)
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(default="", max_length=120)
    phone: str | None = Field(default=None, max_length=32)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if value.count("@") != 1 or "." not in value.split("@")[1]:
            raise ValueError("Enter a valid email address")
        return value


class LoginRequest(BaseModel):
    email: str
    password: str


class CustomerRead(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    phone: str | None
    role: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    customer: CustomerRead


def customer_read(customer: Customer) -> CustomerRead:
    return CustomerRead.model_validate(customer, from_attributes=True)


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE, token, max_age=settings.refresh_token_days * 86400,
        httponly=True, secure=settings.secure_cookies, samesite="lax",
        domain=settings.cookie_domain, path="/v1/auth",
    )


async def issue_session(customer: Customer, request: Request, response: Response, db: AsyncSession, family_id: UUID | None = None) -> AuthResponse:
    refresh, token_hash = new_refresh_token()
    db.add(RefreshSession(
        customer_id=customer.id, family_id=family_id or uuid4(), token_hash=token_hash,
        user_agent=request.headers.get("user-agent", "")[:500], ip_address=request_ip(request),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days),
    ))
    await db.commit()
    set_refresh_cookie(response, refresh)
    return AuthResponse(
        access_token=create_access_token(customer.id, customer.role),
        expires_in=settings.access_token_minutes * 60, customer=customer_read(customer),
    )


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(payload: RegisterRequest, request: Request, response: Response, db: AsyncSession = Depends(session)):
    if await db.scalar(select(Customer.id).where(Customer.email == payload.email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    customer = Customer(
        email=payload.email, password_hash=hash_password(payload.password),
        first_name=payload.first_name.strip(), last_name=payload.last_name.strip(), phone=payload.phone,
    )
    db.add(customer)
    await db.flush()
    return await issue_session(customer, request, response, db)


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(session)):
    customer = await db.scalar(select(Customer).where(Customer.email == payload.email.strip().lower()))
    if not customer or not customer.is_active or not verify_password(payload.password, customer.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    return await issue_session(customer, request, response, db)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(session)):
    raw = request.cookies.get(COOKIE)
    if not raw:
        raise HTTPException(status_code=401, detail="Refresh session missing")
    token_hash = hash_refresh_token(raw)
    active = await db.scalar(select(RefreshSession).where(RefreshSession.token_hash == token_hash).with_for_update())
    if not active:
        raise HTTPException(status_code=401, detail="Refresh session is invalid")
    if active.revoked_at is not None:
        # Reuse of a rotated token signals possible theft; revoke the entire token family.
        await db.execute(update(RefreshSession).where(
            RefreshSession.family_id == active.family_id, RefreshSession.revoked_at.is_(None)
        ).values(revoked_at=datetime.now(timezone.utc)))
        await db.commit()
        raise HTTPException(status_code=401, detail="Refresh token reuse detected; session family revoked")
    if active.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh session expired")
    customer = await db.scalar(select(Customer).where(Customer.id == active.customer_id, Customer.is_active.is_(True)))
    if not customer:
        raise HTTPException(status_code=401, detail="Customer session is no longer active")
    active.revoked_at = datetime.now(timezone.utc)
    active.last_used_at = active.revoked_at
    return await issue_session(customer, request, response, db, active.family_id)


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response, db: AsyncSession = Depends(session)):
    raw = request.cookies.get(COOKIE)
    if raw:
        await db.execute(update(RefreshSession).where(
            RefreshSession.token_hash == hash_refresh_token(raw), RefreshSession.revoked_at.is_(None)
        ).values(revoked_at=datetime.now(timezone.utc)))
        await db.commit()
    response.delete_cookie(COOKIE, domain=settings.cookie_domain, path="/v1/auth")


@router.get("/me", response_model=CustomerRead)
async def me(customer: Customer = Depends(current_customer)):
    return customer_read(customer)
