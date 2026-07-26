from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    woo_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(220), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(260), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    price_kes: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    regular_price_kes: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    stock_quantity: Mapped[int | None] = mapped_column(Integer)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="publish", nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text)
    source_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    synchronized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        Index("ix_products_browse", "status", "in_stock"),
        Index("ix_products_name", "name"),
    )


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    webhook_id: Mapped[str] = mapped_column(String(160), nullable=False)
    delivery_key: Mapped[str] = mapped_column(String(190), nullable=False)
    topic: Mapped[str] = mapped_column(String(80), nullable=False)
    resource: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(24), default="received", nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("delivery_key", name="uq_webhook_delivery_key"),
        Index("ix_webhook_processing", "state", "received_at"),
    )


class SyncCheckpoint(Base):
    __tablename__ = "sync_checkpoints"
    resource: Mapped[str] = mapped_column(String(80), primary_key=True)
    cursor: Mapped[str | None] = mapped_column(String(260))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
