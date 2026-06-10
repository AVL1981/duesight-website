from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import payment_server


TEST_DB = Path(__file__).with_name("_order_upload_test_orders.db")
UPLOAD_DIR = Path(__file__).with_name("_order_uploads")
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def clean_upload_test_files():
    if TEST_DB.exists():
        TEST_DB.unlink()
    if UPLOAD_DIR.exists():
        for path in sorted(UPLOAD_DIR.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            else:
                path.rmdir()
        UPLOAD_DIR.rmdir()
    yield
    if TEST_DB.exists():
        TEST_DB.unlink()
    if UPLOAD_DIR.exists():
        for path in sorted(UPLOAD_DIR.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            else:
                path.rmdir()
        UPLOAD_DIR.rmdir()


def _client():
    app = FastAPI()
    app.include_router(payment_server.payment_router, prefix="/api/payment")
    return TestClient(app)


def _prepare(monkeypatch):
    monkeypatch.setattr(payment_server, "DB_PATH", TEST_DB)
    monkeypatch.setattr(payment_server, "UPLOAD_DIR", UPLOAD_DIR)
    payment_server._init_db()
    conn = payment_server._db()
    conn.execute(
        """INSERT INTO orders
           (order_id, mollie_id, product, company_name, customer_email, amount,
            currency, status, scan_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "ds_upload",
            "tr_upload",
            "predd",
            "Mollie B.V.",
            "finance@mollie.com",
            "399.00",
            "EUR",
            "pending",
            "pending",
        ),
    )
    conn.commit()
    conn.close()


def test_customer_upload_is_linked_to_order(monkeypatch):
    _prepare(monkeypatch)

    response = _client().post(
        "/api/payment/orders/ds_upload/uploads",
        data={"customer_email": "finance@mollie.com"},
        files={"file": ("jaarrekening.pdf", b"%PDF-1.4\nminimal", "application/pdf")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "uploaded"
    assert payload["filename"] == "jaarrekening.pdf"
    assert payload["size_bytes"] > 0
    assert len(payload["sha256"]) == 64

    conn = payment_server._db()
    row = conn.execute("SELECT upload_status FROM orders WHERE order_id = ?", ("ds_upload",)).fetchone()
    upload = conn.execute(
        "SELECT original_filename, size_bytes, sha256 FROM order_uploads WHERE order_id = ?",
        ("ds_upload",),
    ).fetchone()
    event = conn.execute("SELECT action FROM payment_events").fetchone()
    conn.close()

    assert row["upload_status"] == "uploaded"
    assert upload["original_filename"] == "jaarrekening.pdf"
    assert upload["size_bytes"] == payload["size_bytes"]
    assert upload["sha256"] == payload["sha256"]
    assert event["action"] == "customer_upload_received"
    assert len(list(UPLOAD_DIR.rglob("*.pdf"))) == 1


def test_customer_upload_requires_matching_email(monkeypatch):
    _prepare(monkeypatch)

    response = _client().post(
        "/api/payment/orders/ds_upload/uploads",
        data={"customer_email": "other@example.com"},
        files={"file": ("jaarrekening.pdf", b"%PDF-1.4\nminimal", "application/pdf")},
    )

    assert response.status_code == 403
    assert not UPLOAD_DIR.exists()


@pytest.mark.parametrize(
    ("status", "scan_status", "delivery_status"),
    [
        ("refunded", "queued", ""),
        ("canceled", "cancelled", ""),
        ("failed", "cancelled", ""),
        ("paid", "delivered", "ready"),
    ],
)
def test_customer_upload_rejects_closed_order_states(monkeypatch, status, scan_status, delivery_status):
    _prepare(monkeypatch)
    conn = payment_server._db()
    conn.execute(
        "UPDATE orders SET status = ?, scan_status = ?, delivery_status = ? WHERE order_id = ?",
        (status, scan_status, delivery_status, "ds_upload"),
    )
    conn.commit()
    conn.close()

    response = _client().post(
        "/api/payment/orders/ds_upload/uploads",
        data={"customer_email": "finance@mollie.com"},
        files={"file": ("jaarrekening.pdf", b"%PDF-1.4\nminimal", "application/pdf")},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "order_not_open_for_upload"
    assert not UPLOAD_DIR.exists()


def test_customer_upload_limit_is_enforced_per_order(monkeypatch):
    monkeypatch.setattr(payment_server, "MAX_UPLOADS_PER_ORDER", 2)
    _prepare(monkeypatch)
    client = _client()

    first = client.post(
        "/api/payment/orders/ds_upload/uploads",
        data={"customer_email": "finance@mollie.com"},
        files={"file": ("jaarrekening-1.pdf", b"%PDF-1.4\none", "application/pdf")},
    )
    second = client.post(
        "/api/payment/orders/ds_upload/uploads",
        data={"customer_email": "finance@mollie.com"},
        files={"file": ("jaarrekening-2.pdf", b"%PDF-1.4\ntwo", "application/pdf")},
    )
    third = client.post(
        "/api/payment/orders/ds_upload/uploads",
        data={"customer_email": "finance@mollie.com"},
        files={"file": ("jaarrekening-3.pdf", b"%PDF-1.4\nthree", "application/pdf")},
    )

    conn = payment_server._db()
    upload_count = conn.execute(
        "SELECT COUNT(*) AS upload_count FROM order_uploads WHERE order_id = ?",
        ("ds_upload",),
    ).fetchone()["upload_count"]
    conn.close()

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 409
    assert third.json()["code"] == "upload_limit_reached"
    assert upload_count == 2
    assert len(list(UPLOAD_DIR.rglob("*.pdf"))) == 2


def test_cleanup_stale_uploads_purges_only_old_unpaid_uploads(monkeypatch):
    _prepare(monkeypatch)
    old = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat().replace("+00:00", "Z")
    recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace("+00:00", "Z")

    uploads = [
        ("ds_upload", "tr_upload", "pending", "pending", "", "up_old_unpaid", old),
        ("ds_paid_upload", "tr_paid_upload", "paid", "queued", "", "up_old_paid", old),
        ("ds_delivered_upload", "tr_delivered_upload", "refunded", "delivered", "", "up_old_delivered", old),
        ("ds_recent_upload", "tr_recent_upload", "pending", "pending", "", "up_recent_unpaid", recent),
    ]

    conn = payment_server._db()
    for order_id, mollie_id, status, scan_status, delivery_status, upload_id, created_at in uploads[1:]:
        conn.execute(
            """INSERT INTO orders
               (order_id, mollie_id, product, company_name, customer_email, amount,
                currency, status, scan_status, delivery_status, upload_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                order_id,
                mollie_id,
                "predd",
                "Mollie B.V.",
                "finance@mollie.com",
                "399.00",
                "EUR",
                status,
                scan_status,
                delivery_status,
                "uploaded",
            ),
        )
    conn.execute("UPDATE orders SET upload_status = ? WHERE order_id = ?", ("uploaded", "ds_upload"))

    for order_id, _mollie_id, _status, _scan_status, _delivery_status, upload_id, created_at in uploads:
        target_dir = UPLOAD_DIR / order_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{upload_id}_jaarrekening.pdf"
        target_path.write_bytes(b"%PDF-1.4\nupload")
        conn.execute(
            """INSERT INTO order_uploads
               (upload_id, order_id, original_filename, stored_path, content_type,
                size_bytes, sha256, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                upload_id,
                order_id,
                "jaarrekening.pdf",
                str(target_path),
                "application/pdf",
                target_path.stat().st_size,
                "0" * 64,
                created_at,
            ),
        )
    conn.commit()
    conn.close()

    dry_run = payment_server.cleanup_stale_uploads(retention_hours=24, dry_run=True)
    execute = payment_server.cleanup_stale_uploads(retention_hours=24, dry_run=False)

    conn = payment_server._db()
    rows = [
        (row["order_id"], row["upload_id"])
        for row in conn.execute("SELECT order_id, upload_id FROM order_uploads ORDER BY order_id").fetchall()
    ]
    purged_order = conn.execute(
        "SELECT upload_status FROM orders WHERE order_id = ?",
        ("ds_upload",),
    ).fetchone()
    actions = [row["action"] for row in conn.execute("SELECT action FROM payment_events ORDER BY id").fetchall()]
    conn.close()

    assert dry_run["status"] == "dry_run"
    assert dry_run["eligible"] == 1
    assert dry_run["deleted_files"] == 0
    assert execute["status"] == "executed"
    assert execute["eligible"] == 1
    assert execute["deleted_files"] == 1
    assert execute["deleted_rows"] == 1
    assert execute["skipped_paid_or_ready"] == 2
    assert execute["skipped_recent"] == 1
    assert execute["order_ids"] == ["ds_upload"]
    assert rows == [
        ("ds_delivered_upload", "up_old_delivered"),
        ("ds_paid_upload", "up_old_paid"),
        ("ds_recent_upload", "up_recent_unpaid"),
    ]
    assert purged_order["upload_status"] == "purged"
    assert "customer_upload_purged" in actions
    assert not (UPLOAD_DIR / "ds_upload" / "up_old_unpaid_jaarrekening.pdf").exists()
    assert (UPLOAD_DIR / "ds_delivered_upload" / "up_old_delivered_jaarrekening.pdf").exists()
    assert (UPLOAD_DIR / "ds_paid_upload" / "up_old_paid_jaarrekening.pdf").exists()
    assert (UPLOAD_DIR / "ds_recent_upload" / "up_recent_unpaid_jaarrekening.pdf").exists()


def test_cleanup_uploads_cli_dry_run_redacts_order_ids(monkeypatch):
    _prepare(monkeypatch)
    old = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat().replace("+00:00", "Z")
    target_dir = UPLOAD_DIR / "ds_upload"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / "up_old_cli_jaarrekening.pdf"
    target_path.write_bytes(b"%PDF-1.4\nupload")

    conn = payment_server._db()
    conn.execute("UPDATE orders SET upload_status = ? WHERE order_id = ?", ("uploaded", "ds_upload"))
    conn.execute(
        """INSERT INTO order_uploads
           (upload_id, order_id, original_filename, stored_path, content_type,
            size_bytes, sha256, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "up_old_cli",
            "ds_upload",
            "jaarrekening.pdf",
            str(target_path),
            "application/pdf",
            target_path.stat().st_size,
            "0" * 64,
            old,
        ),
    )
    conn.commit()
    conn.close()

    env = os.environ.copy()
    env.update(
        {
            "DUESIGHT_PAYMENT_DB_PATH": str(TEST_DB),
            "DUESIGHT_UPLOAD_DIR": str(UPLOAD_DIR),
        }
    )
    result = subprocess.run(
        [sys.executable, str(ROOT / "payment_server.py"), "cleanup-uploads", "--retention-hours", "24"],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "dry_run"
    assert payload["eligible"] == 1
    assert payload["orders_affected"] == 1
    assert payload["order_ids_redacted"] is True
    assert "order_ids" not in payload
    assert "ds_upload" not in result.stdout
    assert "finance@mollie.com" not in result.stdout
    assert target_path.exists()


def test_customer_upload_rejects_unsupported_file_type(monkeypatch):
    _prepare(monkeypatch)

    response = _client().post(
        "/api/payment/orders/ds_upload/uploads",
        data={"customer_email": "finance@mollie.com"},
        files={"file": ("malware.exe", b"MZ", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "unsupported_file_type"
