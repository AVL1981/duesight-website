import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import payment_server


ROOT = Path(__file__).resolve().parents[1]
TEST_DB = Path(__file__).with_name("_refund_flow_test_orders.db")
SUPPORT_FILE = Path(__file__).with_name("_refund_support_events.jsonl")
ADMIN_HEADERS = {"X-DueSight-Admin-Secret": "unit-admin-secret"}


@pytest.fixture(autouse=True)
def clean_refund_test_files():
    for path in (TEST_DB, SUPPORT_FILE):
        if path.exists():
            path.unlink()
    yield
    for path in (TEST_DB, SUPPORT_FILE):
        if path.exists():
            path.unlink()


def _client():
    app = FastAPI()
    app.include_router(payment_server.payment_router, prefix="/api/payment")
    return TestClient(app)


def _prepare(monkeypatch):
    monkeypatch.setattr(payment_server, "DB_PATH", TEST_DB)
    monkeypatch.setattr(payment_server, "SUPPORT_EVENTS_FILE", SUPPORT_FILE)
    monkeypatch.setenv("DUESIGHT_PAYMENT_ADMIN_SECRET", "unit-admin-secret")
    payment_server._init_db()


def _insert_order(status="paid", scan_status="queued", refund_status="none"):
    conn = payment_server._db()
    conn.execute(
        """INSERT INTO orders
           (order_id, mollie_id, product, company_name, customer_email, amount,
            currency, status, scan_status, refund_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "ds_refund",
            "tr_refund",
            "compact",
            "Mollie B.V.",
            "finance@mollie.com",
            "79.00",
            "EUR",
            status,
            scan_status,
            refund_status,
        ),
    )
    conn.commit()
    conn.close()


def test_paid_order_refund_request_is_logged(monkeypatch):
    _prepare(monkeypatch)
    _insert_order(status="paid", scan_status="queued")

    response = _client().post(
        "/api/payment/refund/request",
        json={
            "order_id": "ds_refund",
            "customer_email": "finance@mollie.com",
            "reason": "Customer requested cancellation inside review window.",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "refund_requested"

    conn = payment_server._db()
    row = conn.execute(
        """SELECT status, scan_status, refund_status, refund_reason,
                  refund_contact_email, refund_requested_at
           FROM orders WHERE order_id = ?""",
        ("ds_refund",),
    ).fetchone()
    event = conn.execute("SELECT action FROM payment_events").fetchone()
    conn.close()

    assert row["status"] == "paid"
    assert row["scan_status"] == "queued"
    assert row["refund_status"] == "requested"
    assert row["refund_reason"].startswith("Customer requested")
    assert row["refund_contact_email"] == "finance@mollie.com"
    assert row["refund_requested_at"]
    assert event["action"] == "refund_requested"

    support_event = json.loads(SUPPORT_FILE.read_text(encoding="utf-8").strip())
    assert support_event["type"] == "refund_requested"
    assert support_event["order_id"] == "ds_refund"


def test_unpaid_order_cancellation_is_recorded(monkeypatch):
    _prepare(monkeypatch)
    _insert_order(status="pending", scan_status="pending")

    response = _client().post(
        "/api/payment/refund/request",
        json={
            "order_id": "ds_refund",
            "customer_email": "finance@mollie.com",
            "reason": "Customer stopped before payment.",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancellation_recorded"

    conn = payment_server._db()
    row = conn.execute(
        "SELECT status, refund_status, refund_resolution, refund_resolved_at FROM orders WHERE order_id = ?",
        ("ds_refund",),
    ).fetchone()
    conn.close()

    assert row["status"] == "canceled"
    assert row["refund_status"] == "canceled"
    assert row["refund_resolution"] == "customer_cancelled_before_payment"
    assert row["refund_resolved_at"]


def test_admin_refund_resolution_marks_order_refunded(monkeypatch):
    _prepare(monkeypatch)
    _insert_order(status="paid", scan_status="queued", refund_status="requested")
    monkeypatch.setenv("MOLLIE_API_KEY", "test_unit_should_not_print")
    captured = {}

    def fake_refund(**kwargs):
        captured.update(kwargs)
        return {"id": "re_admin_secret", "status": "queued"}

    monkeypatch.setattr(payment_server, "_create_mollie_payment_refund", fake_refund)

    response = _client().post(
        "/api/payment/refund/resolve",
        headers=ADMIN_HEADERS,
        json={
            "order_id": "ds_refund",
            "decision": "refunded",
            "note": "Manual Mollie test refund completed by Arian.",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "refunded",
        "order_id": "ds_refund",
        "refund_created": True,
        "amount": "79.00",
        "currency": "EUR",
        "mollie_refund_status": "queued",
    }
    assert captured == {
        "payment_id": "tr_refund",
        "amount": "79.00",
        "currency": "EUR",
        "description": "Manual Mollie test refund completed by Arian.",
        "metadata": {"order_id": "ds_refund", "source": "duesight_refund_smoke"},
    }

    conn = payment_server._db()
    row = conn.execute(
        """SELECT status, scan_status, refund_status, refund_resolution,
                  refund_resolved_at, refunded_at
           FROM orders WHERE order_id = ?""",
        ("ds_refund",),
    ).fetchone()
    events = conn.execute("SELECT action FROM payment_events ORDER BY id").fetchall()
    conn.close()

    assert row["status"] == "refunded"
    assert row["scan_status"] == "cancelled"
    assert row["refund_status"] == "refunded"
    assert row["refund_resolution"] == "Manual Mollie test refund completed by Arian."
    assert row["refund_resolved_at"]
    assert row["refunded_at"]
    assert [event["action"] for event in events] == ["mollie_refund_created"]


def test_admin_refund_resolution_refuses_live_key_without_explicit_allow(monkeypatch):
    _prepare(monkeypatch)
    _insert_order(status="paid", scan_status="queued", refund_status="requested")
    monkeypatch.setenv("MOLLIE_API_KEY", "live_unit_should_not_print")

    response = _client().post(
        "/api/payment/refund/resolve",
        headers=ADMIN_HEADERS,
        json={
            "order_id": "ds_refund",
            "decision": "refunded",
            "note": "Manual Mollie refund",
        },
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload["code"] == "live_key_requires_allow_live"
    assert "live_unit_should_not_print" not in json.dumps(payload)


def test_admin_refund_resolution_requires_secret(monkeypatch):
    _prepare(monkeypatch)
    _insert_order(status="paid", scan_status="queued", refund_status="requested")
    client = _client()

    missing = client.post(
        "/api/payment/refund/resolve",
        json={"order_id": "ds_refund", "decision": "refunded", "note": "Manual refund"},
    )
    wrong = client.post(
        "/api/payment/refund/resolve",
        headers={"X-DueSight-Admin-Secret": "wrong"},
        json={"order_id": "ds_refund", "decision": "refunded", "note": "Manual refund"},
    )

    assert missing.status_code == 403
    assert wrong.status_code == 403


def test_mollie_payment_refund_posts_expected_payload(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def getcode(self):
            return 201

        def read(self, limit):
            return b'{"id":"re_unit_secret","status":"queued"}'

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setenv("MOLLIE_API_KEY", "test_unit_should_not_print")
    monkeypatch.setattr(payment_server.urllib.request, "urlopen", fake_urlopen)

    result = payment_server._create_mollie_payment_refund(
        payment_id="tr_refund",
        amount="79.00",
        currency="EUR",
        description="DueSight refund smoke",
        metadata={"order_id": "ds_refund"},
    )

    assert result["id"] == "re_unit_secret"
    assert captured["url"].endswith("/v2/payments/tr_refund/refunds")
    assert captured["headers"]["Authorization"] == "Bearer test_unit_should_not_print"
    assert captured["payload"]["amount"] == {"currency": "EUR", "value": "79.00"}
    assert captured["payload"]["description"] == "DueSight refund smoke"
    assert captured["payload"]["metadata"] == {"order_id": "ds_refund"}
    assert captured["timeout"] == 20


def test_mollie_refund_smoke_marks_order_refunded(monkeypatch):
    _prepare(monkeypatch)
    _insert_order(status="paid", scan_status="queued", refund_status="requested")
    monkeypatch.setenv("MOLLIE_API_KEY", "test_unit_should_not_print")
    monkeypatch.setattr(
        payment_server,
        "_create_mollie_payment_refund",
        lambda **kwargs: {"id": "re_unit_secret", "status": "queued"},
    )

    result = payment_server.create_mollie_refund_for_order(
        "ds_refund",
        amount="79.00",
        note="DueSight refund smoke",
    )

    assert payment_server._redact_refund_result(result) == {
        "status": "refunded",
        "order_id": "ds_refund",
        "refund_created": True,
        "amount": "79.00",
        "currency": "EUR",
        "mollie_refund_status": "queued",
    }

    conn = payment_server._db()
    row = conn.execute(
        """SELECT status, scan_status, refund_status, refund_resolution, refunded_at
           FROM orders WHERE order_id = ?""",
        ("ds_refund",),
    ).fetchone()
    event = conn.execute("SELECT action, details FROM payment_events WHERE order_id = ?", ("ds_refund",)).fetchone()
    conn.close()

    assert row["status"] == "refunded"
    assert row["scan_status"] == "cancelled"
    assert row["refund_status"] == "refunded"
    assert row["refund_resolution"] == "DueSight refund smoke"
    assert row["refunded_at"]
    assert event["action"] == "mollie_refund_created"
    assert json.loads(event["details"]) == {"refund_status": "queued"}


def test_refund_smoke_cli_refuses_live_key_without_override(tmp_path):
    db_path = tmp_path / "orders.db"
    old_db = payment_server.DB_PATH
    try:
        payment_server.DB_PATH = db_path
        payment_server._init_db()
        conn = payment_server._db()
        conn.execute(
            """INSERT INTO orders
               (order_id, mollie_id, product, company_name, customer_email, amount,
                currency, status, scan_status, refund_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("ds_cli_refund", "tr_cli_refund_secret", "compact", "Mollie B.V.", "finance@mollie.com", "79.00", "EUR", "paid", "queued", "requested"),
        )
        conn.commit()
        conn.close()
    finally:
        payment_server.DB_PATH = old_db

    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(ROOT),
            "PYTHONDONTWRITEBYTECODE": "1",
            "DUESIGHT_PAYMENT_DB_PATH": str(db_path),
            "MOLLIE_API_KEY": "live_unit_should_not_print",
        }
    )
    result = subprocess.run(
        [sys.executable, str(ROOT / "payment_server.py"), "refund-smoke", "--order-id", "ds_cli_refund"],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 2
    assert "live_unit_should_not_print" not in combined
    assert "tr_cli_refund_secret" not in combined
    payload = json.loads(result.stdout)
    assert payload["status"] == "refused"
    assert payload["code"] == "live_key_requires_allow_live"
    assert payload["refund_created"] is False


def test_refund_amount_cannot_exceed_order_amount(monkeypatch):
    """Amount cap: refund_amount > order.amount must be rejected."""
    _prepare(monkeypatch)
    _insert_order(status="paid", scan_status="queued", refund_status="requested")
    monkeypatch.setenv("MOLLIE_API_KEY", "test_unit_should_not_print")

    with pytest.raises(ValueError, match="refund_amount_exceeds_order"):
        payment_server.create_mollie_refund_for_order(
            "ds_refund",
            amount="99.00",  # order amount is 79.00
            note="Over-cap refund attempt",
        )

    # Verify order remains 'paid' (status not mutated on validation failure)
    conn = payment_server._db()
    row = conn.execute("SELECT status FROM orders WHERE order_id = ?", ("ds_refund",)).fetchone()
    conn.close()
    assert row["status"] == "paid"


def test_refund_toctou_guard_rejects_concurrent_refund(monkeypatch):
    """TOCTOU guard: once status is 'refunding', a second call must fail."""
    _prepare(monkeypatch)
    _insert_order(status="paid", scan_status="queued", refund_status="requested")
    monkeypatch.setenv("MOLLIE_API_KEY", "test_unit_should_not_print")
    monkeypatch.setattr(
        payment_server,
        "_create_mollie_payment_refund",
        lambda **kwargs: {"id": "re_toctou", "status": "queued"},
    )

    # First refund succeeds (atomically sets status to 'refunding' then 'refunded')
    result1 = payment_server.create_mollie_refund_for_order("ds_refund", amount="79.00")
    assert result1["status"] == "refunded"

    # Second refund must fail — order is now 'refunded', not 'paid'
    with pytest.raises(ValueError, match="order_not_paid"):
        payment_server.create_mollie_refund_for_order("ds_refund", amount="79.00")


def test_refund_toctou_rollback_on_mollie_failure(monkeypatch):
    """TOCTOU rollback: if Mollie call fails, order status must revert to 'paid'."""
    _prepare(monkeypatch)
    _insert_order(status="paid", scan_status="queued", refund_status="requested")
    monkeypatch.setenv("MOLLIE_API_KEY", "test_unit_should_not_print")
    monkeypatch.setattr(
        payment_server,
        "_create_mollie_payment_refund",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("mollie_refund_unavailable")),
    )

    with pytest.raises(RuntimeError, match="mollie_refund_unavailable"):
        payment_server.create_mollie_refund_for_order("ds_refund", amount="79.00")

    # Order must be rolled back to 'paid' (not stuck in 'refunding')
    conn = payment_server._db()
    row = conn.execute("SELECT status FROM orders WHERE order_id = ?", ("ds_refund",)).fetchone()
    conn.close()
    assert row["status"] == "paid"


def test_refund_exact_order_amount_is_allowed(monkeypatch):
    """Boundary check: refund_amount == order.amount must succeed."""
    _prepare(monkeypatch)
    _insert_order(status="paid", scan_status="queued", refund_status="requested")
    monkeypatch.setenv("MOLLIE_API_KEY", "test_unit_should_not_print")
    monkeypatch.setattr(
        payment_server,
        "_create_mollie_payment_refund",
        lambda **kwargs: {"id": "re_exact", "status": "queued"},
    )

    result = payment_server.create_mollie_refund_for_order("ds_refund", amount="79.00")
    assert result["status"] == "refunded"
    assert result["amount"] == "79.00"
