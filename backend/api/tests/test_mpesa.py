import base64
from datetime import datetime, timezone
from decimal import Decimal
import httpx
import pytest
from app.services.mpesa import MpesaClient, normalize_kenyan_phone, parse_stk_callback


def test_normalizes_common_kenyan_phone_formats():
    assert normalize_kenyan_phone("0712 345 678") == "254712345678"
    assert normalize_kenyan_phone("+254 712 345 678") == "254712345678"
    with pytest.raises(ValueError):
        normalize_kenyan_phone("1234")


@pytest.mark.asyncio
async def test_stk_push_uses_oauth_password_and_callback():
    requests = []
    def handler(request: httpx.Request):
        requests.append(request)
        if request.url.path.endswith("/oauth/v1/generate"):
            return httpx.Response(200, json={"access_token": "token"})
        return httpx.Response(200, json={
            "ResponseCode": "0", "CheckoutRequestID": "ws_CO_123",
            "MerchantRequestID": "merchant-1", "CustomerMessage": "Success",
        })
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = MpesaClient("https://sandbox.safaricom.co.ke", "key", "secret", "174379", "pass", http)
        result = await client.stk_push(
            Decimal("3200"), "0712345678", "CC-TEST", "https://api.test/callback",
            datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc),
        )
    assert result["CheckoutRequestID"] == "ws_CO_123"
    body = __import__("json").loads(requests[1].content)
    assert body["PhoneNumber"] == "254712345678"
    assert body["CallBackURL"] == "https://api.test/callback"
    assert base64.b64decode(body["Password"]).decode().startswith("174379pass")


def test_parses_successful_stk_callback():
    parsed = parse_stk_callback({"Body": {"stkCallback": {
        "MerchantRequestID": "m1", "CheckoutRequestID": "c1", "ResultCode": 0,
        "ResultDesc": "Success", "CallbackMetadata": {"Item": [
            {"Name": "Amount", "Value": 3200},
            {"Name": "MpesaReceiptNumber", "Value": "SAMPLE123"},
            {"Name": "PhoneNumber", "Value": 254712345678},
        ]},
    }}})
    assert parsed["amount"] == Decimal("3200")
    assert parsed["receipt"] == "SAMPLE123"
