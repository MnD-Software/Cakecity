from fastapi import Request
from ..models import AuditEvent, Customer


def record_audit(
    db, actor: Customer, request: Request, action: str, target_type: str,
    target_id, changes: dict | None = None,
) -> AuditEvent:
    forwarded = request.headers.get("x-forwarded-for")
    ip_address = forwarded.split(",")[0].strip() if forwarded else request.client.host if request.client else None
    event = AuditEvent(
        actor_id=actor.id, action=action, target_type=target_type, target_id=str(target_id),
        changes=changes or {}, ip_address=ip_address,
        user_agent=request.headers.get("user-agent", "")[:500],
        correlation_id=request.headers.get("x-request-id", "")[:100] or None,
    )
    db.add(event)
    return event
