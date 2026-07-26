import base64
import hashlib
import hmac
from decimal import Decimal
import httpx


def verify_flutterwave_signature(body: bytes, signature: str | None, secret: str) -> bool:
    if not signature or not secret:
        return False
    expected = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    return hmac.compare_digest(expected, signature.strip())


class FlutterwaveClient:
    def __init__(self, base_url: str, secret_key: str, client: httpx.AsyncClient | None = None):
        if not secret_key:
            raise ValueError("Flutterwave is not configured")
        self.base_url = base_url.rstrip("/")
        self.secret_key = secret_key
        self.client = client

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        owned = self.client is None
        client = self.client or httpx.AsyncClient(timeout=httpx.Timeout(25.0))
        try:
            response = await client.request(
                method, f"{self.base_url}{path}",
                headers={"Authorization": f"Bearer {self.secret_key}", "Content-Type": "application/json"},
                **kwargs,
            )
            response.raise_for_status()
            return response.json()
        finally:
            if owned:
                await client.aclose()

    async def create_checkout(
        self, reference: str, amount: Decimal, email: str, phone: str,
        name: str, redirect_url: str,
    ) -> str:
        payload = await self._request("POST", "/v3/payments", json={
            "tx_ref": reference, "amount": str(amount), "currency": "KES",
            "redirect_url": redirect_url,
            "customer": {"email": email, "phonenumber": phone, "name": name},
            "customizations": {
                "title": "Cake City", "description": f"Celebration order {reference}",
            },
            "payment_options": "card",
        })
        link = payload.get("data", {}).get("link")
        if payload.get("status") != "success" or not link:
            raise RuntimeError("Card checkout could not be created")
        return link

    async def verify_transaction(self, transaction_id: str) -> dict:
        return await self._request("GET", f"/v3/transactions/{transaction_id}/verify")


def verified_flutterwave_payment(
    response: dict, expected_reference: str, expected_amount: Decimal, currency: str = "KES",
) -> bool:
    data = response.get("data", {})
    return (
        response.get("status") == "success"
        and data.get("status") == "successful"
        and str(data.get("tx_ref")) == expected_reference
        and str(data.get("currency")) == currency
        and Decimal(str(data.get("amount", "0"))) == expected_amount
    )
