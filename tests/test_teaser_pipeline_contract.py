from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routers import scan


def test_teaser_scan_contract_uses_public_preview_shape(monkeypatch):
    async def fake_call_ddintel(tool_name, params):
        if tool_name == "kvk_screen":
            return {
                "trade_name": "Mollie B.V.",
                "kvk_number": "56087887",
                "active": True,
                "legal_form": "Besloten Vennootschap",
                "city": "Amsterdam",
            }
        if tool_name == "scan_tech_stack":
            return {"technologies": ["Cloudflare", "React", "Stripe"]}
        if tool_name == "check_security_headers":
            return {"score": 88, "missing_headers": ["content-security-policy"]}
        if tool_name == "financial_proxy_analysis":
            return {"risk_flags": ["proxy_review_required"]}
        return {}

    monkeypatch.setattr(scan, "call_ddintel", fake_call_ddintel)

    app = FastAPI()
    app.include_router(scan.router, prefix="/api")
    response = TestClient(app).post("/api/teaser-scan?company_name=Mollie%20B.V.")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["company"] == "Mollie B.V."
    assert data["source_scope"] == "public-source preview"
    assert data["entity"]["status_active"] is True
    assert data["tech_stack"]["count"] == 3
    assert data["financial"]["flags_count"] == 1
    assert data["cyber"]["flags_count"] == 1
    assert data["total_flags"] == 2


def test_scan_server_legacy_checkout_is_disabled_by_default():
    import scan_server

    response = TestClient(scan_server.app).get("/api/checkout?tier=standard&domain=mollie.com")

    assert response.status_code == 410
    assert response.json()["replacement"] == "/api/payment/create"
