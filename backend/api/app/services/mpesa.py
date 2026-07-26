import base64
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import re
import httpx

EAT = timezone(timedelta(hours=3))


def normalize_kenyan_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("0") and len(digits) == 10:
        digits = "254" + digits[1:]
    elif digits.startswith("7") and len(digits) == 9:
        digits = "254" + digits
    if not re.fullmatch(r"254[17]\d{8}", digits):
        raise ValueError("Enter a valid Kenyan Safaricom number")
    return digits


class MpesaClient:
    def __init__(
        self, base_url: str, consumer_key: str, consumer_secret: str,
        shortcode: str, passkey: str, client: httpx.AsyncClient | None = None,
    ):
        if not all((consumer_key, consumer_secret, shortcode, passkey)):
            raise ValueError("M-Pesa credentials are not configured")
        self.base_url = base_url.rstrip("/")
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.shortcode = shortcode
        self.passkey = passkey
        self.client = client

    async def _token(self, client: httpx.AsyncClient) -> str:
        response = await client.get(
            f"{self.base_url}/oauth/v1/generate",
            params={"grant_type": "client_credentials"},
            auth=(self.consumer_key, self.consumer_secret),
        )
        response.raise_for_status()
        return response.json()["access_token"]

    async def stk_push(
        self, amount: Decimal, phone: str, reference: str, callback_url: str,
        now: datetime | None = None,
    ) -> dict:
        if amount != amount.to_integral_value() or amount <= 0:
            raise ValueError("M-Pesa amount must be a positive whole KES value")
        timestamp = (now or datetime.now(EAT)).astimezone(EAT).strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(f"{self.shortcode}{self.passkey}{timestamp}".encode()).decode()
        owned = self.client is None
        client = self.client or httpx.AsyncClient(timeout=httpx.Timeout(25.0))
        try:
            token = await self._token(client)
            response = await client.post(
                f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "BusinessShortCode": self.shortcode,
                    "Password": password,
                    "Timestamp": timestamp,
                    "TransactionType": "CustomerPayBillOnline",
                    "Amount": int(amount),
                    "PartyA": normalize_kenyan_phone(phone),
                    "PartyB": self.shortcode,
                    "PhoneNumber": normalize_kenyan_phone(phone),
                    "CallBackURL": callback_url,
                    "AccountReference": reference[:12],
                    "TransactionDesc": f"Cake City {reference}"[:32],
                },
            )
            response.raise_for_status()
            payload = response.json()
            if str(payload.get("ResponseCode")) != "0":
                raise RuntimeError(payload.get("ResponseDescription", "M-Pesa rejected the request"))
            return payload
        finally:
            if owned:
                await client.aclose()


def parse_stk_callback(payload: dict) -> dict:
    callback = payload.get("Body", {}).get("stkCallback", {})
    result_code = int(callback.get("ResultCode", -1))
    metadata = {}
    for item in callback.get("CallbackMetadata", {}).get("Item", []):
        if "Name" in item:
            metadata[item["Name"]] = item.get("Value")
    return {
        "merchant_request_id": callback.get("MerchantRequestID"),
        "checkout_request_id": callback.get("CheckoutRequestID"),
        "result_code": result_code,
        "result_description": str(callback.get("ResultDesc", ""))[:500],
        "amount": Decimal(str(metadata["Amount"])) if "Amount" in metadata else None,
        "receipt": metadata.get("MpesaReceiptNumber"),
        "phone": str(metadata.get("PhoneNumber", "")) or None,
    }
