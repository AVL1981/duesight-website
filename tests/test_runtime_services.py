from fastapi.testclient import TestClient


def _assert_security_headers(response):
    assert response.headers["Content-Security-Policy"]
    assert response.headers["Strict-Transport-Security"].startswith("max-age=")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Permissions-Policy"]
    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"


def test_refactored_api_health_imports_and_responds():
    from app.main import app

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_payment_server_root_imports_and_responds():
    import payment_server

    response = TestClient(payment_server.create_app()).get("/")

    assert response.status_code == 200
    assert response.json()["service"] == "DueSight Payment Server"
    _assert_security_headers(response)


def test_scan_server_health_imports_and_responds(monkeypatch):
    import scan_server

    monkeypatch.setattr(scan_server, "DDINTEL_BASE", "http://127.0.0.1:9")
    response = TestClient(scan_server.app).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "ddintel_connected" in response.json()


def test_scan_server_root_has_security_headers():
    import scan_server

    response = TestClient(scan_server.app).get("/")

    assert response.status_code == 200
    assert response.json()["service"] == "DueSight Scan Server"
    _assert_security_headers(response)


def test_refactored_api_non_health_has_security_headers():
    from app.main import app

    response = TestClient(app).get("/api/cache-stats")

    assert response.status_code in {200, 503}
    _assert_security_headers(response)
