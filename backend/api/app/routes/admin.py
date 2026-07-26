from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from ..auth import require_roles
from ..database import session
from ..models import (
    AuditEvent, CampaignDelivery, CRMActivity, CRMLead, CRMTask, Customer,
    LoyaltyAccount, LoyaltyLedgerEntry, MarketingCampaign, Order, Referral,
)
from ..services.audit import record_audit
from ..services.segments import SEGMENTS, customer_ids_for_segment

router = APIRouter(prefix="/v1/admin", tags=["admin"])
staff = require_roles("admin", "manager", "marketing", "support")
growth_staff = require_roles("admin", "manager", "marketing")
crm_staff = require_roles("admin", "manager", "marketing", "support")
REVENUE_STATES = ("paid", "received", "confirmed", "baking", "decorating", "quality_check", "packaging", "driver_assigned", "out_for_delivery", "delivered")
LEAD_STAGES = ("new", "contacted", "qualified", "proposal", "won", "lost")


class LeadInput(BaseModel):
    name: str = Field(min_length=2, max_length=240)
    email: str = Field(min_length=5, max_length=320)
    phone: str | None = Field(default=None, max_length=32)
    source: str = Field(default="manual", min_length=2, max_length=60)
    estimated_value: Decimal = Field(default=0, ge=0, le=10_000_000)
    owner_id: UUID | None = None
    next_action_at: datetime | None = None


class LeadStageInput(BaseModel):
    stage: str = Field(pattern="^(new|contacted|qualified|proposal|won|lost)$")
    note: str = Field(min_length=2, max_length=500)


class ActivityInput(BaseModel):
    activity_type: str = Field(pattern="^(note|call|email|whatsapp|meeting)$")
    summary: str = Field(min_length=2, max_length=500)


class TaskInput(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    due_at: datetime
    assignee_id: UUID | None = None


class CampaignInput(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    channel: str = Field(pattern="^(in_app|email|push)$")
    audience_segment: str = Field(pattern="^(all|new|repeat|vip|lapsed|birthday_upcoming)$")
    subject: str = Field(min_length=2, max_length=180)
    message: str = Field(min_length=2, max_length=1000)
    call_to_action_url: str = Field(default="/", min_length=1, max_length=500)


class ScheduleInput(BaseModel):
    scheduled_at: datetime


def lead_read(lead: CRMLead) -> dict:
    return {
        "id": str(lead.id), "customer_id": str(lead.customer_id) if lead.customer_id else None,
        "name": lead.name, "email": lead.email, "phone": lead.phone, "source": lead.source,
        "stage": lead.stage, "estimated_value": f"{lead.estimated_value:.2f}",
        "owner_id": str(lead.owner_id) if lead.owner_id else None,
        "next_action_at": lead.next_action_at, "created_at": lead.created_at,
    }


def campaign_read(item: MarketingCampaign, total: int = 0, sent: int = 0) -> dict:
    return {
        "id": str(item.id), "name": item.name, "channel": item.channel,
        "audience_segment": item.audience_segment, "subject": item.subject,
        "message": item.message, "call_to_action_url": item.call_to_action_url,
        "state": item.state, "scheduled_at": item.scheduled_at, "launched_at": item.launched_at,
        "created_at": item.created_at, "audience_count": total, "delivered_count": sent,
    }


@router.get("/overview")
async def overview(_: Customer = Depends(staff), db: AsyncSession = Depends(session)):
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=30)
    previous = since - timedelta(days=30)
    current_revenue = await db.scalar(select(func.coalesce(func.sum(Order.total), 0)).where(
        Order.state.in_(REVENUE_STATES), Order.created_at >= since,
    ))
    previous_revenue = await db.scalar(select(func.coalesce(func.sum(Order.total), 0)).where(
        Order.state.in_(REVENUE_STATES), Order.created_at >= previous, Order.created_at < since,
    ))
    order_count = await db.scalar(select(func.count(Order.id)).where(
        Order.state.in_(REVENUE_STATES), Order.created_at >= since,
    ))
    customers = await db.scalar(select(func.count(Customer.id)).where(Customer.role == "customer", Customer.is_active.is_(True)))
    customer_orders = (await db.execute(select(
        Order.customer_id, func.count(Order.id),
    ).where(
        Order.customer_id.is_not(None), Order.state.in_(REVENUE_STATES),
    ).group_by(Order.customer_id))).all()
    repeat_customers = sum(1 for _, count in customer_orders if count >= 2)
    referral_count = await db.scalar(select(func.count(Referral.id)).where(Referral.state == "completed"))
    pipeline_value = await db.scalar(select(func.coalesce(func.sum(CRMLead.estimated_value), 0)).where(
        CRMLead.stage.not_in(("won", "lost")),
    ))
    revenue_change = ((Decimal(current_revenue) - Decimal(previous_revenue)) / Decimal(previous_revenue) * 100) if previous_revenue else Decimal("0")
    return {
        "revenue_30d": f"{current_revenue:.2f}", "revenue_change_percent": f"{revenue_change:.1f}",
        "orders_30d": order_count, "average_order_value": f"{(Decimal(current_revenue) / order_count if order_count else 0):.2f}",
        "customers": customers, "repeat_purchase_rate": round(repeat_customers / len(customer_orders) * 100, 1) if customer_orders else 0,
        "completed_referrals": referral_count, "open_pipeline_value": f"{pipeline_value:.2f}",
    }


@router.get("/analytics/revenue")
async def revenue_series(
    days: int = Query(default=30, ge=7, le=365),
    _: Customer = Depends(staff), db: AsyncSession = Depends(session),
):
    start = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (await db.execute(select(
        func.date(Order.created_at).label("day"), func.sum(Order.total), func.count(Order.id),
    ).where(
        Order.state.in_(REVENUE_STATES), Order.created_at >= start,
    ).group_by(func.date(Order.created_at)).order_by(func.date(Order.created_at)))).all()
    return [{"date": day, "revenue": f"{revenue:.2f}", "orders": orders} for day, revenue, orders in rows]


@router.get("/analytics/products")
async def product_performance(_: Customer = Depends(staff), db: AsyncSession = Depends(session)):
    from ..models import OrderLine
    rows = (await db.execute(select(
        OrderLine.product_name, func.sum(OrderLine.quantity), func.sum(OrderLine.line_total),
    ).join(Order, Order.id == OrderLine.order_id).where(
        Order.state.in_(REVENUE_STATES),
    ).group_by(OrderLine.product_name).order_by(func.sum(OrderLine.line_total).desc()).limit(20))).all()
    return [{"name": name, "units": units, "revenue": f"{revenue:.2f}"} for name, units, revenue in rows]


@router.get("/analytics/retention")
async def retention_performance(_: Customer = Depends(staff), db: AsyncSession = Depends(session)):
    tiers = (await db.execute(select(
        LoyaltyAccount.tier, func.count(LoyaltyAccount.customer_id),
    ).group_by(LoyaltyAccount.tier))).all()
    issued = await db.scalar(select(func.coalesce(func.sum(LoyaltyLedgerEntry.points), 0)).where(LoyaltyLedgerEntry.points > 0))
    redeemed = await db.scalar(select(func.coalesce(func.sum(-LoyaltyLedgerEntry.points), 0)).where(LoyaltyLedgerEntry.points < 0))
    referrals_total = await db.scalar(select(func.count(Referral.id)))
    referrals_completed = await db.scalar(select(func.count(Referral.id)).where(Referral.state == "completed"))
    campaigns = await db.scalar(select(func.count(MarketingCampaign.id)).where(MarketingCampaign.state == "completed"))
    dispatches = await db.scalar(select(func.count(CampaignDelivery.id)).where(CampaignDelivery.delivered_at.is_not(None)))
    return {
        "tiers": {tier: count for tier, count in tiers},
        "points_issued": issued, "points_redeemed": redeemed,
        "referrals_total": referrals_total, "referrals_completed": referrals_completed,
        "referral_conversion_rate": round(referrals_completed / referrals_total * 100, 1) if referrals_total else 0,
        "completed_campaigns": campaigns, "campaign_dispatches": dispatches,
    }


@router.get("/customers")
async def customers(
    segment: str = Query(default="all"), search: str = Query(default="", max_length=100),
    limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0),
    _: Customer = Depends(staff), db: AsyncSession = Depends(session),
):
    if segment not in SEGMENTS:
        raise HTTPException(status_code=422, detail="Unknown customer segment")
    ids = await customer_ids_for_segment(db, segment)
    statement = select(Customer).where(Customer.id.in_(ids))
    if search.strip():
        pattern = f"%{search.strip()}%"
        statement = statement.where(or_(Customer.email.ilike(pattern), Customer.first_name.ilike(pattern), Customer.last_name.ilike(pattern)))
    items = (await db.scalars(statement.order_by(Customer.created_at.desc()).offset(offset).limit(limit))).all()
    account_map = {item.customer_id: item for item in (await db.scalars(select(LoyaltyAccount).where(
        LoyaltyAccount.customer_id.in_([item.id for item in items]),
    ))).all()} if items else {}
    return [{
        "id": str(item.id), "name": f"{item.first_name} {item.last_name}".strip(), "email": item.email,
        "phone": item.phone, "created_at": item.created_at,
        "tier": account_map[item.id].tier if item.id in account_map else "silver",
        "lifetime_spend": f"{account_map[item.id].lifetime_spend:.2f}" if item.id in account_map else "0.00",
    } for item in items]


@router.get("/crm/leads")
async def list_leads(
    stage: str | None = None, _: Customer = Depends(crm_staff), db: AsyncSession = Depends(session),
):
    statement = select(CRMLead)
    if stage:
        if stage not in LEAD_STAGES:
            raise HTTPException(status_code=422, detail="Unknown CRM stage")
        statement = statement.where(CRMLead.stage == stage)
    return [lead_read(item) for item in (await db.scalars(statement.order_by(CRMLead.updated_at.desc()).limit(200))).all()]


@router.post("/crm/leads", status_code=201)
async def create_lead(payload: LeadInput, request: Request, actor: Customer = Depends(crm_staff), db: AsyncSession = Depends(session)):
    lead = CRMLead(created_by=actor.id, **payload.model_dump())
    db.add(lead)
    await db.flush()
    record_audit(db, actor, request, "crm.lead.created", "crm_lead", lead.id, payload.model_dump(mode="json"))
    await db.commit()
    await db.refresh(lead)
    return lead_read(lead)


@router.patch("/crm/leads/{lead_id}/stage")
async def update_lead_stage(lead_id: UUID, payload: LeadStageInput, request: Request, actor: Customer = Depends(crm_staff), db: AsyncSession = Depends(session)):
    lead = await db.get(CRMLead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    previous = lead.stage
    lead.stage = payload.stage
    db.add(CRMActivity(lead_id=lead.id, actor_id=actor.id, activity_type="note", summary=payload.note))
    record_audit(db, actor, request, "crm.lead.stage_changed", "crm_lead", lead.id, {"from": previous, "to": payload.stage, "note": payload.note})
    await db.commit()
    return lead_read(lead)


@router.post("/crm/leads/{lead_id}/activities", status_code=201)
async def add_activity(lead_id: UUID, payload: ActivityInput, request: Request, actor: Customer = Depends(crm_staff), db: AsyncSession = Depends(session)):
    if not await db.get(CRMLead, lead_id):
        raise HTTPException(status_code=404, detail="Lead not found")
    activity = CRMActivity(lead_id=lead_id, actor_id=actor.id, **payload.model_dump())
    db.add(activity)
    record_audit(db, actor, request, "crm.activity.created", "crm_lead", lead_id, payload.model_dump())
    await db.commit()
    return {"id": str(activity.id), "created": True}


@router.post("/crm/leads/{lead_id}/tasks", status_code=201)
async def add_task(lead_id: UUID, payload: TaskInput, request: Request, actor: Customer = Depends(crm_staff), db: AsyncSession = Depends(session)):
    if not await db.get(CRMLead, lead_id):
        raise HTTPException(status_code=404, detail="Lead not found")
    task = CRMTask(lead_id=lead_id, assignee_id=payload.assignee_id or actor.id, title=payload.title, due_at=payload.due_at)
    db.add(task)
    await db.flush()
    record_audit(db, actor, request, "crm.task.created", "crm_task", task.id, payload.model_dump(mode="json"))
    await db.commit()
    return {"id": str(task.id), "created": True}


@router.get("/campaigns")
async def list_campaigns(_: Customer = Depends(growth_staff), db: AsyncSession = Depends(session)):
    items = (await db.scalars(select(MarketingCampaign).order_by(MarketingCampaign.created_at.desc()).limit(100))).all()
    if not items:
        return []
    counts = (await db.execute(select(
        CampaignDelivery.campaign_id, func.count(CampaignDelivery.id),
        func.count(CampaignDelivery.delivered_at),
    ).where(CampaignDelivery.campaign_id.in_([item.id for item in items])).group_by(CampaignDelivery.campaign_id))).all()
    mapped = {campaign_id: (total, sent) for campaign_id, total, sent in counts}
    return [campaign_read(item, *mapped.get(item.id, (0, 0))) for item in items]


@router.post("/campaigns", status_code=201)
async def create_campaign(payload: CampaignInput, request: Request, actor: Customer = Depends(growth_staff), db: AsyncSession = Depends(session)):
    campaign = MarketingCampaign(created_by=actor.id, **payload.model_dump())
    db.add(campaign)
    await db.flush()
    record_audit(db, actor, request, "campaign.created", "campaign", campaign.id, payload.model_dump())
    await db.commit()
    return campaign_read(campaign)


@router.post("/campaigns/{campaign_id}/schedule")
async def schedule_campaign(campaign_id: UUID, payload: ScheduleInput, request: Request, actor: Customer = Depends(growth_staff), db: AsyncSession = Depends(session)):
    campaign = await db.get(MarketingCampaign, campaign_id, with_for_update=True)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.state not in ("draft", "scheduled"):
        raise HTTPException(status_code=409, detail="Only draft campaigns can be scheduled")
    scheduled = payload.scheduled_at
    if scheduled.tzinfo is None:
        scheduled = scheduled.replace(tzinfo=timezone.utc)
    campaign.state, campaign.scheduled_at = "scheduled", scheduled
    record_audit(db, actor, request, "campaign.scheduled", "campaign", campaign.id, {"scheduled_at": scheduled.isoformat()})
    await db.commit()
    return campaign_read(campaign)


@router.post("/campaigns/{campaign_id}/cancel")
async def cancel_campaign(campaign_id: UUID, request: Request, actor: Customer = Depends(growth_staff), db: AsyncSession = Depends(session)):
    campaign = await db.get(MarketingCampaign, campaign_id, with_for_update=True)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.state not in ("draft", "scheduled"):
        raise HTTPException(status_code=409, detail="Campaign can no longer be cancelled")
    campaign.state = "cancelled"
    record_audit(db, actor, request, "campaign.cancelled", "campaign", campaign.id)
    await db.commit()
    return campaign_read(campaign)


@router.get("/audit")
async def audit_log(
    limit: int = Query(default=100, ge=1, le=250), action: str | None = None,
    _: Customer = Depends(require_roles("admin", "manager")), db: AsyncSession = Depends(session),
):
    statement = select(AuditEvent)
    if action:
        statement = statement.where(AuditEvent.action == action)
    events = (await db.scalars(statement.order_by(AuditEvent.created_at.desc()).limit(limit))).all()
    return [{
        "id": str(item.id), "actor_id": str(item.actor_id) if item.actor_id else None,
        "action": item.action, "target_type": item.target_type, "target_id": item.target_id,
        "changes": item.changes, "ip_address": item.ip_address, "created_at": item.created_at,
    } for item in events]
