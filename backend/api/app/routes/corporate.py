import hashlib
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import current_customer, require_roles
from ..database import session
from ..models import (
    CorporateAccount, CorporateApproval, CorporateInvoice, CorporateInvoicePayment, CorporateMember,
    CorporateOrderRequest, CorporateRecurringOrder, Customer, Order, OrderLine,
    OutboxEvent, PaymentIntent, Product,
)
from ..services.audit import record_audit
from .checkout import calculate_unit_price

router = APIRouter(prefix="/v1/corporate", tags=["corporate"])
corporate_staff = require_roles("admin", "manager", "support")
corporate_admin = require_roles("admin", "manager")


class AccountInput(BaseModel):
    name: str = Field(min_length=2, max_length=240)
    billing_email: str = Field(min_length=5, max_length=320)
    phone: str | None = Field(default=None, max_length=32)
    tax_pin: str | None = Field(default=None, max_length=40)
    billing_address: dict = Field(default_factory=dict)
    credit_limit: Decimal = Field(ge=0, le=100_000_000)
    approval_threshold: Decimal = Field(default=0, ge=0, le=100_000_000)
    payment_terms_days: int = Field(default=30, ge=0, le=120)
    account_manager_id: UUID | None = None


class MemberInput(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    role: Literal["requester", "approver", "admin"] = "requester"
    spend_limit: Decimal | None = Field(default=None, ge=0, le=100_000_000)
    cost_center: str | None = Field(default=None, max_length=120)


class CorporateLineInput(BaseModel):
    product_slug: str = Field(min_length=1, max_length=220)
    quantity: int = Field(ge=1, le=500)
    size: Literal["1kg", "1.5kg", "2kg"] = "1kg"
    message: str = Field(default="", max_length=32)
    add_ons: list[Literal["candles", "greeting-card", "gift-wrap", "flowers"]] = Field(default_factory=list, max_length=4)


class CorporateAddressInput(BaseModel):
    line1: str = Field(min_length=3, max_length=260)
    area: str | None = Field(default=None, max_length=160)
    city: str = Field(default="Nairobi", max_length=120)
    notes: str | None = Field(default=None, max_length=500)


class CorporateRequestInput(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    purchase_order_number: str | None = Field(default=None, max_length=100)
    cost_center: str | None = Field(default=None, max_length=120)
    items: list[CorporateLineInput] = Field(min_length=1, max_length=100)
    fulfilment: Literal["delivery", "pickup"] = "delivery"
    delivery_slot: str | None = Field(default=None, max_length=80)
    delivery_address: CorporateAddressInput | None = None


class DecisionInput(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class RecurringInput(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    cadence: Literal["weekly", "monthly"]
    next_run_at: datetime
    order: CorporateRequestInput


class InvoicePaymentInput(BaseModel):
    amount: Decimal = Field(gt=0, le=100_000_000)
    reference: str = Field(min_length=2, max_length=180)


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:160]


async def membership(db: AsyncSession, customer_id: UUID, lock: bool = False) -> tuple[CorporateMember, CorporateAccount]:
    statement = select(CorporateMember).where(
        CorporateMember.customer_id == customer_id, CorporateMember.is_active.is_(True),
    )
    if lock:
        statement = statement.with_for_update()
    member = await db.scalar(statement)
    if not member:
        raise HTTPException(status_code=403, detail="A corporate account membership is required")
    account = await db.get(CorporateAccount, member.account_id)
    if not account or account.state != "active":
        raise HTTPException(status_code=403, detail="Corporate account is not active")
    return member, account


async def price_corporate(db: AsyncSession, payload: CorporateRequestInput) -> tuple[dict, Decimal, Decimal, Decimal]:
    if payload.fulfilment == "delivery" and not payload.delivery_address:
        raise HTTPException(status_code=422, detail="Delivery address is required")
    slugs = {item.product_slug for item in payload.items}
    products = {item.slug: item for item in (await db.scalars(select(Product).where(
        Product.slug.in_(slugs), Product.status == "publish",
    ))).all()}
    lines, subtotal = [], Decimal("0")
    for requested in payload.items:
        product = products.get(requested.product_slug)
        if not product or not product.in_stock:
            raise HTTPException(status_code=409, detail=f"{requested.product_slug} is unavailable")
        if product.stock_quantity is not None and product.stock_quantity < requested.quantity:
            raise HTTPException(status_code=409, detail=f"{product.name} has insufficient stock")
        unit = calculate_unit_price(Decimal(product.price_kes), requested.size, requested.add_ons)
        total = unit * requested.quantity
        subtotal += total
        lines.append({
            "product_id": str(product.id), "woo_product_id": product.woo_id,
            "product_slug": product.slug, "name": product.name, "quantity": requested.quantity,
            "unit_price": str(unit), "line_total": str(total),
            "configuration": {"size": requested.size, "message": requested.message, "add_ons": requested.add_ons},
        })
    delivery = Decimal("0") if payload.fulfilment == "pickup" or subtotal >= 5000 else Decimal("350")
    return {"currency": "KES", "lines": lines}, subtotal, delivery, subtotal + delivery


def request_read(item: CorporateOrderRequest) -> dict:
    return {
        "id": str(item.id), "reference": item.reference, "title": item.title,
        "purchase_order_number": item.purchase_order_number, "cost_center": item.cost_center,
        "state": item.state, "subtotal": f"{item.subtotal:.2f}",
        "delivery_fee": f"{item.delivery_fee:.2f}", "total": f"{item.total:.2f}",
        "fulfilment": item.fulfilment, "delivery_slot": item.delivery_slot,
        "quote": item.quote_snapshot, "submitted_at": item.submitted_at,
        "decided_at": item.decided_at, "order_id": str(item.order_id) if item.order_id else None,
        "rejection_reason": item.rejection_reason,
    }


async def make_request(
    db: AsyncSession, member: CorporateMember, payload: CorporateRequestInput,
    idempotency_key: str, recurring_id: UUID | None = None,
) -> CorporateOrderRequest:
    existing = await db.scalar(select(CorporateOrderRequest).where(
        CorporateOrderRequest.idempotency_key == idempotency_key,
    ))
    if existing:
        return existing
    snapshot, subtotal, delivery, total = await price_corporate(db, payload)
    item = CorporateOrderRequest(
        account_id=member.account_id, requester_id=member.customer_id,
        recurring_order_id=recurring_id, reference=f"CCR-{uuid4().hex[:10].upper()}",
        idempotency_key=idempotency_key, title=payload.title.strip(),
        purchase_order_number=payload.purchase_order_number, cost_center=payload.cost_center or member.cost_center,
        fulfilment=payload.fulfilment, delivery_slot=payload.delivery_slot,
        delivery_address=payload.delivery_address.model_dump() if payload.delivery_address else {}, quote_snapshot=snapshot,
        subtotal=subtotal, delivery_fee=delivery, total=total,
    )
    db.add(item)
    await db.flush()
    return item


@router.post("/admin/accounts", status_code=201)
async def create_account(payload: AccountInput, request: Request, actor: Customer = Depends(corporate_admin), db: AsyncSession = Depends(session)):
    slug = slugify(payload.name)
    if not slug or await db.scalar(select(CorporateAccount.id).where(CorporateAccount.slug == slug)):
        raise HTTPException(status_code=409, detail="A corporate account with this name already exists")
    if payload.account_manager_id:
        manager = await db.scalar(select(Customer).where(
            Customer.id == payload.account_manager_id, Customer.role.in_(("admin", "manager", "support")),
        ))
        if not manager:
            raise HTTPException(status_code=422, detail="Account manager must be an active staff member")
    values = payload.model_dump()
    if not values["account_manager_id"]:
        values["account_manager_id"] = actor.id
    account = CorporateAccount(slug=slug, **values)
    db.add(account)
    await db.flush()
    record_audit(db, actor, request, "corporate.account.created", "corporate_account", account.id, {
        "name": account.name, "credit_limit": str(account.credit_limit),
    })
    await db.commit()
    return {"id": str(account.id), "slug": account.slug}


@router.get("/admin/accounts")
async def admin_accounts(actor: Customer = Depends(corporate_staff), db: AsyncSession = Depends(session)):
    accounts = (await db.scalars(select(CorporateAccount).order_by(CorporateAccount.name))).all()
    rows = []
    for account in accounts:
        members = await db.scalar(select(func.count(CorporateMember.id)).where(
            CorporateMember.account_id == account.id, CorporateMember.is_active.is_(True),
        ))
        outstanding = await outstanding_credit(db, account.id)
        rows.append((account, members, outstanding))
    return [{"id": str(account.id), "name": account.name, "billing_email": account.billing_email,
             "credit_limit": f"{account.credit_limit:.2f}", "outstanding": f"{outstanding:.2f}",
             "payment_terms_days": account.payment_terms_days, "state": account.state,
             "members": members} for account, members, outstanding in rows]


@router.post("/admin/accounts/{account_id}/members", status_code=201)
async def add_member(account_id: UUID, payload: MemberInput, request: Request, actor: Customer = Depends(corporate_admin), db: AsyncSession = Depends(session)):
    account = await db.get(CorporateAccount, account_id)
    customer = await db.scalar(select(Customer).where(Customer.email == payload.email.strip().lower(), Customer.is_active.is_(True)))
    if not account or not customer:
        raise HTTPException(status_code=404, detail="Account or customer was not found")
    if await db.scalar(select(CorporateMember.id).where(
        CorporateMember.customer_id == customer.id,
    )):
        raise HTTPException(status_code=409, detail="Customer already belongs to a corporate account")
    item = CorporateMember(account_id=account.id, customer_id=customer.id, **payload.model_dump(exclude={"email"}))
    db.add(item)
    record_audit(db, actor, request, "corporate.member.added", "corporate_account", account.id, {
        "customer_id": str(customer.id), "role": item.role,
    })
    await db.commit()
    return {"id": str(item.id), "customer_id": str(customer.id), "role": item.role}


@router.get("/me")
async def corporate_home(customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    member, account = await membership(db, customer.id)
    outstanding = await db.scalar(select(func.coalesce(func.sum(CorporateInvoice.amount - CorporateInvoice.amount_paid), 0)).where(
        CorporateInvoice.account_id == account.id, CorporateInvoice.state.in_(("open", "part_paid", "overdue")),
    ))
    manager = await db.get(Customer, account.account_manager_id) if account.account_manager_id else None
    pending = await db.scalar(select(func.count(CorporateOrderRequest.id)).where(
        CorporateOrderRequest.account_id == account.id, CorporateOrderRequest.state == "pending_approval",
    ))
    return {
        "account": {"id": str(account.id), "name": account.name, "tax_pin": account.tax_pin,
                    "credit_limit": f"{account.credit_limit:.2f}", "outstanding": f"{outstanding:.2f}",
                    "available_credit": f"{max(Decimal('0'), account.credit_limit - Decimal(outstanding)):.2f}",
                    "payment_terms_days": account.payment_terms_days},
        "membership": {"role": member.role, "spend_limit": f"{member.spend_limit:.2f}" if member.spend_limit is not None else None,
                       "cost_center": member.cost_center},
        "account_manager": ({"name": f"{manager.first_name} {manager.last_name}".strip(),
                             "email": manager.email, "phone": manager.phone} if manager else None),
        "pending_approvals": pending if member.role in ("approver", "admin") else 0,
    }


@router.get("/requests")
async def requests(customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    member, _ = await membership(db, customer.id)
    query = select(CorporateOrderRequest).where(CorporateOrderRequest.account_id == member.account_id)
    if member.role == "requester":
        query = query.where(CorporateOrderRequest.requester_id == customer.id)
    items = (await db.scalars(query.order_by(CorporateOrderRequest.submitted_at.desc()).limit(200))).all()
    return [request_read(item) for item in items]


@router.post("/requests", status_code=201)
async def create_request(payload: CorporateRequestInput, request: Request, idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=16, max_length=180), customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    member, _ = await membership(db, customer.id)
    item = await make_request(db, member, payload, idempotency_key)
    record_audit(db, customer, request, "corporate.request.submitted", "corporate_order_request", item.id, {
        "total": str(item.total), "purchase_order_number": item.purchase_order_number,
    })
    await db.commit()
    return request_read(item)


async def outstanding_credit(db: AsyncSession, account_id: UUID) -> Decimal:
    value = await db.scalar(select(func.coalesce(func.sum(CorporateInvoice.amount - CorporateInvoice.amount_paid), 0)).where(
        CorporateInvoice.account_id == account_id, CorporateInvoice.state.in_(("open", "part_paid", "overdue")),
    ))
    return Decimal(value)


@router.post("/requests/{request_id}/approve", status_code=201)
async def approve(request_id: UUID, payload: DecisionInput, request: Request, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    member, account = await membership(db, customer.id)
    if member.role not in ("approver", "admin"):
        raise HTTPException(status_code=403, detail="Approver permission is required")
    account = await db.scalar(select(CorporateAccount).where(CorporateAccount.id == account.id).with_for_update())
    item = await db.scalar(select(CorporateOrderRequest).where(
        CorporateOrderRequest.id == request_id, CorporateOrderRequest.account_id == account.id,
    ).with_for_update())
    if not item or item.state != "pending_approval":
        raise HTTPException(status_code=409, detail="Request is not awaiting approval")
    requester_member = await db.scalar(select(CorporateMember).where(
        CorporateMember.account_id == account.id, CorporateMember.customer_id == item.requester_id,
    ))
    effective_limit = requester_member.spend_limit if requester_member and requester_member.spend_limit is not None else account.approval_threshold
    if effective_limit and item.total > effective_limit and member.role != "admin":
        raise HTTPException(status_code=403, detail="This request exceeds your corporate approval policy")
    if await outstanding_credit(db, account.id) + item.total > account.credit_limit:
        raise HTTPException(status_code=409, detail="Corporate credit limit would be exceeded")
    requester = await db.get(Customer, item.requester_id)
    order = Order(
        reference=f"CC-{uuid4().hex[:12].upper()}", customer_id=requester.id,
        customer_email=requester.email, customer_phone=requester.phone or account.phone or "",
        customer_name=f"{requester.first_name} {requester.last_name}".strip(),
        subtotal=item.subtotal, delivery_fee=item.delivery_fee, discount=0, total=item.total,
        fulfilment=item.fulfilment, delivery_slot=item.delivery_slot, delivery_address=item.delivery_address,
        state="paid",
    )
    db.add(order)
    await db.flush()
    for line in item.quote_snapshot["lines"]:
        db.add(OrderLine(
            order_id=order.id, product_id=UUID(line["product_id"]), woo_product_id=line["woo_product_id"],
            product_name=line["name"], quantity=line["quantity"], unit_price=Decimal(line["unit_price"]),
            line_total=Decimal(line["line_total"]), configuration=line["configuration"],
        ))
    invoice_number = f"CCI-{datetime.now(timezone.utc):%Y%m}-{uuid4().hex[:8].upper()}"
    invoice = CorporateInvoice(
        account_id=account.id, request_id=item.id, order_id=order.id,
        invoice_number=invoice_number, purchase_order_number=item.purchase_order_number,
        amount=item.total, due_at=datetime.now(timezone.utc) + timedelta(days=account.payment_terms_days),
    )
    db.add(invoice)
    intent = PaymentIntent(
        order_id=order.id, idempotency_key=f"corporate-invoice:{item.id}",
        client_secret_hash=hashlib.sha256(f"corporate:{item.id}".encode()).hexdigest(),
        method="invoice", provider="corporate_credit", provider_reference=invoice_number,
        amount=item.total, state="paid", paid_at=datetime.now(timezone.utc),
        provider_payload={"corporate_account_id": str(account.id), "purchase_order_number": item.purchase_order_number},
    )
    db.add(intent)
    await db.flush()
    db.add(OutboxEvent(
        aggregate_type="order", aggregate_id=order.id, topic="order.payment_confirmed",
        payload={"order_id": str(order.id), "payment_intent_id": str(intent.id)},
    ))
    item.order_id, item.state = order.id, "converted"
    item.decided_at = item.converted_at = datetime.now(timezone.utc)
    db.add(CorporateApproval(request_id=item.id, actor_id=customer.id, decision="approved", note=payload.note))
    record_audit(db, customer, request, "corporate.request.approved", "corporate_order_request", item.id, {
        "order_id": str(order.id), "invoice_number": invoice_number, "total": str(item.total),
    })
    await db.commit()
    return {"request": request_read(item), "order_reference": order.reference, "invoice_number": invoice_number}


@router.post("/requests/{request_id}/reject")
async def reject(request_id: UUID, payload: DecisionInput, request: Request, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    member, account = await membership(db, customer.id)
    if member.role not in ("approver", "admin"):
        raise HTTPException(status_code=403, detail="Approver permission is required")
    item = await db.scalar(select(CorporateOrderRequest).where(
        CorporateOrderRequest.id == request_id, CorporateOrderRequest.account_id == account.id,
    ).with_for_update())
    if not item or item.state != "pending_approval":
        raise HTTPException(status_code=409, detail="Request is not awaiting approval")
    if not payload.note:
        raise HTTPException(status_code=422, detail="A rejection reason is required")
    item.state, item.rejection_reason, item.decided_at = "rejected", payload.note, datetime.now(timezone.utc)
    db.add(CorporateApproval(request_id=item.id, actor_id=customer.id, decision="rejected", note=payload.note))
    record_audit(db, customer, request, "corporate.request.rejected", "corporate_order_request", item.id, {"reason": payload.note})
    await db.commit()
    return request_read(item)


@router.get("/invoices")
async def invoices(customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    member, _ = await membership(db, customer.id)
    items = (await db.scalars(select(CorporateInvoice).where(
        CorporateInvoice.account_id == member.account_id,
    ).order_by(CorporateInvoice.issued_at.desc()).limit(500))).all()
    now = datetime.now(timezone.utc)
    return [{"id": str(item.id), "invoice_number": item.invoice_number,
             "purchase_order_number": item.purchase_order_number, "amount": f"{item.amount:.2f}",
             "amount_paid": f"{item.amount_paid:.2f}",
             "state": "overdue" if item.state in ("open", "part_paid") and item.due_at < now else item.state,
             "issued_at": item.issued_at, "due_at": item.due_at} for item in items]


@router.get("/statements")
async def statements(customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    member, _ = await membership(db, customer.id)
    rows = (await db.execute(select(
        func.date_trunc("month", CorporateInvoice.issued_at),
        func.sum(CorporateInvoice.amount), func.sum(CorporateInvoice.amount_paid),
        func.count(CorporateInvoice.id),
    ).where(CorporateInvoice.account_id == member.account_id).group_by(
        func.date_trunc("month", CorporateInvoice.issued_at),
    ).order_by(func.date_trunc("month", CorporateInvoice.issued_at).desc()).limit(24))).all()
    return [{"month": month, "invoiced": f"{invoiced:.2f}", "paid": f"{paid:.2f}",
             "balance": f"{invoiced - paid:.2f}", "invoice_count": count}
            for month, invoiced, paid, count in rows]


@router.get("/recurring")
async def recurring_orders(customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    member, _ = await membership(db, customer.id)
    rows = (await db.scalars(select(CorporateRecurringOrder).where(
        CorporateRecurringOrder.account_id == member.account_id,
    ).order_by(CorporateRecurringOrder.created_at.desc()))).all()
    return [{"id": str(item.id), "name": item.name, "cadence": item.cadence,
             "next_run_at": item.next_run_at, "is_active": item.is_active,
             "last_run_at": item.last_run_at} for item in rows]


@router.post("/recurring", status_code=201)
async def create_recurring(payload: RecurringInput, request: Request, customer: Customer = Depends(current_customer), db: AsyncSession = Depends(session)):
    member, _ = await membership(db, customer.id)
    if payload.next_run_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="First run must be in the future")
    await price_corporate(db, payload.order)
    item = CorporateRecurringOrder(
        account_id=member.account_id, owner_id=customer.id, name=payload.name,
        cadence=payload.cadence, next_run_at=payload.next_run_at,
        order_payload=payload.order.model_dump(mode="json"),
    )
    db.add(item)
    await db.flush()
    record_audit(db, customer, request, "corporate.recurring.created", "corporate_recurring_order", item.id, {
        "cadence": item.cadence, "next_run_at": item.next_run_at.isoformat(),
    })
    await db.commit()
    return {"id": str(item.id), "next_run_at": item.next_run_at}


@router.post("/admin/invoices/{invoice_id}/payments")
async def record_invoice_payment(invoice_id: UUID, payload: InvoicePaymentInput, request: Request, actor: Customer = Depends(corporate_admin), db: AsyncSession = Depends(session)):
    invoice = await db.scalar(select(CorporateInvoice).where(CorporateInvoice.id == invoice_id).with_for_update())
    if not invoice or invoice.state in ("paid", "void"):
        raise HTTPException(status_code=409, detail="Invoice cannot receive this payment")
    balance = invoice.amount - invoice.amount_paid
    if payload.amount > balance:
        raise HTTPException(status_code=422, detail="Payment exceeds the invoice balance")
    if await db.scalar(select(CorporateInvoicePayment.id).where(CorporateInvoicePayment.reference == payload.reference)):
        raise HTTPException(status_code=409, detail="Payment reference has already been recorded")
    db.add(CorporateInvoicePayment(
        invoice_id=invoice.id, amount=payload.amount,
        reference=payload.reference.strip(), recorded_by=actor.id,
    ))
    invoice.amount_paid += payload.amount
    if invoice.amount_paid == invoice.amount:
        invoice.state, invoice.paid_at = "paid", datetime.now(timezone.utc)
    else:
        invoice.state = "part_paid"
    record_audit(db, actor, request, "corporate.invoice.payment_recorded", "corporate_invoice", invoice.id, {
        "amount": str(payload.amount), "reference": payload.reference,
        "balance": str(invoice.amount - invoice.amount_paid),
    })
    await db.commit()
    return {"invoice_number": invoice.invoice_number, "state": invoice.state,
            "amount_paid": f"{invoice.amount_paid:.2f}",
            "balance": f"{invoice.amount - invoice.amount_paid:.2f}"}


async def process_due_corporate_recurring(db: AsyncSession, now: datetime) -> int:
    rows = (await db.scalars(select(CorporateRecurringOrder).where(
        CorporateRecurringOrder.is_active.is_(True),
        CorporateRecurringOrder.next_run_at <= now,
    ).order_by(CorporateRecurringOrder.next_run_at).with_for_update(skip_locked=True).limit(100))).all()
    created = 0
    for recurring in rows:
        member = await db.scalar(select(CorporateMember).where(
            CorporateMember.account_id == recurring.account_id,
            CorporateMember.customer_id == recurring.owner_id,
            CorporateMember.is_active.is_(True),
        ))
        scheduled = recurring.next_run_at
        if not member:
            recurring.is_active = False
            continue
        payload = CorporateRequestInput.model_validate(recurring.order_payload)
        await make_request(
            db, member, payload,
            f"corporate-recurring:{recurring.id}:{scheduled.isoformat()}",
            recurring.id,
        )
        recurring.last_run_at = now
        recurring.next_run_at = next_recurring_run(scheduled, recurring.cadence)
        created += 1
    return created


def next_recurring_run(scheduled: datetime, cadence: str) -> datetime:
    if cadence == "weekly":
        return scheduled + timedelta(days=7)
    month = scheduled.month + 1
    year = scheduled.year + (1 if month == 13 else 0)
    month = 1 if month == 13 else month
    first = scheduled.replace(year=year, month=month, day=1)
    following_month = first.replace(
        year=year + (1 if month == 12 else 0), month=1 if month == 12 else month + 1,
    )
    max_day = (following_month - timedelta(days=1)).day
    return first.replace(day=min(scheduled.day, max_day))
