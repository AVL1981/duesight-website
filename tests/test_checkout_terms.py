import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import payment_server


ROOT = Path(__file__).resolve().parents[1]
TEST_DB = Path(__file__).with_name("_checkout_terms_test_orders.db")


@pytest.fixture(autouse=True)
def clean_terms_test_db():
    if TEST_DB.exists():
        TEST_DB.unlink()
    yield
    if TEST_DB.exists():
        TEST_DB.unlink()


class CreatedPayment:
    id = "tr_terms"
    checkout_url = "https://checkout.mollie.test/tr_terms"


class CreatedLinkedPayment:
    id = "tr_terms_linked"
    _links = {"checkout": {"href": "https://checkout.mollie.test/tr_terms_linked"}}


class FakePayments:
    def __init__(self, captured):
        self.captured = captured
        self.idempotency_keys: list[str] = []

    def create(self, payment_data, idempotency_key="", **_kwargs):
        self.captured.append(payment_data)
        self.idempotency_keys.append(idempotency_key)
        return CreatedPayment()


class FakeMollie:
    def __init__(self, captured):
        self.payments = FakePayments(captured)


class FakeLinkedMollie:
    def __init__(self, captured):
        self.payments = FakePayments(captured)
        self.payments.create = lambda payment_data, idempotency_key="", **_k: self._create(payment_data, idempotency_key)

    def _create(self, payment_data, idempotency_key=""):
        self.payments.captured.append(payment_data)
        self.payments.idempotency_keys.append(idempotency_key)
        return CreatedLinkedPayment()


def _client():
    app = FastAPI()
    app.include_router(payment_server.payment_router, prefix="/api/payment")
    return TestClient(app)


def _prepare_db(monkeypatch):
    monkeypatch.setattr(payment_server, "DB_PATH", TEST_DB)
    payment_server._init_db()


def test_checkout_requires_terms_acceptance(monkeypatch):
    _prepare_db(monkeypatch)

    response = _client().post(
        "/api/payment/create",
        json={
            "product": "compact",
            "company_name": "Mollie B.V.",
            "customer_email": "finance@mollie.com",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "terms_acceptance_required"

    conn = payment_server._db()
    count = conn.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"]
    conn.close()
    assert count == 0


def test_checkout_records_terms_acceptance(monkeypatch):
    _prepare_db(monkeypatch)
    captured = []
    monkeypatch.setattr(payment_server, "_mollie", lambda: FakeMollie(captured))

    response = _client().post(
        "/api/payment/create",
        json={
            "product": "compact",
            "company_name": "Mollie B.V.",
            "kvk_number": "56087887",
            "domain": "mollie.com",
            "customer_email": "finance@mollie.com",
            "terms_accepted": True,
        },
        headers={
            "user-agent": "DueSightTest/1.0",
            "x-forwarded-for": "203.0.113.10",
        },
    )

    assert response.status_code == 200
    assert response.json()["checkout_url"] == "https://checkout.mollie.test/tr_terms"
    assert len(captured) == 1

    conn = payment_server._db()
    row = conn.execute(
        """SELECT terms_accepted_at, terms_version, privacy_version, terms_ip,
                  terms_user_agent, terms_acceptance_hash, metadata
           FROM orders WHERE mollie_id = ?""",
        ("tr_terms",),
    ).fetchone()
    conn.close()

    assert row["terms_accepted_at"].endswith("Z")
    assert row["terms_version"] == payment_server.TERMS_VERSION
    assert row["privacy_version"] == payment_server.PRIVACY_VERSION
    assert row["terms_ip"] == "203.0.113.10"
    assert row["terms_user_agent"] == "DueSightTest/1.0"
    assert len(row["terms_acceptance_hash"]) == 64

    metadata = json.loads(row["metadata"])
    acceptance = metadata["terms_acceptance"]
    assert acceptance["accepted"] is True
    assert acceptance["hash"] == row["terms_acceptance_hash"]
    assert captured[0]["metadata"]["terms_acceptance_hash"] == row["terms_acceptance_hash"]


def test_checkout_accepts_mollie_links_checkout_href(monkeypatch):
    _prepare_db(monkeypatch)
    captured = []
    monkeypatch.setattr(payment_server, "_mollie", lambda: FakeLinkedMollie(captured))

    response = _client().post(
        "/api/payment/create",
        json={
            "product": "compact",
            "company_name": "Mollie B.V.",
            "customer_email": "finance@mollie.com",
            "terms_accepted": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["payment_id"] == "tr_terms_linked"
    assert response.json()["checkout_url"] == "https://checkout.mollie.test/tr_terms_linked"

    conn = payment_server._db()
    row = conn.execute("SELECT status FROM orders WHERE mollie_id = ?", ("tr_terms_linked",)).fetchone()
    conn.close()
    assert row["status"] == "pending"


def test_checkout_smoke_cli_redacts_checkout_artifacts(tmp_path):
    db_path = tmp_path / "orders.db"
    fake_pkg = tmp_path / "mollie" / "api"
    fake_pkg.mkdir(parents=True)
    (tmp_path / "mollie" / "__init__.py").write_text("", encoding="utf-8")
    (fake_pkg / "__init__.py").write_text("", encoding="utf-8")
    (fake_pkg / "client.py").write_text(
        """
class CreatedPayment:
    id = "tr_cli_checkout_secret"
    checkout_url = "https://checkout.mollie.test/cli-secret"


class FakePayments:
    def create(self, payment_data, idempotency_key="", **_kwargs):
        return CreatedPayment()


class Client:
    def set_api_key(self, api_key):
        self.api_key = api_key

    @property
    def payments(self):
        return FakePayments()
""",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": os.pathsep.join([str(tmp_path), str(ROOT)]),
            "PYTHONDONTWRITEBYTECODE": "1",
            "DUESIGHT_PAYMENT_DB_PATH": str(db_path),
            "DUESIGHT_BASE_URL": "https://duesight.test",
            "MOLLIE_API_KEY": "test_unit_should_not_print",
        }
    )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "payment_server.py"),
            "checkout-smoke",
            "--product",
            "compact",
            "--company",
            "Mollie B.V.",
            "--email",
            "finance@mollie.com",
            "--domain",
            "mollie.com",
            "--kvk",
            "56087887",
            "--terms-accepted",
        ],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 0, result.stderr
    assert "tr_cli_checkout_secret" not in combined
    assert "checkout.mollie.test" not in combined
    assert "test_unit_should_not_print" not in combined

    payload = json.loads(result.stdout)
    assert payload["checkout_created"] is True
    assert payload["status"] == "pending"
    assert payload["product"] == "compact"
    assert payload["amount"] == "79.00"
    assert "order_id" in payload
    assert "payment_id" not in payload
    assert "checkout_url" not in payload

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        """SELECT mollie_id, product, company_name, customer_email,
                  terms_ip, terms_user_agent, terms_acceptance_hash
           FROM orders WHERE order_id = ?""",
        (payload["order_id"],),
    ).fetchone()
    conn.close()

    assert row["mollie_id"] == "tr_cli_checkout_secret"
    assert row["product"] == "compact"
    assert row["company_name"] == "Mollie B.V."
    assert row["customer_email"] == "finance@mollie.com"
    assert row["terms_ip"] == "cli"
    assert row["terms_user_agent"] == "payment_server.py checkout-smoke"
    assert len(row["terms_acceptance_hash"]) == 64


def test_checkout_smoke_cli_refuses_live_key_without_override(tmp_path):
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(ROOT),
            "PYTHONDONTWRITEBYTECODE": "1",
            "DUESIGHT_PAYMENT_DB_PATH": str(tmp_path / "orders.db"),
            "MOLLIE_API_KEY": "live_unit_should_not_print",
        }
    )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "payment_server.py"),
            "checkout-smoke",
            "--company",
            "Mollie B.V.",
            "--email",
            "finance@mollie.com",
            "--terms-accepted",
        ],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 2
    assert "live_unit_should_not_print" not in combined

    payload = json.loads(result.stdout)
    assert payload["status"] == "refused"
    assert payload["code"] == "live_key_requires_allow_live"
    assert payload["checkout_created"] is False
