import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import payment_server


ROOT = Path(__file__).resolve().parents[1]
TEST_DB = Path(__file__).with_name("_delivery_flow_test_orders.db")
DELIVERY_FILE = Path(__file__).with_name("_delivery_events.jsonl")
EMAIL_FILE = Path(__file__).with_name("_delivery_email_outbox.jsonl")
REPORT_FILE = Path(__file__).with_name("_worker_report.html")
READINESS_SCRIPT = ROOT / "scripts" / "payment_live_readiness.ps1"
ADMIN_HEADERS = {"X-DueSight-Admin-Secret": "unit-admin-secret"}


@pytest.fixture(autouse=True)
def clean_delivery_test_files():
    for path in (TEST_DB, DELIVERY_FILE, EMAIL_FILE, REPORT_FILE):
        if path.exists():
            path.unlink()
    yield
    for path in (TEST_DB, DELIVERY_FILE, EMAIL_FILE, REPORT_FILE):
        if path.exists():
            path.unlink()


def _client():
    app = FastAPI()
    app.include_router(payment_server.payment_router, prefix="/api/payment")
    return TestClient(app)


def _prepare(monkeypatch):
    monkeypatch.setattr(payment_server, "DB_PATH", TEST_DB)
    monkeypatch.setattr(payment_server, "DELIVERY_EVENTS_FILE", DELIVERY_FILE)
    monkeypatch.setattr(payment_server, "EMAIL_OUTBOX_FILE", EMAIL_FILE)
    monkeypatch.setattr(payment_server, "BASE_URL", "https://duesight.test")
    monkeypatch.setenv("DUESIGHT_PAYMENT_ADMIN_SECRET", "unit-admin-secret")
    payment_server._init_db()


def _insert_paid_order():
    conn = payment_server._db()
    conn.execute(
        """INSERT INTO orders
           (order_id, mollie_id, product, company_name, customer_email, amount,
            currency, status, scan_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "ds_delivery",
            "tr_delivery",
            "predd",
            "Mollie B.V.",
            "finance@mollie.com",
            "399.00",
            "EUR",
            "paid",
            "queued",
        ),
    )
    conn.commit()
    conn.close()


def test_admin_delivery_complete_creates_tokenized_link(monkeypatch):
    _prepare(monkeypatch)
    _insert_paid_order()

    response = _client().post(
        "/api/payment/delivery/complete",
        headers=ADMIN_HEADERS,
        json={
            "order_id": "ds_delivery",
            "report_url": "https://duesight.test/reports/ds_delivery.pdf",
            "send_email": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["delivery_url"].startswith("https://duesight.test/api/payment/delivery-link/ds_delivery?token=")

    parsed = urlparse(payload["delivery_url"])
    token = parse_qs(parsed.query)["token"][0]
    assert len(token) > 20

    conn = payment_server._db()
    row = conn.execute(
        """SELECT report_url, scan_status, delivery_status, delivery_token_hash,
                  delivery_email, delivery_created_at
           FROM orders WHERE order_id = ?""",
        ("ds_delivery",),
    ).fetchone()
    event = conn.execute("SELECT action FROM payment_events").fetchone()
    conn.close()

    assert row["report_url"] == "https://duesight.test/reports/ds_delivery.pdf"
    assert row["scan_status"] == "delivered"
    assert row["delivery_status"] == "ready"
    assert len(row["delivery_token_hash"]) == 64
    assert row["delivery_email"] == "finance@mollie.com"
    assert row["delivery_created_at"]
    assert event["action"] == "delivery_ready"

    delivery_event = json.loads(DELIVERY_FILE.read_text(encoding="utf-8").strip())
    assert delivery_event["type"] == "delivery_ready"
    assert delivery_event["order_id"] == "ds_delivery"


def test_admin_delivery_complete_requires_secret(monkeypatch):
    _prepare(monkeypatch)
    _insert_paid_order()
    client = _client()

    missing = client.post(
        "/api/payment/delivery/complete",
        json={"order_id": "ds_delivery", "report_url": "https://duesight.test/reports/ds_delivery.pdf"},
    )
    wrong = client.post(
        "/api/payment/delivery/complete",
        headers={"X-DueSight-Admin-Secret": "wrong"},
        json={"order_id": "ds_delivery", "report_url": "https://duesight.test/reports/ds_delivery.pdf"},
    )

    assert missing.status_code == 403
    assert wrong.status_code == 403
    assert missing.json()["detail"] == "payment admin secret required"


def test_admin_delivery_process_requires_secret(monkeypatch):
    _prepare(monkeypatch)
    _insert_paid_order()
    client = _client()

    assert client.post("/api/payment/delivery/process/ds_delivery").status_code == 403


def test_admin_delivery_endpoint_reports_missing_secret_config(monkeypatch):
    _prepare(monkeypatch)
    _insert_paid_order()
    monkeypatch.delenv("DUESIGHT_PAYMENT_ADMIN_SECRET", raising=False)

    response = _client().post(
        "/api/payment/delivery/complete",
        json={"order_id": "ds_delivery", "report_url": "https://duesight.test/reports/ds_delivery.pdf"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "payment admin secret not configured"


def test_customer_delivery_link_requires_valid_token(monkeypatch):
    _prepare(monkeypatch)
    _insert_paid_order()
    client = _client()

    created = client.post(
        "/api/payment/delivery/complete",
        headers=ADMIN_HEADERS,
        json={"order_id": "ds_delivery", "report_url": "https://duesight.test/reports/ds_delivery.pdf"},
    )
    token = parse_qs(urlparse(created.json()["delivery_url"]).query)["token"][0]

    bad = client.get("/api/payment/delivery-link/ds_delivery?token=wrong")
    good = client.get(f"/api/payment/delivery-link/ds_delivery?token={token}")

    assert bad.status_code == 403
    assert good.status_code == 200
    assert good.json()["report_url"] == "https://duesight.test/reports/ds_delivery.pdf"
    assert good.json()["delivery_status"] == "ready"


def test_delivery_can_write_safe_email_outbox(monkeypatch):
    _prepare(monkeypatch)
    _insert_paid_order()

    response = _client().post(
        "/api/payment/delivery/complete",
        headers=ADMIN_HEADERS,
        json={
            "order_id": "ds_delivery",
            "report_url": "https://duesight.test/reports/ds_delivery.pdf",
            "send_email": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["email_status"] == "outbox_only"

    outbox = json.loads(EMAIL_FILE.read_text(encoding="utf-8").strip())
    assert outbox["type"] == "delivery_email_outbox"
    assert outbox["order_id"] == "ds_delivery"
    assert outbox["email"] == "finance@mollie.com"
    assert outbox["delivery_url"].startswith("https://duesight.test/api/payment/delivery-link/ds_delivery?token=")


def test_delivery_can_send_via_configured_smtp(monkeypatch):
    _prepare(monkeypatch)
    _insert_paid_order()
    sent = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            self.host = host
            self.port = port
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self):
            sent.append(("starttls", self.host, self.port, self.timeout))

        def login(self, user, password):
            sent.append(("login", user, password))

        def send_message(self, message):
            sent.append(("send", message["To"], message["Subject"], message.get_content()))

    monkeypatch.setenv("DUESIGHT_EMAIL_SEND_ENABLED", "true")
    monkeypatch.setenv("SMTP_HOST", "smtp.test.local")
    monkeypatch.setenv("SMTP_PORT", "2525")
    monkeypatch.setenv("SMTP_USER", "docs@duesight.test")
    monkeypatch.setenv("SMTP_PASS", "unit-test-password")
    monkeypatch.setenv("SMTP_FROM", "docs@duesight.test")
    monkeypatch.setenv("SMTP_FROM_NAME", "DueSight Test")
    monkeypatch.setattr(payment_server.smtplib, "SMTP", FakeSMTP)

    response = _client().post(
        "/api/payment/delivery/complete",
        headers=ADMIN_HEADERS,
        json={
            "order_id": "ds_delivery",
            "report_url": "https://duesight.test/reports/ds_delivery.pdf",
            "send_email": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["email_status"] == "smtp_sent"
    assert sent[0] == ("starttls", "smtp.test.local", 2525, 20)
    assert sent[1] == ("login", "docs@duesight.test", "unit-test-password")
    assert sent[2][0] == "send"
    assert sent[2][1] == "finance@mollie.com"
    assert "https://duesight.test/api/payment/delivery-link/ds_delivery?token=" in sent[2][3]

    outbox = json.loads(EMAIL_FILE.read_text(encoding="utf-8").strip())
    assert outbox["status"] == "smtp_sent"


def test_email_smoke_can_send_via_configured_smtp(monkeypatch):
    _prepare(monkeypatch)
    sent = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            self.host = host
            self.port = port
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self):
            sent.append(("starttls", self.host, self.port, self.timeout))

        def login(self, user, password):
            sent.append(("login", user, password))

        def send_message(self, message):
            sent.append(("send", message["To"], message["Subject"], message.get_content()))

    monkeypatch.setenv("DUESIGHT_EMAIL_SEND_ENABLED", "true")
    monkeypatch.setenv("SMTP_HOST", "smtp.test.local")
    monkeypatch.setenv("SMTP_PORT", "2525")
    monkeypatch.setenv("SMTP_USER", "docs@duesight.test")
    monkeypatch.setenv("SMTP_PASS", "unit-test-password")
    monkeypatch.setenv("SMTP_FROM", "docs@duesight.test")
    monkeypatch.setattr(payment_server.smtplib, "SMTP", FakeSMTP)

    result = payment_server.run_email_smoke("controlled@example.test", allow_send=True)

    assert result["status"] == "smtp_sent"
    assert result["smtp_attempted"] is True
    assert result["recipient_present"] is True
    assert sent[0] == ("starttls", "smtp.test.local", 2525, 20)
    assert sent[1] == ("login", "docs@duesight.test", "unit-test-password")
    assert sent[2][0] == "send"
    assert sent[2][1] == "controlled@example.test"

    outbox = json.loads(EMAIL_FILE.read_text(encoding="utf-8").strip())
    assert outbox["type"] == "email_smoke"
    assert outbox["status"] == "smtp_sent"


def test_email_smoke_cli_defaults_to_outbox_and_is_redacted(tmp_path):
    email_file = tmp_path / "email_outbox.jsonl"
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(ROOT),
            "PYTHONDONTWRITEBYTECODE": "1",
            "DUESIGHT_EMAIL_OUTBOX_FILE": str(email_file),
            "DUESIGHT_EMAIL_SEND_ENABLED": "true",
            "SMTP_HOST": "smtp.test.local",
            "SMTP_USER": "docs@duesight.test",
            "SMTP_PASS": "smtp_unit_should_not_print",
        }
    )

    result = subprocess.run(
        [sys.executable, str(ROOT / "payment_server.py"), "email-smoke", "--to", "controlled@example.test"],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 0, result.stderr
    assert "smtp_unit_should_not_print" not in combined
    assert "controlled@example.test" not in combined
    payload = json.loads(result.stdout)
    assert payload["status"] == "outbox_only"
    assert payload["smtp_attempted"] is False
    assert payload["recipient_present"] is True

    outbox = json.loads(email_file.read_text(encoding="utf-8").strip())
    assert outbox["type"] == "email_smoke"
    assert outbox["email"] == "controlled@example.test"
    assert outbox["status"] == "outbox_only"


def test_email_smoke_cli_allow_send_requires_success(tmp_path):
    email_file = tmp_path / "email_outbox.jsonl"
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(ROOT),
            "PYTHONDONTWRITEBYTECODE": "1",
            "DUESIGHT_EMAIL_OUTBOX_FILE": str(email_file),
            "DUESIGHT_EMAIL_SEND_ENABLED": "false",
            "SMTP_PASS": "smtp_unit_should_not_print",
        }
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "payment_server.py"),
            "email-smoke",
            "--to",
            "controlled@example.test",
            "--allow-send",
        ],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 2
    assert "smtp_unit_should_not_print" not in result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "outbox_only"
    assert payload["smtp_attempted"] is True


def test_delivery_worker_completes_queued_order_with_protected_report(monkeypatch):
    _prepare(monkeypatch)
    _insert_paid_order()
    REPORT_FILE.write_text("<html><body>DueSight report ready</body></html>", encoding="utf-8")

    def fake_runner(order):
        assert order["order_id"] == "ds_delivery"
        assert order["customer_email"] == "finance@mollie.com"
        return {"report_path": str(REPORT_FILE)}

    result = payment_server.run_delivery_for_order("ds_delivery", report_runner=fake_runner, send_email=True)

    assert result["status"] == "completed"
    assert result["email_status"] == "outbox_only"
    assert result["report_url"].startswith("https://duesight.test/api/payment/report-file/ds_delivery?token=")

    delivery_token = parse_qs(urlparse(result["delivery_url"]).query)["token"][0]
    report_token = parse_qs(urlparse(result["report_url"]).query)["token"][0]
    assert delivery_token == report_token

    client = _client()
    bad = client.get("/api/payment/report-file/ds_delivery?token=bad")
    good = client.get(f"/api/payment/report-file/ds_delivery?token={report_token}")

    assert bad.status_code == 403
    assert good.status_code == 200
    assert b"DueSight report ready" in good.content

    conn = payment_server._db()
    row = conn.execute(
        "SELECT scan_status, delivery_status, report_path, report_url FROM orders WHERE order_id = ?",
        ("ds_delivery",),
    ).fetchone()
    events = conn.execute("SELECT action, details FROM payment_events ORDER BY id").fetchall()
    actions = [r["action"] for r in events]
    conn.close()
    event_details = json.dumps([json.loads(r["details"]) for r in events], ensure_ascii=True)
    delivery_events = DELIVERY_FILE.read_text(encoding="utf-8")
    email_outbox = EMAIL_FILE.read_text(encoding="utf-8")

    assert row["scan_status"] == "delivered"
    assert row["delivery_status"] == "ready"
    assert row["report_path"] == str(REPORT_FILE.resolve())
    assert row["report_url"] == result["report_url"]
    assert actions == ["delivery_worker_started", "delivery_ready", "delivery_worker_completed"]
    assert report_token in email_outbox
    assert report_token not in event_details
    assert report_token not in delivery_events
    assert "token=[redacted]" in event_details
    assert "token=[redacted]" in delivery_events


def test_delivery_queue_processes_paid_queued_orders(monkeypatch):
    _prepare(monkeypatch)
    _insert_paid_order()
    REPORT_FILE.write_text("<html><body>Queued report ready</body></html>", encoding="utf-8")

    results = payment_server.process_delivery_queue(
        report_runner=lambda order: {"report_path": str(REPORT_FILE)},
        send_email=False,
    )

    assert len(results) == 1
    assert results[0]["status"] == "completed"

    conn = payment_server._db()
    row = conn.execute(
        "SELECT scan_status, delivery_status FROM orders WHERE order_id = ?",
        ("ds_delivery",),
    ).fetchone()
    conn.close()

    assert row["scan_status"] == "delivered"
    assert row["delivery_status"] == "ready"


def test_agent_report_runner_exports_order_uploads(monkeypatch, tmp_path):
    agent_dir = tmp_path / "duesight-agent"
    delivery_dir = agent_dir / "delivery"
    delivery_dir.mkdir(parents=True)
    (agent_dir / "deliver_report.py").write_text("# test stub\n", encoding="utf-8")
    report = delivery_dir / "rapport_mollie-com_20260607.html"
    report.write_text("<html><body>Agent report</body></html>", encoding="utf-8")
    captured = {}

    def fake_run(cmd, cwd, env, capture_output, text, timeout):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        captured["env"] = env
        captured["timeout"] = timeout
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setenv("DUESIGHT_AGENT_DIR", str(agent_dir))
    monkeypatch.setattr(payment_server.subprocess, "run", fake_run)

    result = payment_server._run_agent_report(
        {
            "order_id": "ds_delivery",
            "product": "compact",
            "company_name": "Mollie B.V.",
            "domain": "mollie.com",
            "customer_email": "finance@mollie.com",
            "uploads": [
                {
                    "upload_id": "up_test",
                    "original_filename": "jaarrekening.pdf",
                    "stored_path": str(tmp_path / "jaarrekening.pdf"),
                    "sha256": "a" * 64,
                }
            ],
        }
    )

    assert result == {"report_path": str(report)}
    assert captured["cwd"] == str(agent_dir)
    assert "--company" in captured["cmd"]
    assert captured["cmd"][captured["cmd"].index("--tier") + 1] == "quick_scan"
    uploads = json.loads(captured["env"]["DUESIGHT_ORDER_UPLOADS_JSON"])
    assert uploads[0]["original_filename"] == "jaarrekening.pdf"
    assert uploads[0]["sha256"] == "a" * 64


def test_agent_report_runner_rejects_monitoring_without_subprocess(monkeypatch, tmp_path):
    agent_dir = tmp_path / "duesight-agent"
    agent_dir.mkdir(parents=True)
    (agent_dir / "deliver_report.py").write_text("# test stub\n", encoding="utf-8")

    def fail_run(*_args, **_kwargs):
        pytest.fail("monitoring order should not start deliver_report.py")

    monkeypatch.setenv("DUESIGHT_AGENT_DIR", str(agent_dir))
    monkeypatch.setattr(payment_server.subprocess, "run", fail_run)

    with pytest.raises(ValueError, match="product_not_report_deliverable:monitoring"):
        payment_server._run_agent_report(
            {
                "order_id": "ds_monitoring",
                "product": "monitoring",
                "company_name": "Mollie B.V.",
                "domain": "mollie.com",
                "customer_email": "finance@mollie.com",
            }
        )


def test_delivery_queue_skips_non_report_monitoring_orders(monkeypatch):
    _prepare(monkeypatch)
    conn = payment_server._db()
    conn.execute(
        """INSERT INTO orders
           (order_id, mollie_id, product, company_name, customer_email, amount,
            currency, status, scan_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "ds_monitoring",
            "tr_monitoring",
            "monitoring",
            "Mollie B.V.",
            "finance@mollie.com",
            "19.00",
            "EUR",
            "paid",
            "queued",
        ),
    )
    conn.commit()
    conn.close()

    def fail_runner(order):
        pytest.fail(f"monitoring order reached report runner: {order['order_id']}")

    assert payment_server.process_delivery_queue(report_runner=fail_runner, send_email=False) == []


def test_smoke_config_delivery_queue_counts_only_report_products(monkeypatch):
    _prepare(monkeypatch)
    conn = payment_server._db()
    conn.executemany(
        """INSERT INTO orders
           (order_id, mollie_id, product, company_name, customer_email, amount,
            currency, status, scan_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                "ds_compact",
                "tr_compact",
                "compact",
                "Mollie B.V.",
                "finance@mollie.com",
                "79.00",
                "EUR",
                "paid",
                "queued",
            ),
            (
                "ds_monitoring",
                "tr_monitoring",
                "monitoring",
                "Mollie B.V.",
                "finance@mollie.com",
                "19.00",
                "EUR",
                "paid",
                "queued",
            ),
        ],
    )
    conn.commit()
    conn.close()

    status = payment_server.smoke_config_status()

    assert status["orders_total"] == 2
    assert status["paid_orders"] == 2
    assert status["delivery_queue"] == 1


def test_worker_once_cli_processes_isolated_queue(tmp_path):
    db_path = tmp_path / "orders.db"
    delivery_file = tmp_path / "delivery_events.jsonl"
    email_file = tmp_path / "email_outbox.jsonl"
    report_file = tmp_path / "report.html"
    report_file.write_text("<html><body>CLI report ready</body></html>", encoding="utf-8")

    old_db = payment_server.DB_PATH
    old_delivery = payment_server.DELIVERY_EVENTS_FILE
    old_email = payment_server.EMAIL_OUTBOX_FILE
    old_base = payment_server.BASE_URL
    try:
        payment_server.DB_PATH = db_path
        payment_server.DELIVERY_EVENTS_FILE = delivery_file
        payment_server.EMAIL_OUTBOX_FILE = email_file
        payment_server.BASE_URL = "https://duesight.test"
        payment_server._init_db()
        conn = payment_server._db()
        conn.execute(
            """INSERT INTO orders
               (order_id, mollie_id, product, company_name, customer_email, amount,
                currency, status, scan_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "ds_cli",
                "tr_cli",
                "predd",
                "Mollie B.V.",
                "finance@mollie.com",
                "399.00",
                "EUR",
                "paid",
                "queued",
            ),
        )
        conn.commit()
        conn.close()
    finally:
        payment_server.DB_PATH = old_db
        payment_server.DELIVERY_EVENTS_FILE = old_delivery
        payment_server.EMAIL_OUTBOX_FILE = old_email
        payment_server.BASE_URL = old_base

    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(ROOT),
            "PYTHONDONTWRITEBYTECODE": "1",
            "DUESIGHT_PAYMENT_DB_PATH": str(db_path),
            "DUESIGHT_DELIVERY_EVENTS_FILE": str(delivery_file),
            "DUESIGHT_EMAIL_OUTBOX_FILE": str(email_file),
            "DUESIGHT_BASE_URL": "https://duesight.test",
        }
    )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "payment_server.py"),
            "worker-once",
            "--limit",
            "1",
            "--report-path",
            str(report_file),
            "--no-email",
        ],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["processed"][0]["status"] == "completed"

    old_db = payment_server.DB_PATH
    try:
        payment_server.DB_PATH = db_path
        conn = payment_server._db()
        row = conn.execute(
            "SELECT scan_status, delivery_status, report_path FROM orders WHERE order_id = ?",
            ("ds_cli",),
        ).fetchone()
        conn.close()
    finally:
        payment_server.DB_PATH = old_db

    assert row["scan_status"] == "delivered"
    assert row["delivery_status"] == "ready"
    assert row["report_path"] == str(report_file.resolve())
    assert not email_file.exists()


def test_smoke_config_cli_is_redacted(tmp_path):
    db_path = tmp_path / "orders.db"
    email_file = tmp_path / "email_outbox.jsonl"
    upload_dir = tmp_path / "uploads"
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(ROOT),
            "PYTHONDONTWRITEBYTECODE": "1",
            "DUESIGHT_PAYMENT_DB_PATH": str(db_path),
            "DUESIGHT_EMAIL_OUTBOX_FILE": str(email_file),
            "DUESIGHT_UPLOAD_DIR": str(upload_dir),
            "MOLLIE_API_KEY": "test_unit_should_not_print",
            "DUESIGHT_PAYMENT_ADMIN_SECRET": "admin_unit_should_not_print",
            "SMTP_PASS": "smtp_unit_should_not_print",
            "SMTP_HOST": "smtp.test.local",
            "SMTP_USER": "docs@duesight.test",
            "DUESIGHT_EMAIL_SEND_ENABLED": "true",
        }
    )

    result = subprocess.run(
        [sys.executable, str(ROOT / "payment_server.py"), "smoke-config"],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "test_unit_should_not_print" not in result.stdout
    assert "admin_unit_should_not_print" not in result.stdout
    assert "smtp_unit_should_not_print" not in result.stdout
    payload = json.loads(result.stdout)
    assert payload["mollie_api_key_present"] is True
    assert payload["payment_admin_secret_present"] is True
    assert payload["smtp_will_send"] is True
    assert payload["payment_db_configured"] == str(db_path)


def test_live_readiness_reports_launch_blockers(monkeypatch):
    _prepare(monkeypatch)
    monkeypatch.setenv("MOLLIE_API_KEY", "test_unit_should_not_print")
    monkeypatch.setenv("DUESIGHT_EMAIL_SEND_ENABLED", "false")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASS", raising=False)
    monkeypatch.setattr(
        payment_server,
        "_tls_probe",
        lambda url: {
            "host": "duesight.test",
            "scheme": "https",
            "tls_valid": False,
            "error": "certificate_hostname_mismatch",
        },
    )
    monkeypatch.setattr(
        payment_server,
        "_payment_service_probe",
        lambda url: {
            "service_ready": False,
            "health": {"path": "/health", "status_code": 404, "json_ok": False, "error": ""},
            "products": {"path": "/api/payment/products", "status_code": 404, "json_ok": False, "error": ""},
        },
    )
    monkeypatch.setattr(
        payment_server,
        "_pm2_process_status",
        lambda: {
            "available": False,
            "required": ["duesight-payment", "duesight-delivery-worker"],
            "processes": {},
            "missing": ["duesight-payment", "duesight-delivery-worker"],
            "not_online": [],
            "error": "pm2_missing",
        },
    )

    payload = payment_server.live_readiness_status()

    assert payload["ready"] is False
    assert payload["status"] == "blocked"
    assert payload["mollie_key_mode"] == "test"
    assert payload["payment_admin_secret_present"] is True
    assert "base_url_tls_invalid" in payload["blockers"]
    assert "webhook_tls_invalid" in payload["blockers"]
    assert "payment_service_unreachable" in payload["blockers"]
    assert "local_payment_service_unreachable" in payload["blockers"]
    assert "smtp_not_ready" in payload["blockers"]
    assert "pm2_missing" in payload["blockers"]
    assert payload["tls"]["base_url"]["error"] == "certificate_hostname_mismatch"
    assert payload["payment_service"]["health"]["status_code"] == 404
    assert payload["pm2"]["missing"] == ["duesight-payment", "duesight-delivery-worker"]


def test_live_readiness_reports_pm2_process_blocker(monkeypatch):
    _prepare(monkeypatch)
    monkeypatch.setenv("MOLLIE_API_KEY", "test_unit_should_not_print")
    monkeypatch.setenv("DUESIGHT_EMAIL_SEND_ENABLED", "true")
    monkeypatch.setenv("SMTP_HOST", "smtp.test.local")
    monkeypatch.setenv("SMTP_USER", "docs@duesight.test")
    monkeypatch.setenv("SMTP_PASS", "smtp_unit_should_not_print")
    monkeypatch.setattr(
        payment_server,
        "_tls_probe",
        lambda url: {"host": "duesight.test", "scheme": "https", "tls_valid": True, "error": ""},
    )
    monkeypatch.setattr(
        payment_server,
        "_payment_service_probe",
        lambda url: {"service_ready": True, "health": {"status_code": 200}, "products": {"status_code": 200}},
    )
    monkeypatch.setattr(
        payment_server,
        "_pm2_process_status",
        lambda: {
            "available": True,
            "required": ["duesight-payment", "duesight-delivery-worker"],
            "processes": {"duesight-payment": {"status": "stopped", "online": False}},
            "missing": ["duesight-delivery-worker"],
            "not_online": ["duesight-payment"],
            "error": "",
        },
    )

    payload = payment_server.live_readiness_status()

    assert payload["ready"] is False
    assert payload["blockers"] == ["pm2_processes_not_online"]
    assert payload["pm2_available"] is True
    assert payload["pm2"]["missing"] == ["duesight-delivery-worker"]
    assert payload["pm2"]["not_online"] == ["duesight-payment"]


def test_live_readiness_can_skip_local_payment_service(monkeypatch):
    _prepare(monkeypatch)
    monkeypatch.setenv("MOLLIE_API_KEY", "test_unit_should_not_print")
    monkeypatch.setenv("DUESIGHT_EMAIL_SEND_ENABLED", "true")
    monkeypatch.setenv("SMTP_HOST", "smtp.test.local")
    monkeypatch.setenv("SMTP_USER", "docs@duesight.test")
    monkeypatch.setenv("SMTP_PASS", "smtp_unit_should_not_print")
    monkeypatch.setattr(payment_server, "_payment_service_probe", lambda url: {"service_ready": False})
    monkeypatch.setattr(
        payment_server,
        "_pm2_process_status",
        lambda: {
            "available": True,
            "required": ["duesight-payment", "duesight-delivery-worker"],
            "processes": {
                "duesight-payment": {"status": "online", "online": True},
                "duesight-delivery-worker": {"status": "online", "online": True},
            },
            "missing": [],
            "not_online": [],
            "error": "",
        },
    )

    payload = payment_server.live_readiness_status(check_network=False, check_local_service=False)

    assert payload["ready"] is True
    assert payload["local_payment_service"]["skipped"] is True


def test_live_readiness_requires_payment_admin_secret(monkeypatch):
    _prepare(monkeypatch)
    monkeypatch.delenv("DUESIGHT_PAYMENT_ADMIN_SECRET", raising=False)
    monkeypatch.setenv("MOLLIE_API_KEY", "test_unit_should_not_print")
    monkeypatch.setenv("DUESIGHT_EMAIL_SEND_ENABLED", "true")
    monkeypatch.setenv("SMTP_HOST", "smtp.test.local")
    monkeypatch.setenv("SMTP_USER", "docs@duesight.test")
    monkeypatch.setenv("SMTP_PASS", "smtp_unit_should_not_print")
    monkeypatch.setattr(payment_server, "_payment_service_probe", lambda url: {"service_ready": True})
    monkeypatch.setattr(
        payment_server,
        "_pm2_process_status",
        lambda: {
            "available": True,
            "required": ["duesight-payment", "duesight-delivery-worker"],
            "processes": {
                "duesight-payment": {"status": "online", "online": True},
                "duesight-delivery-worker": {"status": "online", "online": True},
            },
            "missing": [],
            "not_online": [],
            "error": "",
        },
    )

    payload = payment_server.live_readiness_status(check_network=False, check_local_service=False)

    assert payload["ready"] is False
    assert payload["payment_admin_secret_present"] is False
    assert payload["blockers"] == ["payment_admin_secret_missing"]


def test_pm2_process_status_parses_jlist(monkeypatch):
    class Completed:
        returncode = 0
        stdout = json.dumps(
            [
                {"name": "duesight-payment", "pm2_env": {"status": "online"}},
                {"name": "duesight-delivery-worker", "pm2_env": {"status": "stopped"}},
                {"name": "unrelated", "pm2_env": {"status": "online"}},
            ]
        )

    monkeypatch.setattr(payment_server, "_pm2_executable", lambda: "pm2")
    monkeypatch.setattr(payment_server.subprocess, "run", lambda *args, **kwargs: Completed())

    payload = payment_server._pm2_process_status()

    assert payload["available"] is True
    assert payload["missing"] == []
    assert payload["not_online"] == ["duesight-delivery-worker"]
    assert payload["processes"]["duesight-payment"]["online"] is True
    assert payload["processes"]["duesight-delivery-worker"]["status"] == "stopped"


def test_readiness_check_cli_is_redacted(tmp_path):
    db_path = tmp_path / "orders.db"
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(ROOT),
            "PYTHONDONTWRITEBYTECODE": "1",
            "DUESIGHT_PAYMENT_DB_PATH": str(db_path),
            "MOLLIE_API_KEY": "test_unit_should_not_print",
            "SMTP_PASS": "smtp_unit_should_not_print",
            "SMTP_HOST": "smtp.test.local",
            "SMTP_USER": "docs@duesight.test",
            "DUESIGHT_EMAIL_SEND_ENABLED": "true",
        }
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "payment_server.py"),
            "readiness-check",
            "--skip-network",
            "--skip-pm2",
            "--skip-local-service",
        ],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    combined = result.stdout + result.stderr
    assert "test_unit_should_not_print" not in combined
    assert "smtp_unit_should_not_print" not in combined
    payload = json.loads(result.stdout)
    assert payload["mollie_key_mode"] == "test"
    assert payload["smtp_will_send"] is True
    assert payload["tls"]["base_url"]["skipped"] is True
    assert payload["payment_service"]["skipped"] is True
    assert payload["local_payment_service"]["skipped"] is True
    assert payload["pm2_available"] is None
    assert payload["pm2"]["skipped"] is True


def test_readiness_check_cli_can_fail_on_blocked(tmp_path):
    db_path = tmp_path / "orders.db"
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(ROOT),
            "PYTHONDONTWRITEBYTECODE": "1",
            "DUESIGHT_PAYMENT_DB_PATH": str(db_path),
            "MOLLIE_API_KEY": "test_unit_should_not_print",
            "DUESIGHT_PAYMENT_ADMIN_SECRET": "admin_unit_should_not_print",
            "DUESIGHT_EMAIL_SEND_ENABLED": "false",
        }
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "payment_server.py"),
            "readiness-check",
            "--skip-network",
            "--skip-pm2",
            "--skip-local-service",
            "--fail-on-blocked",
        ],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 3
    assert "test_unit_should_not_print" not in result.stdout + result.stderr
    assert "admin_unit_should_not_print" not in result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["ready"] is False
    assert payload["blockers"] == ["smtp_not_ready"]


def test_payment_live_readiness_script_uses_redacted_commands():
    script = READINESS_SCRIPT.read_text(encoding="utf-8")

    assert "readiness-check" in script
    assert "--fail-on-blocked" in script
    assert "--skip-local-service" in script
    assert "smoke-config" in script
    assert "payment_server.py" in script
    assert "Get-Content" not in script
    assert "MOLLIE_API_KEY" not in script
    assert "SMTP_PASS" not in script
    assert ".env" not in script


def test_payment_live_readiness_script_can_require_ready(tmp_path):
    db_path = tmp_path / "orders.db"
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(ROOT),
            "PYTHONDONTWRITEBYTECODE": "1",
            "DUESIGHT_PAYMENT_DB_PATH": str(db_path),
            "MOLLIE_API_KEY": "test_unit_should_not_print",
            "DUESIGHT_PAYMENT_ADMIN_SECRET": "admin_unit_should_not_print",
            "DUESIGHT_EMAIL_SEND_ENABLED": "false",
        }
    )

    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(READINESS_SCRIPT),
            "-SkipNetwork",
            "-SkipPm2",
            "-SkipLocalService",
            "-RequireReady",
        ],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )

    assert result.returncode == 3
    assert "test_unit_should_not_print" not in result.stdout + result.stderr
    assert "admin_unit_should_not_print" not in result.stdout + result.stderr
    assert "smtp_not_ready" in result.stdout


def test_webhook_replay_cli_redacts_payment_id(tmp_path):
    db_path = tmp_path / "orders.db"
    fake_pkg = tmp_path / "mollie" / "api"
    fake_pkg.mkdir(parents=True)
    (tmp_path / "mollie" / "__init__.py").write_text("", encoding="utf-8")
    (fake_pkg / "__init__.py").write_text("", encoding="utf-8")
    (fake_pkg / "client.py").write_text(
        """
class FakePayment:
    id = "tr_cli_secret"
    status = "paid"
    amount = {"value": "79.00", "currency": "EUR"}

    def is_paid(self):
        return True


class FakePayments:
    def get(self, payment_id):
        return FakePayment()


class Client:
    def set_api_key(self, api_key):
        self.api_key = api_key

    @property
    def payments(self):
        return FakePayments()
""",
        encoding="utf-8",
    )

    old_db = payment_server.DB_PATH
    try:
        payment_server.DB_PATH = db_path
        payment_server._init_db()
        conn = payment_server._db()
        conn.execute(
            """INSERT INTO orders
               (order_id, mollie_id, product, company_name, customer_email, amount,
                currency, status, scan_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("ds_cli_replay", "tr_cli_secret", "compact", "Mollie B.V.", "finance@mollie.com", "79.00", "EUR", "pending", "pending"),
        )
        conn.commit()
        conn.close()
    finally:
        payment_server.DB_PATH = old_db

    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": os.pathsep.join([str(tmp_path), str(ROOT)]),
            "PYTHONDONTWRITEBYTECODE": "1",
            "DUESIGHT_PAYMENT_DB_PATH": str(db_path),
            "DUESIGHT_SCAN_QUEUE_FILE": str(tmp_path / "scan_queue.jsonl"),
            "DUESIGHT_SUPPORT_EVENTS_FILE": str(tmp_path / "support_events.jsonl"),
            "MOLLIE_API_KEY": "test_unit_should_not_print",
        }
    )
    result = subprocess.run(
        [sys.executable, str(ROOT / "payment_server.py"), "webhook-replay", "--payment-id", "tr_cli_secret"],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "tr_cli_secret" not in result.stdout
    assert "test_unit_should_not_print" not in result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "paid"
    assert payload["action"] == "queued"


def test_delivery_requires_paid_order(monkeypatch):
    _prepare(monkeypatch)
    conn = payment_server._db()
    conn.execute(
        """INSERT INTO orders
           (order_id, mollie_id, product, company_name, customer_email, amount,
            currency, status, scan_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("ds_unpaid", "tr_unpaid", "compact", "Acme B.V.", "ops@acme.nl", "79.00", "EUR", "pending", "pending"),
    )
    conn.commit()
    conn.close()

    response = _client().post(
        "/api/payment/delivery/complete",
        headers=ADMIN_HEADERS,
        json={"order_id": "ds_unpaid", "report_url": "https://duesight.test/reports/ds_unpaid.pdf"},
    )

    assert response.status_code == 409
    assert response.json()["error"] == "Order is not paid"


def test_refunded_order_is_not_delivered(monkeypatch):
    _prepare(monkeypatch)
    conn = payment_server._db()
    conn.execute(
        """INSERT INTO orders
           (order_id, mollie_id, product, company_name, customer_email, amount,
            currency, status, scan_status, refund_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "ds_refunded_delivery",
            "tr_refunded_delivery",
            "compact",
            "Acme B.V.",
            "ops@acme.nl",
            "79.00",
            "EUR",
            "refunded",
            "queued",
            "refunded",
        ),
    )
    conn.commit()
    conn.close()

    def fail_runner(order):
        pytest.fail(f"refunded order reached delivery runner: {order['order_id']}")

    endpoint = _client().post(
        "/api/payment/delivery/complete",
        headers=ADMIN_HEADERS,
        json={
            "order_id": "ds_refunded_delivery",
            "report_url": "https://duesight.test/reports/ds_refunded_delivery.pdf",
        },
    )
    direct = payment_server.run_delivery_for_order(
        "ds_refunded_delivery",
        report_runner=fail_runner,
        send_email=False,
    )
    queued = payment_server.process_delivery_queue(
        limit=10,
        report_runner=fail_runner,
        send_email=False,
    )

    conn = payment_server._db()
    row = conn.execute(
        "SELECT scan_status, delivery_status, report_url FROM orders WHERE order_id = ?",
        ("ds_refunded_delivery",),
    ).fetchone()
    conn.close()

    assert endpoint.status_code == 409
    assert endpoint.json()["error"] == "Order is not paid"
    assert direct == {"status": "not_paid", "order_id": "ds_refunded_delivery"}
    assert queued == []
    assert row["scan_status"] == "queued"
    assert row["delivery_status"] == ""
    assert row["report_url"] == ""
