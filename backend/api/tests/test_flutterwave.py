import base64
import hashlib
import hmac
from decimal import Decimal
import httpx
import pytest
from app.services.flutterwave import FlutterwaveClient, verified_flutterwave_payment, verify_flutterwave_signature


def test_webhook_signature_is_hmac_verified():
    body, secret = b'{"id":"wbk_1"}', "webhook-secret"
    signature = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    assert verify_flutterwave_signature(body, signature, secret)
    assert not verify_flutterwave_signature(body + b"x", signature, secret)


@pytest.mark.asyncio
async def test_hosted_card_checkout_uses_server_secret_and_kes():
    captured = {}
    def handler(request: httpx.Request):
        captured["request"] = request
        return httpx.Response(200, json={"status": "success", "data": {"link": "https://checkout.flutterwave.com/pay/1"}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = FlutterwaveClient("https://api.flutterwave.com", "FLW-SECRET", http)
        link = await client.create_checkout("CC-123", Decimal("3550"), "a@example.com", "0712", "Amani", "https://app.test/return")
    assert link.startswith("https://checkout.flutterwave.com")
    request = captured["request"]
    assert request.headers["Authorization"] == "Bearer FLW-SECRET"
    body = __import__("json").loads(request.content)
    assert body["currency"] == "KES"
    assert body["payment_options"] == "card"


def test_verification_requires_exact_reference_amount_and_currency():
    valid = {"status": "success", "data": {
        "status": "successful", "tx_ref": "CC-123", "currency": "KES", "amount": 3550,
    }}
    assert verified_flutterwave_payment(valid, "CC-123", Decimal("3550"))
    assert not verified_flutterwave_payment(valid, "CC-other", Decimal("3550"))
    assert not verified_flutterwave_payment(valid, "CC-123", Decimal("3500"))
