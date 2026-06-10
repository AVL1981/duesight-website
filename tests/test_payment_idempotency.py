"""Idempotency contract tests for the Mollie payment create + webhook flow.

Verifies BRIEF 3 acceptance criteria:
  A) Mollie create uses a stable Idempotency-Key derived from the order.
  B) Same webhook fired twice -> 1 report, 1 email, 1 refund side-effect.
  C) payment_events dedupes repeated action rows while webhook_count keeps
     the full delivery audit count.
"""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import payment_server


TEST_DB = Path(__file__).with_name("_payment_idempotency_orders.db")


@pytest.fixture(autouse=True)
def clean_idempotency_db():
    if TEST_DB.exists():
        TEST_DB.unlink()
    yield
    if TEST_DB.exists():
        TEST_DB.unlink()


class CreatedPayment:
    """Mollie-style created payment. Counter is per-instance so each create
    call gets a unique tr_idem_NNN id (mirrors real Mollie)."""

    _counter = [0]

    def __init__(self):
        type(self)._counter[0] += 1
        self.id = f"tr_idem_{type(self)._counter[0]:04d}"
        self.checkout_url = f"https://checkout.mollie.test/idem/{self.id}"


class PaidPayment:
    id = "tr_idem_payment"
    status = "paid"
    amount = {"value": "79.00", "currency": "EUR"}

    def is_paid(self):
        return True


class CanceledPayment:
    id = "tr_idem_payment"
    status = "canceled"
    amount = {"value": "79.00", "currency": "EUR"}

    def is_canceled(self):
        return True


class FakePayments:
    def __init__(self):
        self.create_calls: list[dict] = []
        self.idempotency_keys: list[str] = []
        self.get_responses: dict[str, object] = {}

    def create(self, payment_data, idempotency_key="", **_kwargs):
        self.create_calls.append(payment_data)
        self.idempotency_keys.append(idempotency_key)
        return CreatedPayment()

    def get(self, payment_id):
        return self.get_responses[payment_id]


class FakeMollie:
    def __init__(self, payments: FakePayments):
        self.payments = payments


def _client():
    app = FastAPI()
    app.include_router(payment_server.payment_router, prefix="/api/payment")
    return TestClient(app)


def _prepare(monkeypatch):
    monkeypatch.setattr(payment_server, "DB_PATH", TEST_DB)
    payment_server._init_db()


def _checkout_body(**overrides):
    body = {
        "product": "compact",
        "company_name": "Idempotency B.V.",
        "kvk_number": "56087887",
        "domain": "idem.test",
        "customer_email": "finance@idem.test",
        "terms_accepted": True,
    }
    body.update(overrides)
    return body


# ----------------------------------------------------------------------
# Task A - outbound Idempotency-Key
# ----------------------------------------------------------------------


def test_create_payment_passes_idempotency_key_derived_from_order(monkeypatch):
    _prepare(monkeypatch)
    fake_payments = FakePayments()
    monkeypatch.setattr(payment_server, "_mollie", lambda: FakeMollie(fake_payments))

    response = _client().post("/api/payment/create", json=_checkout_body())

    assert response.status_code == 200
    checkout = response.json()
    order_id = checkout["order_id"]
    assert checkout["payment_id"].startswith("tr_idem_")

    # Exactly one Mollie call
    assert len(fake_payments.create_calls) == 1

    # Idempotency-Key is set, stable, and derived from order_id
    assert len(fake_payments.idempotency_keys) == 1
    key = fake_payments.idempotency_keys[0]
    assert key == f"duesight-order-{order_id}"
    assert key.startswith("duesight-order-ds_")


def test_create_payment_is_deterministic_for_repeated_calls(monkeypatch):
    """Simulate retry safety: if a network blip causes the client to retry
    with the same order_id, the Idempotency-Key stays stable.

    We do not retry the create endpoint itself (it would generate a NEW
    order_id) - instead, the contract under test is that the key is a pure
    function of order_id. Two distinct orders must receive distinct keys.
    """
    _prepare(monkeypatch)
    fake_payments = FakePayments()
    monkeypatch.setattr(payment_server, "_mollie", lambda: FakeMollie(fake_payments))

    first = _client().post("/api/payment/create", json=_checkout_body()).json()
    second = _client().post("/api/payment/create", json=_checkout_body()).json()

    assert first["order_id"] != second["order_id"]
    assert fake_payments.idempotency_keys[0] != fake_payments.idempotency_keys[1]
    assert fake_payments.idempotency_keys[0] == f"duesight-order-{first['order_id']}"
    assert fake_payments.idempotency_keys[1] == f"duesight-order-{second['order_id']}"


# ----------------------------------------------------------------------
# Task B - inbound exactly-once webhook
# ----------------------------------------------------------------------


def _insert_idem_order(status="pending", scan_status="pending"):
    conn = payment_server._db()
    conn.execute(
        """INSERT INTO orders
           (order_id, mollie_id, product, company_name, customer_email, amount,
            currency, status, scan_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "ds_idem",
            "tr_idem_payment",
            "compact",
            "Idempotency B.V.",
            "finance@idem.test",
            "79.00",
            "EUR",
            status,
            scan_status,
        ),
    )
    conn.commit()
    conn.close()


def test_duplicate_paid_webhook_does_not_requeue_or_renotify(monkeypatch):
    _prepare(monkeypatch)
    _insert_idem_order()

    fake_payments = FakePayments()
    fake_payments.get_responses["tr_idem_payment"] = PaidPayment()
    monkeypatch.setattr(payment_server, "_mollie", lambda: FakeMollie(fake_payments))

    queued: list[dict] = []
    notified: list[dict] = []
    monkeypatch.setattr(payment_server, "_queue_scan_order", lambda **kw: queued.append(kw))
    monkeypatch.setattr(payment_server, "_notify_admin", lambda **kw: notified.append(kw))

    client = _client()
    first = client.post("/api/payment/webhook", data={"id": "tr_idem_payment"})
    second = client.post("/api/payment/webhook", data={"id": "tr_idem_payment"})
    third = client.post("/api/payment/webhook", data={"id": "tr_idem_payment"})

    # First call queues + notifies; subsequent calls are deduped.
    assert first.json()["status"] == "paid"
    assert first.json()["action"] == "queued"
    assert second.json()["status"] == "duplicate"
    assert third.json()["status"] == "duplicate"

    # Exactly-once side-effects
    assert len(queued) == 1
    assert len(notified) == 1
    assert queued[0]["order_id"] == "ds_idem"
    assert queued[0]["email"] == "finance@idem.test"

    # webhook_count records every delivery (audit trail), not just first
    conn = payment_server._db()
    row = conn.execute(
        "SELECT webhook_count, status, scan_status FROM orders WHERE order_id = ?",
        ("ds_idem",),
    ).fetchone()
    conn.close()
    assert row["webhook_count"] == 3
    assert row["status"] == "paid"
    assert row["scan_status"] == "queued"


def test_payment_events_dedupes_repeated_actions(monkeypatch):
    """The (mollie_id, action) UNIQUE index prevents log bloat from webhook
    storms. Each distinct action is logged at most once even after dozens of
    redeliveries.
    """
    _prepare(monkeypatch)
    _insert_idem_order()

    fake_payments = FakePayments()
    fake_payments.get_responses["tr_idem_payment"] = PaidPayment()
    monkeypatch.setattr(payment_server, "_mollie", lambda: FakeMollie(fake_payments))
    monkeypatch.setattr(payment_server, "_queue_scan_order", lambda **kw: None)
    monkeypatch.setattr(payment_server, "_notify_admin", lambda **kw: None)

    client = _client()
    for _ in range(10):
        client.post("/api/payment/webhook", data={"id": "tr_idem_payment"})

    conn = payment_server._db()
    actions = [r["action"] for r in conn.execute(
        "SELECT action FROM payment_events ORDER BY id ASC"
    ).fetchall()]
    counts = {a: actions.count(a) for a in set(actions)}
    conn.close()

    # Each unique (mollie_id, action) tuple is logged exactly once.
    assert counts == {"paid_queueing": 1, "paid_queued": 1, "duplicate_paid_ignored": 1}
    # ...but webhook_count records the full storm.
    conn = payment_server._db()
    row = conn.execute(
        "SELECT webhook_count FROM orders WHERE order_id = ?", ("ds_idem",)
    ).fetchone()
    conn.close()
    assert row["webhook_count"] == 10


def test_refund_side_effect_runs_exactly_once(monkeypatch):
    """create_mollie_refund_for_order is the only outbound refund call.
    Two retries against an already-refunded order must NOT post a second
    refund to Mollie.
    """
    _prepare(monkeypatch)
    _insert_idem_order(status="paid", scan_status="queued", )

    refund_calls: list[dict] = []
    monkeypatch.setattr(
        payment_server,
        "_create_mollie_payment_refund",
        lambda payment_id, amount, currency, description, metadata: refund_calls.append(
            {"payment_id": payment_id, "amount": amount, "metadata": metadata}
        ) or {"id": "re_1", "status": "pending"},
    )

    first = payment_server.create_mollie_refund_for_order(
        "ds_idem", amount="79.00", note="idempotency test"
    )
    # Second call: order is now status=refunded, so the guard raises.
    with pytest.raises(ValueError, match="order_not_paid"):
        payment_server.create_mollie_refund_for_order("ds_idem", amount="79.00")

    # Exactly one outbound refund call
    assert len(refund_calls) == 1
    assert refund_calls[0]["payment_id"] == "tr_idem_payment"
    assert refund_calls[0]["metadata"]["order_id"] == "ds_idem"
    assert first["status"] == "refunded"
    assert first["refund_id"] == "re_1"
