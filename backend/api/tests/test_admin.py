from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from starlette.requests import Request
from app.auth import require_roles
from app.main import app
from app.routes.admin import CampaignInput
from app.routes.auth import require_trusted_origin
from app.services.segments import SEGMENTS


@pytest.mark.asyncio
async def test_admin_role_dependency_denies_customer_and_allows_staff():
    dependency = require_roles("admin", "manager")
    with pytest.raises(HTTPException) as denied:
        await dependency(SimpleNamespace(role="customer"))
    assert denied.value.status_code == 403
    manager = SimpleNamespace(role="manager")
    assert await dependency(manager) is manager


def test_cross_site_cookie_requests_require_a_trusted_origin():
    trusted = Request({"type": "http", "method": "POST", "path": "/", "headers": [(b"origin", b"http://localhost:3001")]})
    require_trusted_origin(trusted)
    untrusted = Request({"type": "http", "method": "POST", "path": "/", "headers": [(b"origin", b"https://attacker.example")]})
    with pytest.raises(HTTPException) as denied:
        require_trusted_origin(untrusted)
    assert denied.value.status_code == 403


def test_campaign_contract_limits_channels_and_segments():
    campaign = CampaignInput(
        name="VIP launch", channel="push", audience_segment="vip",
        subject="A new collection", message="Reserved for our best customers.",
    )
    assert campaign.channel == "push"
    assert "birthday_upcoming" in SEGMENTS
    with pytest.raises(ValueError):
        CampaignInput(name="Bad", channel="sms", audience_segment="all", subject="x", message="x")


def test_all_admin_openapi_operations_require_bearer_authentication():
    schema = app.openapi()
    admin_operations = [
        operation for path, methods in schema["paths"].items() if path.startswith("/v1/admin")
        for method, operation in methods.items() if method in {"get", "post", "patch", "put", "delete"}
    ]
    assert len(admin_operations) >= 10
    assert all(operation.get("security") == [{"HTTPBearer": []}] for operation in admin_operations)
