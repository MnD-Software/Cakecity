from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from fastapi import HTTPException
from app.auth import create_access_token, decode_access_token, hash_password, new_refresh_token, verify_password


def test_password_hash_is_salted_and_verifiable():
    first = hash_password("a-secure-cake-password")
    second = hash_password("a-secure-cake-password")
    assert first != second
    assert verify_password("a-secure-cake-password", first)
    assert not verify_password("wrong-password", first)


def test_access_token_is_signed_and_expires():
    issued = datetime(2026, 7, 26, tzinfo=timezone.utc)
    customer_id = uuid4()
    token = create_access_token(customer_id, "customer", issued)
    claims = decode_access_token(token, issued + timedelta(minutes=1))
    assert claims["sub"] == str(customer_id)
    assert claims["role"] == "customer"
    with pytest.raises(HTTPException):
        decode_access_token(token, issued + timedelta(hours=1))
    with pytest.raises(HTTPException):
        decode_access_token(token[:-2] + "aa", issued + timedelta(minutes=1))


def test_refresh_tokens_are_opaque_and_unique():
    first, first_hash = new_refresh_token()
    second, second_hash = new_refresh_token()
    assert first != second
    assert first_hash != second_hash
    assert first not in first_hash
