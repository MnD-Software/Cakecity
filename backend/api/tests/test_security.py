import base64
import hashlib
import hmac
from app.security import delivery_key, verify_webhook_signature


def test_webhook_signature_accepts_valid_digest():
    body, secret = b'{"id":42}', "secret"
    signature = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    assert verify_webhook_signature(body, signature, secret)


def test_webhook_signature_rejects_missing_or_modified_digest():
    assert not verify_webhook_signature(b"{}", None, "secret")
    assert not verify_webhook_signature(b'{"id":43}', "invalid", "secret")


def test_delivery_key_is_deterministic_and_payload_sensitive():
    assert delivery_key("1", "product.updated", b"a") == delivery_key("1", "product.updated", b"a")
    assert delivery_key("1", "product.updated", b"a") != delivery_key("1", "product.updated", b"b")
