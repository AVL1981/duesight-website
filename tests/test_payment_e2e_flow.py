import json
from pathlib import Path
from urllib.parse import urlparse

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import payment_server


TEST_DB = Path(__file__).with_name("_payment_e2e_orders.db")
SCAN_QUEUE_FILE = Path(__file__).with_name("_payment_e2e_scan_queue.jsonl")
SUPPORT_FILE = Path(__file__).with_name("_payment_e2e_support_events.jsonl")
DELIVERY_FILE = Path(__file__).with_name("_payment_e2e_delivery_events.jsonl")
EMAIL_FILE = Path(__file__).with_name("_payment_e2e_email_outbox.jsonl")
UPLOAD_DIR = Path(__file__).with_name("_payment_e2e_uploads")
REPORT_FILE = Path(__file__).with_name("_payment_e2e_report.html")


@pytest.fixture(autouse=True)
def clean_e2e_files():
    paths = [TEST_DB, SCAN_QUEUE_FILE, SUPPORT_FILE, DELIVERY_FILE, EMAIL_FILE, REPORT_FILE]
    for path in paths:
        if path.exists():
            path.unlink()
    if UPLOAD_DIR.exists():
        for path in sorted(UPLOAD_DIR.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            else:
                path.rmdir()
        UPLOAD_DIR.rmdir()
    yield
    for path in paths:
        if path.exists():
            path.unlink()
    if UPLOAD_DIR.exists():
        for path in sorted(UPLOAD_DIR.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            else:
                path.rmdir()
        UPLOAD_DIR.rmdir()


class CreatedPayment:
    id = "tr_e2e_payment"
    checkout_url = "https://checkout.mollie.test/e2e"


class PaidPayment:
    id = "tr_e2e_payment"
    status = "paid"
    amount = {"value": "79.00", "currency": "EUR"}

    def is_paid(self):
        return True


class FakePayments:
    def __init__(self, created_payloads):
        self.created_payloads = created_payloads
        self.idempotency_keys: list[str] = []

    def create(self, payment_data, idempotency_key="", **_kwargs):
        self.created_payloads.append(payment_data)
        self.idempotency_keys.append(idempotency_key)
        return CreatedPayment()

    def get(self, payment_id):
        assert payment_id == CreatedPayment.id
        return PaidPayment()


class FakeMollie:
    def __init__(self, created_payloads):
        self.payments = FakePayments(created_payloads)


def _client():
    app = FastAPI()
    app.include_router(payment_server.payment_router, prefix="/api/payment")
    return TestClient(app)


def _path_from_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.path}?{parsed.query}" if parsed.query else parsed.path


def _prepare(monkeypatch):
    monkeypatch.setattr(payment_server, "DB_PATH", TEST_DB)
    monkeypatch.setattr(payment_server, "SCAN_QUEUE_FILE", SCAN_QUEUE_FILE)
    monkeypatch.setattr(payment_server, "SUPPORT_EVENTS_FILE", SUPPORT_FILE)
    monkeypatch.setattr(payment_server, "DELIVERY_EVENTS_FILE", DELIVERY_FILE)
    monkeypatch.setattr(payment_server, "EMAIL_OUTBOX_FILE", EMAIL_FILE)
    monkeypatch.setattr(payment_server, "UPLOAD_DIR", UPLOAD_DIR)
    monkeypatch.setattr(payment_server, "BASE_URL", "https://duesight.test")
    monkeypatch.setenv("DUESIGHT_EMAIL_SEND_ENABLED", "false")
    payment_server._init_db()


def test_self_serve_payment_upload_delivery_email_flow(monkeypatch):
    _prepare(monkeypatch)
    created_payloads = []
    monkeypatch.setattr(payment_server, "_mollie", lambda: FakeMollie(created_payloads))
    client = _client()

    checkout = client.post(
        "/api/payment/create",
        json={
            "product": "compact",
            "company_name": "Mollie B.V.",
            "kvk_number": "56087887",
            "domain": "mollie.com",
            "customer_email": "finance@mollie.com",
            "terms_accepted": True,
        },
        headers={"user-agent": "DueSightE2E/1.0", "x-forwarded-for": "203.0.113.42"},
    )
    assert checkout.status_code == 200
    checkout_payload = checkout.json()
    order_id = checkout_payload["order_id"]
    payment_id = checkout_payload["payment_id"]
    assert checkout_payload["checkout_url"].startswith("https://checkout.mollie.test/")
    assert created_payloads[0]["metadata"]["order_id"] == order_id
    assert created_payloads[0]["metadata"]["terms_acceptance"]["accepted"] is True

    upload = client.post(
        f"/api/payment/orders/{order_id}/uploads",
        data={"customer_email": "finance@mollie.com"},
        files={"file": ("jaarrekening.pdf", b"%PDF-1.4\nminimal", "application/pdf")},
    )
    assert upload.status_code == 200
    upload_payload = upload.json()
    assert upload_payload["status"] == "uploaded"

    webhook = client.post("/api/payment/webhook", data={"id": payment_id})
    assert webhook.status_code == 200
    assert webhook.json()["status"] == "paid"
    assert webhook.json()["action"] == "queued"

    queued = [json.loads(line) for line in SCAN_QUEUE_FILE.read_text(encoding="utf-8").splitlines()]
    assert len(queued) == 1
    assert queued[0]["order_id"] == order_id
    assert queued[0]["company_name"] == "Mollie B.V."
    assert queued[0]["kvk_number"] == "56087887"
    assert queued[0]["domain"] == "mollie.com"
    assert queued[0]["email"] == "finance@mollie.com"
    assert len(queued[0]["uploads"]) == 1
    queued_upload = queued[0]["uploads"][0]
    assert queued_upload["original_filename"] == "jaarrekening.pdf"
    assert queued_upload["sha256"] == upload_payload["sha256"]
    assert Path(queued_upload["stored_path"]).exists()

    REPORT_FILE.write_text("<html><body>DueSight e2e report</body></html>", encoding="utf-8")

    def e2e_report_runner(order):
        assert order["uploads"][0]["original_filename"] == "jaarrekening.pdf"
        assert order["uploads"][0]["sha256"] == upload_payload["sha256"]
        return {"report_path": str(REPORT_FILE)}

    delivery = payment_server.run_delivery_for_order(
        order_id,
        report_runner=e2e_report_runner,
        send_email=True,
    )
    assert delivery["status"] == "completed"
    assert delivery["delivery_status"] == "ready"
    assert delivery["email_status"] == "outbox_only"

    missing_status_email = client.get(f"/api/payment/status/{order_id}")
    wrong_status_email = client.get(
        f"/api/payment/status/{order_id}",
        params={"customer_email": "other@example.test"},
    )
    status = client.get(
        f"/api/payment/status/{order_id}",
        params={"customer_email": "finance@mollie.com"},
    )
    assert missing_status_email.status_code == 403
    assert wrong_status_email.status_code == 403
    assert status.status_code == 200
    assert status.json() == {
        "order_id": order_id,
        "status": "paid",
        "scan_status": "delivered",
        "delivery_status": "ready",
        "upload_status": "uploaded",
    }

    delivery_link = client.get(_path_from_url(delivery["delivery_url"]))
    assert delivery_link.status_code == 200
    assert delivery_link.json()["delivery_status"] == "ready"

    report_file = client.get(_path_from_url(delivery["report_url"]))
    assert report_file.status_code == 200
    assert b"DueSight e2e report" in report_file.content

    outbox = [json.loads(line) for line in EMAIL_FILE.read_text(encoding="utf-8").splitlines()]
    assert len(outbox) == 1
    assert outbox[0]["status"] == "outbox_only"
    assert outbox[0]["order_id"] == order_id
    assert outbox[0]["email"] == "finance@mollie.com"
    assert outbox[0]["delivery_url"] == delivery["delivery_url"]
    assert payment_id not in EMAIL_FILE.read_text(encoding="utf-8")

    uploads = client.get(f"/api/payment/orders/{order_id}/uploads", params={"customer_email": "finance@mollie.com"})
    assert uploads.status_code == 200
    assert uploads.json()["uploads"][0]["original_filename"] == "jaarrekening.pdf"

    conn = payment_server._db()
    actions = {
        row["action"]
        for row in conn.execute("SELECT action FROM payment_events WHERE order_id = ?", (order_id,)).fetchall()
    }
    row = conn.execute(
        """SELECT status, scan_status, delivery_status, upload_status, report_path, terms_acceptance_hash
           FROM orders WHERE order_id = ?""",
        (order_id,),
    ).fetchone()
    conn.close()

    assert {
        "checkout_created",
        "customer_upload_received",
        "paid_queueing",
        "paid_queued",
        "delivery_worker_started",
        "delivery_ready",
        "delivery_worker_completed",
    }.issubset(actions)
    assert row["status"] == "paid"
    assert row["scan_status"] == "delivered"
    assert row["delivery_status"] == "ready"
    assert row["upload_status"] == "uploaded"
    assert row["report_path"] == str(REPORT_FILE.resolve())
    assert len(row["terms_acceptance_hash"]) == 64
