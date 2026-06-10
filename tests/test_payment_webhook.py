from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import payment_server

TEST_DB = Path(__file__).with_name("_payment_test_orders.db")


@pytest.fixture(autouse=True)
def clean_payment_test_db():
    if TEST_DB.exists():
        TEST_DB.unlink()
    yield
    if TEST_DB.exists():
        TEST_DB.unlink()


class FakePayment:
    def __init__(self, payment_id: str, status: str, value: str = "79.00", currency: str = "EUR"):
        self.id = payment_id
        self.status = status
        self.amount = {"value": value, "currency": currency}

    def is_paid(self):
        return self.status == "paid"

    def is_failed(self):
        return self.status == "failed"

    def is_expired(self):
        return self.status == "expired"

    def is_canceled(self):
        return self.status == "canceled"


class FakePayments:
    def __init__(self, payments):
        self._payments = payments

    def get(self, payment_id):
        return self._payments[payment_id]


class FakeMollie:
    def __init__(self, payments):
        self.payments = FakePayments(payments)


def _client():
    app = FastAPI()
    app.include_router(payment_server.payment_router, prefix="/api/payment")
    return TestClient(app)


def _prepare_db(monkeypatch):
    if TEST_DB.exists():
        TEST_DB.unlink()
    monkeypatch.setattr(payment_server, "DB_PATH", TEST_DB)
    payment_server._init_db()
    return TEST_DB


def _insert_order(status="pending", scan_status="pending", amount="79.00"):
    conn = payment_server._db()
    conn.execute(
        """INSERT INTO orders
           (order_id, mollie_id, product, company_name, kvk_number, domain,
            customer_email, amount, currency, status, scan_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "ds_test",
            "tr_test",
            "compact",
            "Mollie B.V.",
            "56087887",
            "mollie.com",
            "finance@mollie.com",
            amount,
            "EUR",
            status,
            scan_status,
        ),
    )
    conn.commit()
    conn.close()


def test_paid_webhook_queues_scan_once(monkeypatch):
    _prepare_db(monkeypatch)
    _insert_order()

    queued = []
    notified = []
    monkeypatch.setattr(
        payment_server,
        "_mollie",
        lambda: FakeMollie({"tr_test": FakePayment("tr_test", "paid")}),
    )
    monkeypatch.setattr(payment_server, "_queue_scan_order", lambda **kwargs: queued.append(kwargs))
    monkeypatch.setattr(payment_server, "_notify_admin", lambda **kwargs: notified.append(kwargs))

    client = _client()
    first = client.post("/api/payment/webhook", data={"id": "tr_test"})
    second = client.post("/api/payment/webhook", data={"id": "tr_test"})

    assert first.status_code == 200
    assert first.json()["action"] == "queued"
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"
    assert len(queued) == 1
    assert queued[0]["domain"] == "mollie.com"
    assert queued[0]["email"] == "finance@mollie.com"
    assert len(notified) == 1

    conn = payment_server._db()
    row = conn.execute(
        "SELECT status, scan_status, webhook_count, last_webhook_action FROM orders WHERE order_id = ?",
        ("ds_test",),
    ).fetchone()
    events = conn.execute("SELECT action FROM payment_events ORDER BY id").fetchall()
    conn.close()

    assert row["status"] == "paid"
    assert row["scan_status"] == "queued"
    assert row["webhook_count"] == 2
    assert row["last_webhook_action"] == "duplicate_paid_ignored"
    assert [event["action"] for event in events] == [
        "paid_queueing",
        "paid_queued",
        "duplicate_paid_ignored",
    ]


def test_amount_mismatch_does_not_queue_or_mark_paid(monkeypatch):
    _prepare_db(monkeypatch)
    _insert_order(amount="79.00")

    queued = []
    monkeypatch.setattr(
        payment_server,
        "_mollie",
        lambda: FakeMollie({"tr_test": FakePayment("tr_test", "paid", value="399.00")}),
    )
    monkeypatch.setattr(payment_server, "_queue_scan_order", lambda **kwargs: queued.append(kwargs))

    response = _client().post("/api/payment/webhook", data={"id": "tr_test"})

    assert response.status_code == 200
    assert response.json()["status"] == "amount_mismatch"
    assert queued == []

    conn = payment_server._db()
    row = conn.execute(
        "SELECT status, scan_status, last_webhook_action FROM orders WHERE order_id = ?",
        ("ds_test",),
    ).fetchone()
    event = conn.execute("SELECT action FROM payment_events").fetchone()
    conn.close()

    assert row["status"] == "pending"
    assert row["scan_status"] == "pending"
    assert row["last_webhook_action"] == "amount_mismatch"
    assert event["action"] == "amount_mismatch"


def test_terminal_webhook_cannot_downgrade_paid_order(monkeypatch):
    _prepare_db(monkeypatch)
    _insert_order(status="paid", scan_status="queued")

    monkeypatch.setattr(
        payment_server,
        "_mollie",
        lambda: FakeMollie({"tr_test": FakePayment("tr_test", "canceled")}),
    )

    response = _client().post("/api/payment/webhook", data={"id": "tr_test"})

    assert response.status_code == 200
    assert response.json()["status"] == "ignored_paid"

    conn = payment_server._db()
    row = conn.execute(
        "SELECT status, scan_status, last_webhook_action FROM orders WHERE order_id = ?",
        ("ds_test",),
    ).fetchone()
    conn.close()

    assert row["status"] == "paid"
    assert row["scan_status"] == "queued"
    assert row["last_webhook_action"] == "terminal_status_ignored_after_paid"
