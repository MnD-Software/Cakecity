from starlette.requests import Request

from app.main import app
from app.middleware import client_fingerprint, limit_for
from app.settings import settings


def request(path: str, address: str = "203.0.113.8") -> Request:
    return Request({
        "type": "http", "method": "GET", "path": path, "raw_path": path.encode(),
        "query_string": b"", "headers": [], "client": (address, 1234),
        "server": ("testserver", 80), "scheme": "http",
    })


def test_auth_routes_receive_stricter_rate_limit():
    assert limit_for("/v1/auth/login") == settings.auth_rate_limit_per_minute
    assert limit_for("/v1/catalog/products") == settings.rate_limit_per_minute


def test_rate_fingerprint_is_stable_and_path_scoped():
    assert client_fingerprint(request("/a")) == client_fingerprint(request("/a"))
    assert client_fingerprint(request("/a")) != client_fingerprint(request("/b"))


def test_readiness_contract_is_published():
    assert "/ready" in app.openapi()["paths"]
