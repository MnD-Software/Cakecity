import base64
import hashlib
import hmac


def verify_webhook_signature(body: bytes, signature: str | None, secret: str) -> bool:
    if not signature or not secret:
        return False
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("ascii")
    return hmac.compare_digest(expected, signature.strip())


def delivery_key(webhook_id: str, topic: str, body: bytes) -> str:
    fingerprint = hashlib.sha256(body).hexdigest()
    return f"{webhook_id}:{topic}:{fingerprint}"
