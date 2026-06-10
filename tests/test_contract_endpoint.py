from fastapi.testclient import TestClient


def _assert_triage_disclaimer(disclaimer: str) -> None:
    assert "pre-DD" in disclaimer
    assert "GEEN legal advice" in disclaimer
    assert "GEEN clause review" in disclaimer


def test_contract_health_is_available_and_positioned():
    from app.main import app

    response = TestClient(app).get("/api/contract/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["scanner_available"] is True
    assert body["pattern_count"] >= 18
    _assert_triage_disclaimer(body["disclaimer"])


def test_contract_triage_returns_flags_and_disclaimer():
    from app.main import app

    payload = {
        "company_name": "Example Target",
        "source_label": "unit_test_contract.txt",
        "text": (
            "This agreement includes unlimited liability for Seller. "
            "A Change of Control without prior notice triggers default."
        ),
    }

    response = TestClient(app).post("/api/contract/triage", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["risk_level"] in {"HIGH", "CRITICAL"}
    assert body["risk_score"] > 0
    assert {flag["flag_type"] for flag in body["flags"]} >= {
        "UNLIMITED_LIABILITY",
        "CHANGE_OF_CONTROL_NO_NOTICE",
    }
    _assert_triage_disclaimer(body["disclaimer"])
