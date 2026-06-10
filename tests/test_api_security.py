from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.security import configure_api_security


def make_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("DUESIGHT_AUTH_ENABLED", "true")
    monkeypatch.setenv("DUESIGHT_API_KEYS", "api-test-key")
    monkeypatch.setenv("DUESIGHT_ADMIN_API_KEYS", "admin-test-key")
    monkeypatch.setenv("DUESIGHT_PUBLIC_RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.setenv("DUESIGHT_PROTECTED_RATE_LIMIT_PER_MINUTE", "5")
    monkeypatch.setenv("DUESIGHT_RATE_WINDOW_SECONDS", "60")

    app = FastAPI()
    configure_api_security(
        app,
        public_paths={"/health"},
        public_limited_paths={"/api/demo"},
        admin_prefixes={"/api/admin"},
    )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/secure")
    async def secure():
        return {"status": "secure"}

    @app.get("/api/admin/orders")
    async def admin_orders():
        return {"status": "admin"}

    @app.get("/api/demo")
    async def demo():
        return {"status": "demo"}

    return TestClient(app)


def test_health_is_public(monkeypatch):
    client = make_client(monkeypatch)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_protected_endpoint_requires_api_key(monkeypatch):
    client = make_client(monkeypatch)
    assert client.get("/api/secure").status_code == 401

    response = client.get("/api/secure", headers={"X-API-Key": "api-test-key"})
    assert response.status_code == 200
    assert response.headers["X-DueSight-Auth"] == "api"


def test_bearer_token_is_accepted(monkeypatch):
    client = make_client(monkeypatch)
    response = client.get("/api/secure", headers={"Authorization": "Bearer api-test-key"})
    assert response.status_code == 200
    assert response.headers["X-DueSight-Auth"] == "api"


def test_admin_endpoint_requires_admin_key(monkeypatch):
    client = make_client(monkeypatch)
    assert client.get("/api/admin/orders").status_code == 403
    assert client.get("/api/admin/orders", headers={"X-API-Key": "api-test-key"}).status_code == 403

    response = client.get("/api/admin/orders", headers={"X-API-Key": "admin-test-key"})
    assert response.status_code == 200
    assert response.headers["X-DueSight-Auth"] == "admin"


def test_public_demo_endpoint_is_rate_limited(monkeypatch):
    client = make_client(monkeypatch)
    assert client.get("/api/demo").status_code == 200
    assert client.get("/api/demo").status_code == 429
