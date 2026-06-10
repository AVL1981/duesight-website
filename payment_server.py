from __future__ import annotations

import hashlib
import hmac
import json
import mimetypes
import os
import re
import secrets
import shutil
import smtplib
import socket
import ssl
import sqlite3
import subprocess
import sys
import time
import asyncio
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

from fastapi import APIRouter, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=Path(__file__).with_name(".env"))
except Exception:
    pass

try:
    from app.core.security_headers import SecurityHeadersMiddleware
except ImportError:
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).parent))
    from app.core.security_headers import SecurityHeadersMiddleware


ROOT = Path(__file__).resolve().parent


def _env_path(name: str, default: Path) -> Path:
    value = os.getenv(name, "").strip()
    return Path(value).expanduser() if value else default


DATA_DIR = _env_path("DUESIGHT_PAYMENT_DATA_DIR", ROOT / "data")
DB_PATH = _env_path("DUESIGHT_PAYMENT_DB_PATH", DATA_DIR / "orders.db")
SCAN_QUEUE_FILE = _env_path("DUESIGHT_SCAN_QUEUE_FILE", DATA_DIR / "scan_queue.jsonl")
SUPPORT_EVENTS_FILE = _env_path("DUESIGHT_SUPPORT_EVENTS_FILE", DATA_DIR / "support_events.jsonl")
DELIVERY_EVENTS_FILE = _env_path("DUESIGHT_DELIVERY_EVENTS_FILE", DATA_DIR / "delivery_events.jsonl")
EMAIL_OUTBOX_FILE = _env_path("DUESIGHT_EMAIL_OUTBOX_FILE", DATA_DIR / "email_outbox.jsonl")
UPLOAD_DIR = _env_path("DUESIGHT_UPLOAD_DIR", DATA_DIR / "customer_uploads")

BASE_URL = os.getenv("DUESIGHT_BASE_URL", "http://127.0.0.1:5051").rstrip("/")
TERMS_VERSION = os.getenv("DUESIGHT_TERMS_VERSION", "terms-2026-05-11")
PRIVACY_VERSION = os.getenv("DUESIGHT_PRIVACY_VERSION", "privacy-2026-05-11")

MAX_UPLOAD_BYTES = int(os.getenv("DUESIGHT_MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
MAX_UPLOADS_PER_ORDER = int(os.getenv("DUESIGHT_MAX_UPLOADS_PER_ORDER", "5"))
STALE_UPLOAD_RETENTION_HOURS = int(os.getenv("DUESIGHT_STALE_UPLOAD_RETENTION_HOURS", "48"))
REPORT_RUN_TIMEOUT_SECONDS = int(os.getenv("DUESIGHT_REPORT_RUN_TIMEOUT_SECONDS", "1800"))
DELIVERY_WORKER_INTERVAL_SECONDS = int(os.getenv("DUESIGHT_DELIVERY_WORKER_INTERVAL_SECONDS", "60"))
ALLOWED_UPLOAD_EXTENSIONS = {
    ".csv",
    ".doc",
    ".docx",
    ".json",
    ".jpg",
    ".jpeg",
    ".pdf",
    ".png",
    ".txt",
    ".webp",
    ".xls",
    ".xlsx",
}
UPLOAD_BLOCKED_ORDER_STATUSES = {"canceled", "cancelled", "expired", "failed", "refunded"}
UPLOAD_BLOCKED_SCAN_STATUSES = {"canceled", "cancelled", "delivered", "completed"}

PRODUCTS: dict[str, dict[str, str]] = {
    "compact": {
        "name": "DueSight Compact Scan",
        "amount": "79.00",
        "currency": "EUR",
        "tier": "quick_scan",
    },
    "predd": {
        "name": "DueSight Pre-DD Rapport",
        "amount": "399.00",
        "currency": "EUR",
        "tier": "premium",
    },
    "ma": {
        "name": "DueSight M&A Report",
        "amount": "399.00",
        "currency": "EUR",
        "tier": "premium",
    },
    "monitoring": {
        "name": "DueSight Monitoring",
        "amount": "19.00",
        "currency": "EUR",
        "tier": "monitoring",
    },
}

PRODUCT_ALIASES = {
    "quick_scan": "compact",
    "standard": "compact",
    "premium": "predd",
    "institutional": "predd",
}

payment_router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_utc(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_columns(conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, ddl in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def _init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = _db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            mollie_id TEXT UNIQUE,
            product TEXT NOT NULL DEFAULT '',
            company_name TEXT NOT NULL DEFAULT '',
            kvk_number TEXT NOT NULL DEFAULT '',
            domain TEXT NOT NULL DEFAULT '',
            customer_email TEXT NOT NULL DEFAULT '',
            amount TEXT NOT NULL DEFAULT '',
            currency TEXT NOT NULL DEFAULT 'EUR',
            status TEXT NOT NULL DEFAULT 'pending',
            scan_status TEXT NOT NULL DEFAULT 'pending',
            webhook_count INTEGER NOT NULL DEFAULT 0,
            last_webhook_action TEXT NOT NULL DEFAULT '',
            metadata TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT '',
            terms_accepted_at TEXT NOT NULL DEFAULT '',
            terms_version TEXT NOT NULL DEFAULT '',
            privacy_version TEXT NOT NULL DEFAULT '',
            terms_ip TEXT NOT NULL DEFAULT '',
            terms_user_agent TEXT NOT NULL DEFAULT '',
            terms_acceptance_hash TEXT NOT NULL DEFAULT '',
            report_url TEXT NOT NULL DEFAULT '',
            report_path TEXT NOT NULL DEFAULT '',
            delivery_status TEXT NOT NULL DEFAULT '',
            delivery_token_hash TEXT NOT NULL DEFAULT '',
            delivery_email TEXT NOT NULL DEFAULT '',
            delivery_created_at TEXT NOT NULL DEFAULT '',
            delivered_at TEXT NOT NULL DEFAULT '',
            refund_status TEXT NOT NULL DEFAULT 'none',
            refund_reason TEXT NOT NULL DEFAULT '',
            refund_contact_email TEXT NOT NULL DEFAULT '',
            refund_requested_at TEXT NOT NULL DEFAULT '',
            refund_resolution TEXT NOT NULL DEFAULT '',
            refund_resolved_at TEXT NOT NULL DEFAULT '',
            refunded_at TEXT NOT NULL DEFAULT '',
            upload_status TEXT NOT NULL DEFAULT 'none'
        );

        CREATE TABLE IF NOT EXISTS payment_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL DEFAULT '',
            mollie_id TEXT NOT NULL DEFAULT '',
            action TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS order_uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            upload_id TEXT NOT NULL UNIQUE,
            order_id TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            content_type TEXT NOT NULL DEFAULT '',
            size_bytes INTEGER NOT NULL DEFAULT 0,
            sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_orders_mollie_id ON orders(mollie_id);
        CREATE INDEX IF NOT EXISTS idx_events_order ON payment_events(order_id);
        CREATE UNIQUE INDEX IF NOT EXISTS uq_events_mollie_action ON payment_events(mollie_id, action);
        CREATE INDEX IF NOT EXISTS idx_uploads_order ON order_uploads(order_id);
        """
    )
    _ensure_columns(
        conn,
        "orders",
        {
            "kvk_number": "TEXT NOT NULL DEFAULT ''",
            "domain": "TEXT NOT NULL DEFAULT ''",
            "webhook_count": "INTEGER NOT NULL DEFAULT 0",
            "last_webhook_action": "TEXT NOT NULL DEFAULT ''",
            "metadata": "TEXT NOT NULL DEFAULT '{}'",
            "terms_accepted_at": "TEXT NOT NULL DEFAULT ''",
            "terms_version": "TEXT NOT NULL DEFAULT ''",
            "privacy_version": "TEXT NOT NULL DEFAULT ''",
            "terms_ip": "TEXT NOT NULL DEFAULT ''",
            "terms_user_agent": "TEXT NOT NULL DEFAULT ''",
            "terms_acceptance_hash": "TEXT NOT NULL DEFAULT ''",
            "report_url": "TEXT NOT NULL DEFAULT ''",
            "report_path": "TEXT NOT NULL DEFAULT ''",
            "delivery_status": "TEXT NOT NULL DEFAULT ''",
            "delivery_token_hash": "TEXT NOT NULL DEFAULT ''",
            "delivery_email": "TEXT NOT NULL DEFAULT ''",
            "delivery_created_at": "TEXT NOT NULL DEFAULT ''",
            "delivered_at": "TEXT NOT NULL DEFAULT ''",
            "refund_status": "TEXT NOT NULL DEFAULT 'none'",
            "refund_reason": "TEXT NOT NULL DEFAULT ''",
            "refund_contact_email": "TEXT NOT NULL DEFAULT ''",
            "refund_requested_at": "TEXT NOT NULL DEFAULT ''",
            "refund_resolution": "TEXT NOT NULL DEFAULT ''",
            "refund_resolved_at": "TEXT NOT NULL DEFAULT ''",
            "refunded_at": "TEXT NOT NULL DEFAULT ''",
            "upload_status": "TEXT NOT NULL DEFAULT 'none'",
        },
    )
    conn.commit()
    conn.close()


def _json_response(status_code: int, **payload: Any) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=payload)


def _product_key(value: str | None) -> str:
    raw = (value or "compact").strip().lower()
    return PRODUCT_ALIASES.get(raw, raw)


def _product(value: str | None) -> dict[str, str]:
    key = _product_key(value)
    if key not in PRODUCTS:
        raise HTTPException(status_code=400, detail=f"Unsupported product: {value}")
    return {"key": key, **PRODUCTS[key]}


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return ""


def _hash_terms_acceptance(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _redact_url_token(value: str) -> str:
    return re.sub(r"(?i)([?&]token=)[^&#]+", r"\1[redacted]", value)


def _safe_slug(value: str, fallback: str = "file") -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip(".-_")
    return slug[:120] or fallback


def _upload_block_reason(row: sqlite3.Row) -> str:
    status = str(row["status"] or "").lower()
    scan_status = str(row["scan_status"] or "").lower()
    delivery_status = str(row["delivery_status"] or "").lower()
    if status in UPLOAD_BLOCKED_ORDER_STATUSES:
        return "order_not_open_for_upload"
    if scan_status in UPLOAD_BLOCKED_SCAN_STATUSES or delivery_status == "ready":
        return "order_not_open_for_upload"
    return ""


def _order_has_protected_uploads(row: sqlite3.Row) -> bool:
    status = str(row["status"] or "").lower()
    scan_status = str(row["scan_status"] or "").lower()
    delivery_status = str(row["delivery_status"] or "").lower()
    return status == "paid" or scan_status in {"delivered", "completed"} or delivery_status == "ready"


def _write_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")


def _log_event(order_id: str, mollie_id: str, action: str, details: dict[str, Any] | None = None) -> None:
    # Idempotent insert: the uq_events_mollie_action UNIQUE index dedupes
    # repeated (mollie_id, action) tuples so that webhook redelivery storms
    # do not bloat the events table. The first event of a kind is preserved;
    # subsequent identical events are silently dropped.
    conn = _db()
    conn.execute(
        """INSERT OR IGNORE INTO payment_events (order_id, mollie_id, action, details, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (order_id, mollie_id, action, json.dumps(details or {}, ensure_ascii=True), _now()),
    )
    conn.commit()
    conn.close()


def _order_by_mollie_id(mollie_id: str) -> sqlite3.Row | None:
    conn = _db()
    row = conn.execute("SELECT * FROM orders WHERE mollie_id = ?", (mollie_id,)).fetchone()
    conn.close()
    return row


def _order_by_id(order_id: str) -> sqlite3.Row | None:
    conn = _db()
    row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
    conn.close()
    return row


def _uploads_for_order(order_id: str) -> list[dict[str, Any]]:
    conn = _db()
    rows = conn.execute(
        """SELECT upload_id, original_filename, stored_path, content_type,
                  size_bytes, sha256, created_at
           FROM order_uploads
           WHERE order_id = ?
           ORDER BY id ASC""",
        (order_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def _upload_count_for_order(order_id: str) -> int:
    conn = _db()
    row = conn.execute(
        "SELECT COUNT(*) AS upload_count FROM order_uploads WHERE order_id = ?",
        (order_id,),
    ).fetchone()
    conn.close()
    return int(row["upload_count"] or 0)


def _safe_upload_path(stored_path: str) -> Path | None:
    try:
        path = Path(stored_path).expanduser().resolve()
        upload_root = UPLOAD_DIR.expanduser().resolve()
        if not path.is_relative_to(upload_root):
            return None
        return path
    except (OSError, ValueError):
        return None


def cleanup_stale_uploads(retention_hours: int = STALE_UPLOAD_RETENTION_HOURS, dry_run: bool = True) -> dict[str, Any]:
    """Purge stale uploads for abandoned or terminal non-delivered orders."""
    _init_db()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
    conn = _db()
    rows = conn.execute(
        """SELECT u.id, u.upload_id, u.order_id, u.stored_path, u.created_at,
                  o.mollie_id, o.status, o.scan_status, o.delivery_status
           FROM order_uploads u
           JOIN orders o ON o.order_id = u.order_id
           ORDER BY u.created_at ASC, u.id ASC"""
    ).fetchall()

    result: dict[str, Any] = {
        "status": "dry_run" if dry_run else "executed",
        "retention_hours": retention_hours,
        "cutoff": cutoff.isoformat().replace("+00:00", "Z"),
        "scanned": len(rows),
        "eligible": 0,
        "deleted_files": 0,
        "deleted_rows": 0,
        "skipped_paid_or_ready": 0,
        "skipped_recent": 0,
        "skipped_missing_file": 0,
        "skipped_unsafe_path": 0,
        "order_ids": [],
    }
    order_ids: set[str] = set()

    for row in rows:
        created_at = _parse_utc(row["created_at"])
        if not created_at or created_at > cutoff:
            result["skipped_recent"] += 1
            continue
        if _order_has_protected_uploads(row):
            result["skipped_paid_or_ready"] += 1
            continue

        path = _safe_upload_path(row["stored_path"])
        if path is None:
            result["skipped_unsafe_path"] += 1
            continue

        result["eligible"] += 1
        order_ids.add(row["order_id"])
        if dry_run:
            continue

        if path.exists():
            path.unlink()
            result["deleted_files"] += 1
            try:
                path.parent.rmdir()
            except OSError:
                pass
        else:
            result["skipped_missing_file"] += 1

        conn.execute("DELETE FROM order_uploads WHERE id = ?", (row["id"],))
        result["deleted_rows"] += 1
        conn.execute(
            """INSERT INTO payment_events (order_id, mollie_id, action, details, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                row["order_id"],
                row["mollie_id"],
                "customer_upload_purged",
                json.dumps({"reason": "stale_unpaid_upload"}, ensure_ascii=True),
                _now(),
            ),
        )

    if not dry_run and order_ids:
        for order_id in sorted(order_ids):
            count = conn.execute(
                "SELECT COUNT(*) AS upload_count FROM order_uploads WHERE order_id = ?",
                (order_id,),
            ).fetchone()["upload_count"]
            if not count:
                conn.execute(
                    "UPDATE orders SET upload_status = ?, updated_at = ? WHERE order_id = ?",
                    ("purged", _now(), order_id),
                )
        conn.commit()
    conn.close()

    result["order_ids"] = sorted(order_ids)
    return result


def _payment_value(payment: Any, key: str, default: Any = "") -> Any:
    if isinstance(payment, dict):
        return payment.get(key, default)
    return getattr(payment, key, default)


def _payment_link_href(payment: Any, rel: str) -> str:
    links = _payment_value(payment, "_links", None) or _payment_value(payment, "links", None)
    if not links:
        return ""

    link = links.get(rel) if isinstance(links, dict) else getattr(links, rel, None)
    if not link:
        return ""
    if isinstance(link, dict):
        return str(link.get("href") or "")
    return str(getattr(link, "href", "") or "")


def _payment_checkout_url(payment: Any) -> str:
    direct = _payment_value(payment, "checkout_url", "") or _payment_value(payment, "checkoutUrl", "")
    return str(direct or _payment_link_href(payment, "checkout"))


def _payment_status(payment: Any) -> str:
    for name, status in (
        ("is_paid", "paid"),
        ("is_failed", "failed"),
        ("is_expired", "expired"),
        ("is_canceled", "canceled"),
        ("is_cancelled", "canceled"),
    ):
        method = getattr(payment, name, None)
        if callable(method) and method():
            return status
    return str(_payment_value(payment, "status", "open") or "open")


def _payment_amount(payment: Any) -> tuple[str, str]:
    amount = _payment_value(payment, "amount", {}) or {}
    if isinstance(amount, dict):
        return str(amount.get("value", "")), str(amount.get("currency", "EUR"))
    return "", "EUR"


def _mollie() -> Any:
    api_key = os.getenv("MOLLIE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("MOLLIE_API_KEY is not configured")
    from mollie.api.client import Client

    client = Client()
    client.set_api_key(api_key)
    return client


def _create_mollie_payment_refund(
    payment_id: str,
    amount: str,
    currency: str,
    description: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    api_key = os.getenv("MOLLIE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("MOLLIE_API_KEY is not configured")
    url = f"https://api.mollie.com/v2/payments/{quote(payment_id, safe='')}/refunds"
    payload = {
        "amount": {"currency": currency, "value": amount},
        "description": description[:255],
        "metadata": metadata,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=True).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "DueSightPaymentServer/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read(8192)
            status_code = response.getcode()
    except urllib.error.HTTPError as exc:
        exc.read(8192)
        raise RuntimeError(f"mollie_refund_failed_{exc.code}") from None
    except Exception as exc:
        raise RuntimeError("mollie_refund_unavailable") from exc
    if status_code not in {200, 201}:
        raise RuntimeError(f"mollie_refund_failed_{status_code}")
    try:
        parsed = json.loads(body.decode("utf-8"))
    except Exception:
        parsed = {}
    return parsed if isinstance(parsed, dict) else {}


def create_mollie_refund_for_order(
    order_id: str,
    amount: str = "",
    note: str = "",
    allow_live: bool = False,
) -> dict[str, Any]:
    _init_db()
    row = _order_by_id(order_id)
    if not row:
        raise ValueError("order_not_found")
    if row["status"] != "paid":
        raise ValueError("order_not_paid")
    if _mollie_key_mode() == "live" and not allow_live:
        raise PermissionError("live_key_requires_allow_live")

    refund_amount = (amount or row["amount"]).strip()
    if not re.fullmatch(r"\d+(?:\.\d{2})", refund_amount):
        raise ValueError("invalid_refund_amount")

    # Amount cap: refund cannot exceed the original order amount.
    try:
        if float(refund_amount) > float(row["amount"]):
            raise ValueError("refund_amount_exceeds_order")
    except (TypeError, ValueError) as exc:
        if str(exc) == "refund_amount_exceeds_order":
            raise
        raise ValueError("invalid_refund_amount") from None

    # TOCTOU guard: atomically lock the order from 'paid' to 'refunding'
    # so that concurrent refund requests are rejected before reaching Mollie.
    conn = _db()
    conn.execute(
        """UPDATE orders SET status = ?, updated_at = ?
           WHERE order_id = ? AND status = ?""",
        ("refunding", _now(), order_id, "paid"),
    )
    conn.commit()
    if conn.total_changes == 0 or conn.execute(
        "SELECT status FROM orders WHERE order_id = ?", (order_id,)
    ).fetchone()["status"] != "refunding":
        conn.close()
        raise ValueError("order_not_paid")
    conn.close()

    description = (note or f"DueSight refund {order_id}").strip()[:255]
    try:
        refund = _create_mollie_payment_refund(
            payment_id=row["mollie_id"],
            amount=refund_amount,
            currency=row["currency"],
            description=description,
            metadata={"order_id": order_id, "source": "duesight_refund_smoke"},
        )
    except Exception:
        # Rollback the atomic lock so the order remains 'paid' on failure.
        conn = _db()
        conn.execute(
            "UPDATE orders SET status = ?, updated_at = ? WHERE order_id = ?",
            ("paid", _now(), order_id),
        )
        conn.commit()
        conn.close()
        raise

    now = _now()
    scan_status = row["scan_status"] if row["scan_status"] in {"delivered", "completed"} else "cancelled"
    conn = _db()
    conn.execute(
        """UPDATE orders
           SET status = ?, scan_status = ?, refund_status = ?, refund_resolution = ?,
               refund_resolved_at = ?, refunded_at = ?, updated_at = ?
           WHERE order_id = ?""",
        ("refunded", scan_status, "refunded", description, now, now, now, order_id),
    )
    conn.commit()
    conn.close()
    refund_status = str(refund.get("status") or "")
    _log_event(order_id, row["mollie_id"], "mollie_refund_created", {"refund_status": refund_status})
    return {
        "status": "refunded",
        "order_id": order_id,
        "refund_created": True,
        "amount": refund_amount,
        "currency": row["currency"],
        "mollie_refund_status": refund_status,
        "refund_id": str(refund.get("id") or ""),
        "payment_id": row["mollie_id"],
    }


def _queue_scan_order(**kwargs: Any) -> None:
    _write_jsonl(SCAN_QUEUE_FILE, {"type": "scan_queued", "created_at": _now(), **kwargs})


def _notify_admin(**kwargs: Any) -> None:
    _write_jsonl(SUPPORT_EVENTS_FILE, {"type": "admin_payment_notice", "created_at": _now(), **kwargs})


def _smtp_send_enabled() -> bool:
    return os.getenv("DUESIGHT_EMAIL_SEND_ENABLED", "").strip().lower() in {"1", "true", "yes"}


def _smtp_config_present() -> bool:
    return all(_present(os.getenv(name, "")) for name in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS"))


def _send_email_outbox(outbox: dict[str, Any], attempt_smtp: bool = True) -> dict[str, Any]:
    smtp_enabled = _smtp_send_enabled()
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587") or "587")
    sender = os.getenv("SMTP_FROM", "").strip() or smtp_user
    sender_name = os.getenv("SMTP_FROM_NAME", "DueSight Intelligence").strip()
    use_starttls = os.getenv("SMTP_STARTTLS", "true").strip().lower() not in {"0", "false", "no"}
    recipient = str(outbox.get("email") or "").strip()

    if attempt_smtp and smtp_enabled and smtp_host and smtp_user and smtp_pass and sender and recipient:
        message = EmailMessage()
        message["Subject"] = str(outbox.get("subject") or "DueSight bericht")
        message["From"] = f"{sender_name} <{sender}>"
        message["To"] = recipient
        message.set_content(str(outbox.get("body") or ""))
        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as smtp:
                if use_starttls:
                    smtp.starttls()
                smtp.login(smtp_user, smtp_pass)
                smtp.send_message(message)
            outbox["status"] = "smtp_sent"
        except Exception as exc:
            outbox["status"] = "smtp_failed"
            outbox["error"] = str(exc)[:300]

    _write_jsonl(EMAIL_OUTBOX_FILE, outbox)
    return {"status": outbox["status"], "file": str(EMAIL_OUTBOX_FILE)}


def _send_delivery_email(order: sqlite3.Row, delivery_url: str) -> dict[str, Any]:
    subject = f"Uw DueSight rapport staat klaar - {order['company_name'] or order['order_id']}"
    body = (
        f"Beste klant,\n\n"
        f"Uw DueSight rapport voor {order['company_name'] or 'uw aanvraag'} staat klaar.\n\n"
        f"Downloadlink:\n{delivery_url}\n\n"
        f"Deze link is persoonlijk en beveiligd met een token. Deel hem alleen met bevoegde personen.\n\n"
        f"Met vriendelijke groet,\n"
        f"DueSight Intelligence\n"
    )
    outbox = {
        "type": "delivery_email_outbox",
        "order_id": order["order_id"],
        "email": order["customer_email"],
        "company_name": order["company_name"],
        "subject": subject,
        "body": body,
        "delivery_url": delivery_url,
        "created_at": _now(),
        "status": "outbox_only",
    }
    return _send_email_outbox(outbox, attempt_smtp=True)


def run_email_smoke(recipient_email: str, allow_send: bool = False) -> dict[str, Any]:
    email = str(recipient_email or "").strip().lower()
    if "@" not in email:
        raise ValueError("recipient_email_required")

    outbox = {
        "type": "email_smoke",
        "order_id": "email_smoke",
        "email": email,
        "company_name": "DueSight Email Smoke",
        "subject": "DueSight email smoke",
        "body": (
            "DueSight email smoke.\n\n"
            "If this message arrived in the controlled inbox, SMTP delivery is working.\n"
        ),
        "delivery_url": "",
        "created_at": _now(),
        "status": "outbox_only",
    }
    result = _send_email_outbox(outbox, attempt_smtp=allow_send)
    return {
        "status": result["status"],
        "smtp_attempted": bool(allow_send),
        "recipient_present": True,
        "smtp_send_enabled": _smtp_send_enabled(),
        "smtp_config_present": _smtp_config_present(),
        "outbox_file": result["file"],
    }


def complete_delivery_order(
    order_id: str,
    report_url: str = "",
    report_path: str = "",
    send_email: bool = True,
) -> dict[str, Any]:
    """Mark a paid order ready and issue a tokenized delivery link."""
    _init_db()
    row = _order_by_id(order_id)
    if not row:
        raise ValueError("Order not found")
    if row["status"] != "paid":
        raise PermissionError("Order is not paid")

    normalized_url = report_url.strip()
    normalized_path = report_path.strip()
    if normalized_path:
        path = Path(normalized_path).expanduser().resolve()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError("report_path does not exist")
        normalized_path = str(path)
    if normalized_url and not normalized_url.startswith(("http://", "https://")):
        raise ValueError("report_url must be http(s)")
    if not normalized_url and not normalized_path:
        raise ValueError("report_url or report_path is required")

    token = secrets.token_urlsafe(32)
    if not normalized_url:
        normalized_url = f"{BASE_URL}/api/payment/report-file/{quote(order_id)}?token={quote(token)}"
    delivery_url = f"{BASE_URL}/api/payment/delivery-link/{quote(order_id)}?token={quote(token)}"
    created_at = _now()

    conn = _db()
    conn.execute(
        """UPDATE orders
           SET report_url = ?, report_path = ?, scan_status = ?, delivery_status = ?,
               delivery_token_hash = ?, delivery_email = ?, delivery_created_at = ?,
               delivered_at = ?, updated_at = ?
           WHERE order_id = ?""",
        (
            normalized_url,
            normalized_path,
            "delivered",
            "ready",
            _token_hash(token),
            row["customer_email"],
            created_at,
            created_at,
            created_at,
            order_id,
        ),
    )
    conn.commit()
    conn.close()
    event_report_url = _redact_url_token(normalized_url)
    event_delivery_url = _redact_url_token(delivery_url)
    _log_event(order_id, row["mollie_id"], "delivery_ready", {"report_url": event_report_url})
    _write_jsonl(
        DELIVERY_EVENTS_FILE,
        {
            "type": "delivery_ready",
            "order_id": order_id,
            "report_url": event_report_url,
            "delivery_url": event_delivery_url,
            "report_url_token_redacted": event_report_url != normalized_url,
            "delivery_url_token_redacted": event_delivery_url != delivery_url,
            "created_at": created_at,
        },
    )

    email_result = {"status": "skipped"}
    if send_email:
        refreshed = _order_by_id(order_id)
        if refreshed:
            email_result = _send_delivery_email(refreshed, delivery_url)

    return {
        "status": "ready",
        "order_id": order_id,
        "delivery_url": delivery_url,
        "report_url": normalized_url,
        "email_status": email_result["status"],
    }


def _agent_dir() -> Path:
    configured = os.getenv("DUESIGHT_AGENT_DIR", "").strip()
    if configured:
        return Path(configured)
    return ROOT.parent / "duesight-agent"


def _run_agent_report(order: dict[str, Any]) -> dict[str, str]:
    """Run the agent-side report pipeline and return a local report path."""
    agent_dir = _agent_dir()
    deliver_script = agent_dir / "deliver_report.py"
    if not deliver_script.exists():
        raise FileNotFoundError(f"deliver_report.py not found at {deliver_script}")

    domain = (order.get("domain") or "").strip()
    if not domain:
        company = (order.get("company_name") or order.get("order_id") or "unknown").strip().lower()
        domain = re.sub(r"[^a-z0-9]+", "", company) or "unknown"
    slug = domain.replace(".", "-")
    delivery_dir = agent_dir / "delivery"
    before = _now()

    cmd = [
        sys.executable,
        str(deliver_script),
        domain,
        "--company",
        str(order.get("company_name") or domain),
        "--tier",
        str(order.get("product") or "premium"),
    ]
    email = str(order.get("customer_email") or "").strip()
    if email:
        cmd.extend(["--email", email])

    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    uploads = order.get("uploads") if isinstance(order.get("uploads"), list) else []
    if uploads:
        env["DUESIGHT_ORDER_UPLOADS_JSON"] = json.dumps(uploads, ensure_ascii=True)
    completed = subprocess.run(
        cmd,
        cwd=str(agent_dir),
        env=env,
        capture_output=True,
        text=True,
        timeout=REPORT_RUN_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "deliver_report.py failed")[-800:])

    candidates = sorted(
        delivery_dir.glob(f"rapport_{slug}_*.html"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"deliver_report.py completed after {before}, but no report HTML was found")
    return {"report_path": str(candidates[0])}


def run_delivery_for_order(
    order_id: str,
    report_runner=None,
    send_email: bool = True,
) -> dict[str, Any]:
    """Process one paid order from queued scan to ready delivery link."""
    _init_db()
    row = _order_by_id(order_id)
    if not row:
        return {"status": "not_found", "order_id": order_id}
    if row["status"] != "paid":
        return {"status": "not_paid", "order_id": order_id}
    if row["delivery_status"] == "ready":
        return {"status": "already_ready", "order_id": order_id, "report_url": row["report_url"]}

    now = _now()
    conn = _db()
    conn.execute(
        "UPDATE orders SET scan_status = ?, updated_at = ? WHERE order_id = ?",
        ("processing", now, order_id),
    )
    conn.commit()
    conn.close()
    _log_event(order_id, row["mollie_id"], "delivery_worker_started", {})

    try:
        order = dict(row)
        order["uploads"] = _uploads_for_order(order_id)
        result = report_runner(order) if report_runner else _run_agent_report(order)
        if isinstance(result, str):
            result = {"report_url": result} if result.startswith(("http://", "https://")) else {"report_path": result}
        delivery = complete_delivery_order(
            order_id=order_id,
            report_url=str(result.get("report_url") or ""),
            report_path=str(result.get("report_path") or ""),
            send_email=send_email,
        )
        _log_event(
            order_id,
            row["mollie_id"],
            "delivery_worker_completed",
            {"report_url": _redact_url_token(delivery["report_url"])},
        )
        return {**delivery, "status": "completed", "delivery_status": delivery["status"]}
    except Exception as exc:
        conn = _db()
        conn.execute(
            """UPDATE orders
               SET scan_status = ?, last_webhook_action = ?, updated_at = ?
               WHERE order_id = ?""",
            ("failed", "delivery_worker_failed", _now(), order_id),
        )
        conn.commit()
        conn.close()
        _log_event(order_id, row["mollie_id"], "delivery_worker_failed", {"error": str(exc)[:500]})
        return {"status": "failed", "order_id": order_id, "error": str(exc)[:500]}


def process_delivery_queue(limit: int = 10, report_runner=None, send_email: bool = True) -> list[dict[str, Any]]:
    """Process paid queued orders from the local order database."""
    _init_db()
    conn = _db()
    rows = conn.execute(
        """SELECT order_id FROM orders
           WHERE status = 'paid'
             AND COALESCE(delivery_status, '') != 'ready'
             AND scan_status IN ('queueing', 'queued', 'processing')
           ORDER BY created_at ASC, order_id ASC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [run_delivery_for_order(row["order_id"], report_runner=report_runner, send_email=send_email) for row in rows]


def _present(value: str) -> bool:
    return bool((value or "").strip()) and not value.strip().startswith("<")


def _payment_admin_secret() -> str:
    return os.getenv("DUESIGHT_PAYMENT_ADMIN_SECRET", "").strip()


def _payment_admin_secret_present() -> bool:
    return _present(_payment_admin_secret())


def _request_admin_secret(request: Request) -> str:
    direct = request.headers.get("x-duesight-admin-secret", "").strip()
    if direct:
        return direct
    api_key = request.headers.get("x-api-key", "").strip()
    if api_key:
        return api_key
    authorization = request.headers.get("authorization", "").strip()
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""


def _require_payment_admin(request: Request) -> None:
    expected = _payment_admin_secret()
    if not _payment_admin_secret_present():
        raise HTTPException(status_code=503, detail="payment admin secret not configured")
    supplied = _request_admin_secret(request)
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=403, detail="payment admin secret required")


def smoke_config_status() -> dict[str, Any]:
    """Return redacted readiness data for payment/delivery live smoke."""
    _init_db()
    conn = _db()
    row = conn.execute(
        """SELECT
             COUNT(*) AS orders_total,
             SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) AS paid_orders,
             SUM(CASE WHEN status = 'paid' AND scan_status IN ('queued', 'queueing', 'processing')
                      AND COALESCE(delivery_status, '') != 'ready'
                 THEN 1 ELSE 0 END) AS delivery_queue
           FROM orders"""
    ).fetchone()
    conn.close()
    smtp_enabled = _smtp_send_enabled()
    smtp_ready = _smtp_config_present()
    return {
        "status": "ok",
        "base_url": BASE_URL,
        "mollie_api_key_present": _present(os.getenv("MOLLIE_API_KEY", "")),
        "payment_admin_secret_present": _payment_admin_secret_present(),
        "smtp_send_enabled": smtp_enabled,
        "smtp_config_present": smtp_ready,
        "smtp_will_send": smtp_enabled and smtp_ready,
        "payment_db_configured": str(DB_PATH),
        "email_outbox_configured": str(EMAIL_OUTBOX_FILE),
        "upload_dir_configured": str(UPLOAD_DIR),
        "max_upload_bytes": MAX_UPLOAD_BYTES,
        "max_uploads_per_order": MAX_UPLOADS_PER_ORDER,
        "stale_upload_retention_hours": STALE_UPLOAD_RETENTION_HOURS,
        "orders_total": int(row["orders_total"] or 0),
        "paid_orders": int(row["paid_orders"] or 0),
        "delivery_queue": int(row["delivery_queue"] or 0),
        "products": {
            key: {"name": value["name"], "amount": value["amount"], "currency": value["currency"]}
            for key, value in PRODUCTS.items()
        },
    }


def _mollie_key_mode() -> str:
    key = os.getenv("MOLLIE_API_KEY", "").strip()
    if key.startswith("test_"):
        return "test"
    if key.startswith("live_"):
        return "live"
    return "present_unknown" if key else "missing"


def _tls_probe(url: str, timeout_seconds: float = 8.0) -> dict[str, Any]:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    port = parsed.port or 443
    if parsed.scheme != "https" or not host:
        return {
            "host": host,
            "scheme": parsed.scheme or "",
            "tls_valid": False,
            "error": "https_url_required",
        }

    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=timeout_seconds) as sock:
            with context.wrap_socket(sock, server_hostname=host):
                pass
        return {"host": host, "scheme": "https", "tls_valid": True, "error": ""}
    except ssl.CertificateError:
        return {"host": host, "scheme": "https", "tls_valid": False, "error": "certificate_hostname_mismatch"}
    except ssl.SSLCertVerificationError:
        return {"host": host, "scheme": "https", "tls_valid": False, "error": "certificate_validation_failed"}
    except ssl.SSLError:
        return {"host": host, "scheme": "https", "tls_valid": False, "error": "tls_validation_failed"}
    except TimeoutError:
        return {"host": host, "scheme": "https", "tls_valid": False, "error": "tls_probe_timeout"}
    except OSError:
        return {"host": host, "scheme": "https", "tls_valid": False, "error": "tls_probe_failed"}


def _pm2_executable() -> str:
    return shutil.which("pm2") or shutil.which("pm2.cmd") or ""


def _pm2_process_status(required_names: tuple[str, ...] = ("duesight-payment", "duesight-delivery-worker")) -> dict[str, Any]:
    executable = _pm2_executable()
    if not executable:
        return {
            "available": False,
            "required": list(required_names),
            "processes": {},
            "missing": list(required_names),
            "not_online": [],
            "error": "pm2_missing",
        }

    try:
        completed = subprocess.run(
            [executable, "jlist"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception:
        return {
            "available": True,
            "required": list(required_names),
            "processes": {},
            "missing": list(required_names),
            "not_online": [],
            "error": "pm2_probe_failed",
        }
    if completed.returncode != 0:
        return {
            "available": True,
            "required": list(required_names),
            "processes": {},
            "missing": list(required_names),
            "not_online": [],
            "error": "pm2_jlist_failed",
        }

    try:
        rows = json.loads(completed.stdout or "[]")
    except Exception:
        rows = []

    seen: dict[str, dict[str, Any]] = {}
    for item in rows if isinstance(rows, list) else []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        if name not in required_names:
            continue
        env = item.get("pm2_env") if isinstance(item.get("pm2_env"), dict) else {}
        status = str(env.get("status") or item.get("status") or "")
        seen[name] = {"status": status, "online": status == "online"}

    missing = [name for name in required_names if name not in seen]
    not_online = [name for name, state in seen.items() if not state["online"]]
    return {
        "available": True,
        "required": list(required_names),
        "processes": seen,
        "missing": missing,
        "not_online": not_online,
        "error": "",
    }


def _http_json_probe(url: str, timeout_seconds: float = 8.0) -> tuple[dict[str, Any], dict[str, Any] | None]:
    parsed = urlparse(url)
    result: dict[str, Any] = {
        "host": parsed.hostname or "",
        "path": parsed.path or "/",
        "status_code": None,
        "json_ok": False,
        "error": "",
    }
    context = ssl._create_unverified_context() if parsed.scheme == "https" else None
    request = urllib.request.Request(url, headers={"User-Agent": "DueSightReadiness/1.0"})

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds, context=context) as response:
            body = response.read(4096)
            result["status_code"] = response.getcode()
    except urllib.error.HTTPError as exc:
        body = exc.read(4096)
        result["status_code"] = exc.code
    except TimeoutError:
        result["error"] = "route_probe_timeout"
        return result, None
    except OSError:
        result["error"] = "route_probe_failed"
        return result, None

    try:
        payload = json.loads(body.decode("utf-8"))
        if isinstance(payload, dict):
            result["json_ok"] = True
            return result, payload
    except Exception:
        pass
    return result, None


def _payment_service_probe(base_url: str) -> dict[str, Any]:
    base = base_url.rstrip("/")
    health, health_payload = _http_json_probe(f"{base}/health")
    products, products_payload = _http_json_probe(f"{base}/api/payment/products")
    health_ok = health["status_code"] == 200 and (health_payload or {}).get("service") == "DueSight Payment Server"
    products_ok = products["status_code"] == 200 and isinstance((products_payload or {}).get("products"), dict)

    return {
        "service_ready": health_ok and products_ok,
        "health": health,
        "products": products,
    }


def _local_payment_base_url() -> str:
    return os.getenv("DUESIGHT_LOCAL_PAYMENT_BASE_URL", "http://127.0.0.1:5051").strip().rstrip("/")


def live_readiness_status(
    check_network: bool = True,
    check_pm2: bool = True,
    check_local_service: bool = True,
) -> dict[str, Any]:
    """Return redacted launch-readiness checks for the paid delivery chain."""
    config = smoke_config_status()
    webhook_url = f"{BASE_URL}/api/payment/webhook"
    tls_checks = {
        "base_url": _tls_probe(BASE_URL) if check_network else {"skipped": True},
        "webhook_url": _tls_probe(webhook_url) if check_network else {"skipped": True},
    }
    payment_service = _payment_service_probe(BASE_URL) if check_network else {"skipped": True}
    local_payment_service = _payment_service_probe(_local_payment_base_url()) if check_local_service else {"skipped": True}
    pm2_status = _pm2_process_status() if check_pm2 else {"skipped": True}
    pm2_available = bool(pm2_status.get("available")) if check_pm2 else None
    pm2_ok = (
        bool(pm2_status.get("available"))
        and not pm2_status.get("missing")
        and not pm2_status.get("not_online")
        and not pm2_status.get("error")
    ) if check_pm2 else None

    blockers: list[str] = []
    if _mollie_key_mode() == "missing":
        blockers.append("mollie_api_key_missing")
    if not config["payment_admin_secret_present"]:
        blockers.append("payment_admin_secret_missing")
    if check_network:
        if not tls_checks["base_url"].get("tls_valid"):
            blockers.append("base_url_tls_invalid")
        if not tls_checks["webhook_url"].get("tls_valid"):
            blockers.append("webhook_tls_invalid")
        if not payment_service.get("service_ready"):
            blockers.append("payment_service_unreachable")
    if check_local_service and not local_payment_service.get("service_ready"):
        blockers.append("local_payment_service_unreachable")
    if not config["smtp_will_send"]:
        blockers.append("smtp_not_ready")
    if check_pm2 and not pm2_status.get("available"):
        blockers.append("pm2_missing")
    elif check_pm2 and not pm2_ok:
        blockers.append("pm2_processes_not_online")

    return {
        "status": "ready" if not blockers else "blocked",
        "ready": not blockers,
        "blockers": blockers,
        "mollie_key_mode": _mollie_key_mode(),
        "payment_admin_secret_present": config["payment_admin_secret_present"],
        "base_url": BASE_URL,
        "webhook_url": webhook_url,
        "tls": tls_checks,
        "payment_service": payment_service,
        "local_payment_base_url": _local_payment_base_url(),
        "local_payment_service": local_payment_service,
        "smtp_send_enabled": config["smtp_send_enabled"],
        "smtp_config_present": config["smtp_config_present"],
        "smtp_will_send": config["smtp_will_send"],
        "pm2_available": pm2_available,
        "pm2": pm2_status,
        "orders_total": config["orders_total"],
        "paid_orders": config["paid_orders"],
        "delivery_queue": config["delivery_queue"],
    }


def _redact_webhook_result(result: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(result)
    for key in ("payment_id", "mollie_id", "checkout_url"):
        redacted.pop(key, None)
    return redacted


def _redact_checkout_result(result: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(result)
    for key in ("payment_id", "mollie_id", "checkout_url"):
        redacted.pop(key, None)
    redacted["checkout_created"] = True
    return redacted


def _redact_refund_result(result: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(result)
    for key in ("payment_id", "mollie_id", "refund_id"):
        redacted.pop(key, None)
    return redacted


def _redact_cleanup_result(result: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(result)
    order_ids = redacted.pop("order_ids", [])
    redacted["orders_affected"] = len(order_ids)
    redacted["order_ids_redacted"] = bool(order_ids)
    return redacted


def create_checkout_order(
    body: dict[str, Any],
    client_ip: str = "",
    user_agent: str = "",
) -> dict[str, Any]:
    _init_db()
    if body.get("terms_accepted") is not True:
        raise ValueError("terms_acceptance_required")

    item = _product(body.get("product") or body.get("tier"))
    company_name = str(body.get("company_name") or body.get("company") or "").strip()
    customer_email = str(body.get("customer_email") or body.get("email") or "").strip().lower()
    if len(company_name) < 2:
        raise ValueError("company_name_required")
    if "@" not in customer_email:
        raise ValueError("customer_email_required")

    order_id = "ds_" + secrets.token_urlsafe(12).replace("-", "").replace("_", "")[:18]
    accepted_at = _now()
    terms_payload = {
        "order_id": order_id,
        "company_name": company_name,
        "customer_email": customer_email,
        "accepted_at": accepted_at,
        "terms_version": TERMS_VERSION,
        "privacy_version": PRIVACY_VERSION,
        "ip": client_ip,
        "user_agent": user_agent,
    }
    acceptance_hash = _hash_terms_acceptance(terms_payload)
    metadata = {
        "order_id": order_id,
        "product": item["key"],
        "company_name": company_name,
        "kvk_number": str(body.get("kvk_number") or body.get("kvk") or "").strip(),
        "domain": str(body.get("domain") or "").strip(),
        "customer_email": customer_email,
        "terms_acceptance": {
            "accepted": True,
            "accepted_at": accepted_at,
            "terms_version": TERMS_VERSION,
            "privacy_version": PRIVACY_VERSION,
            "hash": acceptance_hash,
        },
        "terms_acceptance_hash": acceptance_hash,
    }

    redirect_url = (
        f"{BASE_URL}/?payment=success&status=pending"
        f"&order_id={quote(order_id)}&domain={quote(metadata['domain'])}&tier={quote(item['tier'])}"
    )
    webhook_url = f"{BASE_URL}/api/payment/webhook"
    payment_data = {
        "amount": {"currency": item["currency"], "value": item["amount"]},
        "description": f"{item['name']} - {company_name}",
        "redirectUrl": redirect_url,
        "webhookUrl": webhook_url,
        "metadata": metadata,
    }

    # Outbound idempotency: derive a stable Idempotency-Key per order_id so that
    # network retries between create_checkout_order and Mollie's POST /v2/payments
    # produce a single Mollie payment (Mollie dedups on the key for 24h).
    payment = _mollie().payments.create(
        payment_data,
        idempotency_key=f"duesight-order-{order_id}",
    )

    mollie_id = str(_payment_value(payment, "id", ""))
    checkout_url = _payment_checkout_url(payment)
    if not mollie_id or not checkout_url:
        raise RuntimeError("mollie_payment_incomplete")

    conn = _db()
    conn.execute(
        """INSERT INTO orders
           (order_id, mollie_id, product, company_name, kvk_number, domain,
            customer_email, amount, currency, status, scan_status, metadata,
            created_at, updated_at, terms_accepted_at, terms_version,
            privacy_version, terms_ip, terms_user_agent, terms_acceptance_hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            order_id,
            mollie_id,
            item["key"],
            company_name,
            metadata["kvk_number"],
            metadata["domain"],
            customer_email,
            item["amount"],
            item["currency"],
            "pending",
            "pending",
            json.dumps(metadata, ensure_ascii=True),
            accepted_at,
            accepted_at,
            accepted_at,
            TERMS_VERSION,
            PRIVACY_VERSION,
            terms_payload["ip"],
            terms_payload["user_agent"],
            acceptance_hash,
        ),
    )
    conn.commit()
    conn.close()
    _log_event(order_id, mollie_id, "checkout_created", {"product": item["key"]})

    return {
        "order_id": order_id,
        "payment_id": mollie_id,
        "checkout_url": checkout_url,
        "status": "pending",
        "product": item["key"],
        "amount": item["amount"],
        "currency": item["currency"],
    }


@payment_router.get("/products")
async def products() -> dict[str, Any]:
    return {"products": PRODUCTS}


@payment_router.post("/create")
async def create_payment(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}

    try:
        return create_checkout_order(body, client_ip=_client_ip(request), user_agent=request.headers.get("user-agent", ""))
    except ValueError as exc:
        code = str(exc)
        messages = {
            "terms_acceptance_required": "Terms and privacy acceptance is required before checkout.",
            "company_name_required": "company_name is required",
            "customer_email_required": "customer_email is required",
        }
        return _json_response(
            400,
            code=code,
            error=messages.get(code, code),
            terms_version=TERMS_VERSION,
            privacy_version=PRIVACY_VERSION,
        )
    except Exception as exc:
        if str(exc) == "mollie_payment_incomplete":
            return _json_response(502, code="mollie_payment_incomplete", error="Mollie payment response is incomplete.")
        return _json_response(503, code="mollie_unavailable", error=str(exc)[:160])


@payment_router.post("/webhook")
async def payment_webhook(id: str = Form(...)) -> dict[str, Any]:
    _init_db()
    payment_id = id.strip()
    row = _order_by_mollie_id(payment_id)
    if not row:
        _log_event("", payment_id, "unknown_payment_webhook", {})
        return {"status": "unknown_payment"}

    conn = _db()
    conn.execute(
        "UPDATE orders SET webhook_count = webhook_count + 1, updated_at = ? WHERE order_id = ?",
        (_now(), row["order_id"]),
    )
    conn.commit()
    conn.close()

    # Inbound exactly-once guard. Mollie may redeliver the same webhook
    # (network retry, dashboard replay, duplicate delivery). The duplicate
    # check below uses the freshly fetched payment status (not the cached
    # row from the top of the handler) so that terminal-status webhooks
    # on an already-paid order still get differentiated
    # (terminal_status_ignored_after_paid) rather than being collapsed into
    # duplicate_paid_ignored. Side-effects (queue_scan_order / notify_admin)
    # are guarded by the current["status"] check below, not by webhook_count.
    try:
        payment = _mollie().payments.get(payment_id)
    except Exception as exc:
        _log_event(row["order_id"], payment_id, "payment_fetch_failed", {"error": str(exc)[:160]})
        return {"status": "payment_fetch_failed"}

    status = _payment_status(payment)
    pay_value, pay_currency = _payment_amount(payment)

    if status == "paid":
        if pay_value != row["amount"] or pay_currency != row["currency"]:
            conn = _db()
            conn.execute(
                "UPDATE orders SET last_webhook_action = ?, updated_at = ? WHERE order_id = ?",
                ("amount_mismatch", _now(), row["order_id"]),
            )
            conn.commit()
            conn.close()
            _log_event(
                row["order_id"],
                payment_id,
                "amount_mismatch",
                {"expected": row["amount"], "actual": pay_value, "currency": pay_currency},
            )
            return {"status": "amount_mismatch"}

        current = _order_by_mollie_id(payment_id)
        if current and current["status"] in {"paid", "refunded"}:
            conn = _db()
            conn.execute(
                "UPDATE orders SET last_webhook_action = ?, updated_at = ? WHERE order_id = ?",
                ("duplicate_paid_ignored", _now(), row["order_id"]),
            )
            conn.commit()
            conn.close()
            _log_event(row["order_id"], payment_id, "duplicate_paid_ignored", {})
            return {"status": "duplicate"}

        _log_event(row["order_id"], payment_id, "paid_queueing", {})
        conn = _db()
        conn.execute(
            """UPDATE orders
               SET status = ?, scan_status = ?, last_webhook_action = ?, updated_at = ?
               WHERE order_id = ?""",
            ("paid", "queueing", "paid_queueing", _now(), row["order_id"]),
        )
        conn.commit()
        conn.close()

        _queue_scan_order(
            order_id=row["order_id"],
            product=row["product"],
            company_name=row["company_name"],
            kvk_number=row["kvk_number"],
            domain=row["domain"],
            email=row["customer_email"],
            uploads=_uploads_for_order(row["order_id"]),
        )
        _notify_admin(order_id=row["order_id"], company_name=row["company_name"], email=row["customer_email"])

        conn = _db()
        conn.execute(
            """UPDATE orders
               SET scan_status = ?, last_webhook_action = ?, updated_at = ?
               WHERE order_id = ?""",
            ("queued", "paid_queued", _now(), row["order_id"]),
        )
        conn.commit()
        conn.close()
        _log_event(row["order_id"], payment_id, "paid_queued", {})
        return {"status": "paid", "action": "queued"}

    if status in {"failed", "expired", "canceled", "cancelled"}:
        if row["status"] in {"paid", "refunded"}:
            conn = _db()
            conn.execute(
                "UPDATE orders SET last_webhook_action = ?, updated_at = ? WHERE order_id = ?",
                ("terminal_status_ignored_after_paid", _now(), row["order_id"]),
            )
            conn.commit()
            conn.close()
            _log_event(row["order_id"], payment_id, "terminal_status_ignored_after_paid", {"status": status})
            return {"status": "ignored_paid"}

        local_status = "canceled" if status == "cancelled" else status
        conn = _db()
        conn.execute(
            """UPDATE orders
               SET status = ?, scan_status = ?, last_webhook_action = ?, updated_at = ?
               WHERE order_id = ?""",
            (local_status, "cancelled", f"payment_{local_status}", _now(), row["order_id"]),
        )
        conn.commit()
        conn.close()
        _log_event(row["order_id"], payment_id, f"payment_{local_status}", {})
        return {"status": local_status}

    conn = _db()
    conn.execute(
        "UPDATE orders SET last_webhook_action = ?, updated_at = ? WHERE order_id = ?",
        (f"payment_{status}", _now(), row["order_id"]),
    )
    conn.commit()
    conn.close()
    _log_event(row["order_id"], payment_id, f"payment_{status}", {})
    return {"status": status}


@payment_router.get("/status/{order_id}")
async def payment_status(order_id: str, customer_email: str = "") -> dict[str, Any]:
    _init_db()
    row = _order_by_id(order_id)
    if not row:
        raise HTTPException(status_code=404, detail="order not found")
    if customer_email.strip().lower() != str(row["customer_email"]).lower():
        raise HTTPException(status_code=403, detail="email does not match order")
    return {
        "order_id": row["order_id"],
        "status": row["status"],
        "scan_status": row["scan_status"],
        "delivery_status": row["delivery_status"],
        "upload_status": row["upload_status"],
    }


@payment_router.post("/delivery/complete")
async def complete_delivery(request: Request):
    _require_payment_admin(request)
    _init_db()
    body = await request.json()
    order_id = str(body.get("order_id") or "").strip()
    report_url = str(body.get("report_url") or "").strip()
    report_path = str(body.get("report_path") or "").strip()
    send_email = bool(body.get("send_email", True))

    try:
        return complete_delivery_order(order_id, report_url=report_url, report_path=report_path, send_email=send_email)
    except ValueError as exc:
        if str(exc) == "Order not found":
            return _json_response(404, error=str(exc))
        return _json_response(400, error=str(exc))
    except PermissionError as exc:
        return _json_response(409, error=str(exc))
    except FileNotFoundError as exc:
        return _json_response(400, error=str(exc))


@payment_router.post("/delivery/process/{order_id}")
async def process_delivery_order_endpoint(order_id: str, request: Request):
    _require_payment_admin(request)
    result = run_delivery_for_order(order_id)
    if result["status"] == "not_found":
        return _json_response(404, error="Order not found")
    if result["status"] == "not_paid":
        return _json_response(409, error="Order is not paid")
    if result["status"] == "failed":
        return _json_response(500, **result)
    return result


@payment_router.get("/delivery-link/{order_id}")
async def delivery_link(order_id: str, token: str) -> dict[str, Any]:
    _init_db()
    row = _order_by_id(order_id)
    if not row:
        raise HTTPException(status_code=404, detail="order not found")
    if not row["delivery_token_hash"] or not hmac.compare_digest(row["delivery_token_hash"], _token_hash(token)):
        raise HTTPException(status_code=403, detail="invalid delivery token")
    return {
        "order_id": row["order_id"],
        "report_url": row["report_url"],
        "delivery_status": row["delivery_status"],
    }


@payment_router.get("/report-file/{order_id}")
async def report_file(order_id: str, token: str):
    _init_db()
    row = _order_by_id(order_id)
    if not row:
        raise HTTPException(status_code=404, detail="order not found")
    if not row["delivery_token_hash"] or not hmac.compare_digest(row["delivery_token_hash"], _token_hash(token)):
        raise HTTPException(status_code=403, detail="invalid delivery token")
    if not row["report_path"]:
        raise HTTPException(status_code=404, detail="local report file not configured")
    path = Path(row["report_path"]).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="local report file not found")
    return FileResponse(path, filename=path.name)


@payment_router.post("/refund/request")
async def refund_request(request: Request):
    _init_db()
    body = await request.json()
    order_id = str(body.get("order_id") or "").strip()
    customer_email = str(body.get("customer_email") or "").strip().lower()
    reason = str(body.get("reason") or "").strip()
    row = _order_by_id(order_id)
    if not row:
        return _json_response(404, error="Order not found")
    if customer_email != str(row["customer_email"]).lower():
        return _json_response(403, error="Email does not match order")

    now = _now()
    if row["status"] != "paid":
        conn = _db()
        conn.execute(
            """UPDATE orders
               SET status = ?, refund_status = ?, refund_resolution = ?,
                   refund_resolved_at = ?, updated_at = ?
               WHERE order_id = ?""",
            ("canceled", "canceled", "customer_cancelled_before_payment", now, now, order_id),
        )
        conn.commit()
        conn.close()
        _log_event(order_id, row["mollie_id"], "cancellation_recorded", {"reason": reason})
        return {"status": "cancellation_recorded"}

    conn = _db()
    conn.execute(
        """UPDATE orders
           SET refund_status = ?, refund_reason = ?, refund_contact_email = ?,
               refund_requested_at = ?, updated_at = ?
           WHERE order_id = ?""",
        ("requested", reason, customer_email, now, now, order_id),
    )
    conn.commit()
    conn.close()
    _log_event(order_id, row["mollie_id"], "refund_requested", {"reason": reason})
    _write_jsonl(
        SUPPORT_EVENTS_FILE,
        {"type": "refund_requested", "order_id": order_id, "reason": reason, "created_at": now},
    )
    return {"status": "refund_requested"}


@payment_router.post("/refund/resolve")
async def refund_resolve(request: Request):
    _require_payment_admin(request)
    _init_db()
    body = await request.json()
    order_id = str(body.get("order_id") or "").strip()
    decision = str(body.get("decision") or "").strip().lower()
    note = str(body.get("note") or "").strip()
    row = _order_by_id(order_id)
    if not row:
        return _json_response(404, error="Order not found")
    if decision not in {"refunded", "rejected"}:
        return _json_response(400, error="decision must be refunded or rejected")

    if decision == "refunded":
        refund_amount = str(body.get("amount") or "").strip()
        allow_live_refund = body.get("allow_live_refund") is True
        try:
            result = create_mollie_refund_for_order(
                order_id,
                amount=refund_amount,
                note=note,
                allow_live=allow_live_refund,
            )
        except ValueError as exc:
            code = str(exc)
            if code == "order_not_found":
                return _json_response(404, code=code, error="Order not found")
            if code == "order_not_paid":
                return _json_response(409, code=code, error="Order is not paid")
            return _json_response(400, code=code, error=code)
        except PermissionError as exc:
            code = str(exc)
            return _json_response(409, code=code, error="Live Mollie refund requires explicit allow_live_refund.")
        except RuntimeError as exc:
            code = str(exc)
            return _json_response(503, code=code, error="Mollie refund could not be created.")
        return _redact_refund_result(result)

    now = _now()
    conn = _db()
    conn.execute(
        """UPDATE orders
           SET refund_status = ?, refund_resolution = ?, refund_resolved_at = ?, updated_at = ?
           WHERE order_id = ?""",
        ("rejected", note, now, now, order_id),
    )
    conn.commit()
    conn.close()
    _log_event(order_id, row["mollie_id"], "refund_rejected", {"note": note})
    return {"status": "rejected"}


@payment_router.post("/orders/{order_id}/uploads")
async def upload_order_file(
    order_id: str,
    customer_email: str = Form(...),
    file: UploadFile = File(...),
):
    _init_db()
    row = _order_by_id(order_id)
    if not row:
        return _json_response(404, error="Order not found")
    if customer_email.strip().lower() != str(row["customer_email"]).lower():
        return _json_response(403, error="Email does not match order")
    if reason := _upload_block_reason(row):
        return _json_response(409, code=reason, error="Order is not open for uploads")
    if _upload_count_for_order(order_id) >= MAX_UPLOADS_PER_ORDER:
        return _json_response(409, code="upload_limit_reached", error="Upload limit reached for this order")

    original_name = Path(file.filename or "upload.bin").name
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        return _json_response(400, code="unsupported_file_type", error="Unsupported upload file type")

    content = await file.read()
    size = len(content)
    if size <= 0:
        return _json_response(400, code="empty_upload", error="Upload is empty")
    if size > MAX_UPLOAD_BYTES:
        return _json_response(413, code="upload_too_large", error="Upload exceeds configured limit")

    digest = hashlib.sha256(content).hexdigest()
    upload_id = "up_" + secrets.token_urlsafe(12).replace("-", "").replace("_", "")[:18]
    safe_order = _safe_slug(order_id, "order")
    safe_file = _safe_slug(original_name, "upload")
    target_dir = UPLOAD_DIR / safe_order
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{upload_id}_{safe_file}"
    target_path.write_bytes(content)

    content_type = file.content_type or mimetypes.guess_type(original_name)[0] or "application/octet-stream"
    now = _now()
    conn = _db()
    conn.execute(
        """INSERT INTO order_uploads
           (upload_id, order_id, original_filename, stored_path, content_type,
            size_bytes, sha256, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (upload_id, order_id, original_name, str(target_path), content_type, size, digest, now),
    )
    conn.execute(
        "UPDATE orders SET upload_status = ?, updated_at = ? WHERE order_id = ?",
        ("uploaded", now, order_id),
    )
    conn.commit()
    conn.close()
    _log_event(order_id, row["mollie_id"], "customer_upload_received", {"upload_id": upload_id})

    return {
        "status": "uploaded",
        "upload_id": upload_id,
        "order_id": order_id,
        "filename": original_name,
        "size_bytes": size,
        "sha256": digest,
    }


@payment_router.get("/orders/{order_id}/uploads")
async def list_order_uploads(order_id: str, customer_email: str) -> dict[str, Any]:
    _init_db()
    row = _order_by_id(order_id)
    if not row:
        raise HTTPException(status_code=404, detail="order not found")
    if customer_email.strip().lower() != str(row["customer_email"]).lower():
        raise HTTPException(status_code=403, detail="email does not match order")

    conn = _db()
    rows = conn.execute(
        """SELECT upload_id, original_filename, content_type, size_bytes, sha256, created_at
           FROM order_uploads WHERE order_id = ? ORDER BY id DESC""",
        (order_id,),
    ).fetchall()
    conn.close()
    return {"order_id": order_id, "uploads": [dict(item) for item in rows]}


def create_app() -> FastAPI:
    app = FastAPI(title="DueSight Payment Server", version="1.0.0")
    # OWASP security headers. Mollie is already in DEFAULT_CSP
    # (connect-src + form-action + Permissions-Policy).
    app.add_middleware(SecurityHeadersMiddleware)
    app.include_router(payment_router, prefix="/api/payment", tags=["Payment"])

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"service": "DueSight Payment Server", "status": "ok"}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "DueSight Payment Server"}

    @app.get("/api/checkout")
    async def legacy_checkout(tier: str = "compact", domain: str = "", email: str = "") -> JSONResponse:
        return _json_response(
            410,
            code="checkout_requires_terms_acceptance",
            error="Use POST /api/payment/create with terms_accepted=true.",
            tier=tier,
            domain=domain,
            email=email,
        )

    return app


app = create_app()


def _run_worker_loop(interval_seconds: int, limit: int) -> None:
    while True:
        results = process_delivery_queue(limit=limit)
        if results:
            print(json.dumps({"processed": results}, ensure_ascii=True), flush=True)
        time.sleep(interval_seconds)


def _static_report_runner(report_url: str = "", report_path: str = ""):
    def runner(order: dict[str, Any]) -> dict[str, str]:
        return {"report_url": report_url, "report_path": report_path}

    return runner


if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="DueSight payment and delivery service")
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Run the payment FastAPI server")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=5051)

    once_parser = subparsers.add_parser("worker-once", help="Process the delivery queue once")
    once_parser.add_argument("--limit", type=int, default=10)
    once_parser.add_argument("--report-url", default="", help="Use a static report URL for smoke tests")
    once_parser.add_argument("--report-path", default="", help="Use a static local report file for smoke tests")
    once_parser.add_argument("--no-email", action="store_true", help="Do not send/write delivery email for this run")

    loop_parser = subparsers.add_parser("worker-loop", help="Continuously process the delivery queue")
    loop_parser.add_argument("--limit", type=int, default=10)
    loop_parser.add_argument("--interval", type=int, default=DELIVERY_WORKER_INTERVAL_SECONDS)
    loop_parser.add_argument("--report-url", default="", help="Use a static report URL for smoke tests")
    loop_parser.add_argument("--report-path", default="", help="Use a static local report file for smoke tests")
    loop_parser.add_argument("--no-email", action="store_true", help="Do not send/write delivery email for this run")

    subparsers.add_parser("smoke-config", help="Print redacted payment/delivery readiness config")

    readiness_parser = subparsers.add_parser("readiness-check", help="Print redacted launch readiness checks")
    readiness_parser.add_argument("--skip-network", action="store_true", help="Skip TLS/network probes")
    readiness_parser.add_argument("--skip-pm2", action="store_true", help="Skip local pm2 availability check")
    readiness_parser.add_argument("--skip-local-service", action="store_true", help="Skip local payment service health probe")
    readiness_parser.add_argument("--fail-on-blocked", action="store_true", help="Exit non-zero when readiness is blocked")

    email_parser = subparsers.add_parser("email-smoke", help="Send or queue a redacted controlled email smoke")
    email_parser.add_argument("--to", required=True, help="Controlled recipient inbox")
    email_parser.add_argument("--allow-send", action="store_true", help="Actually send via SMTP when SMTP env is enabled")

    checkout_parser = subparsers.add_parser("checkout-smoke", help="Create a redacted Mollie checkout smoke payment")
    checkout_parser.add_argument("--product", default="compact")
    checkout_parser.add_argument("--company", required=True)
    checkout_parser.add_argument("--email", required=True)
    checkout_parser.add_argument("--domain", default="")
    checkout_parser.add_argument("--kvk", default="")
    checkout_parser.add_argument("--terms-accepted", action="store_true")
    checkout_parser.add_argument("--allow-live", action="store_true", help="Allow live_* Mollie keys for this smoke")

    replay_parser = subparsers.add_parser("webhook-replay", help="Replay a Mollie webhook payment id locally")
    replay_parser.add_argument("--payment-id", required=True)

    refund_parser = subparsers.add_parser("refund-smoke", help="Create a redacted Mollie refund for a paid order")
    refund_parser.add_argument("--order-id", required=True)
    refund_parser.add_argument("--amount", default="", help="Refund amount, defaults to the order amount")
    refund_parser.add_argument("--note", default="DueSight refund smoke")
    refund_parser.add_argument("--allow-live", action="store_true", help="Allow live_* Mollie keys for this refund smoke")

    cleanup_parser = subparsers.add_parser("cleanup-uploads", help="Dry-run or purge stale unpaid customer uploads")
    cleanup_parser.add_argument("--retention-hours", type=int, default=STALE_UPLOAD_RETENTION_HOURS)
    cleanup_parser.add_argument("--execute", action="store_true", help="Actually delete eligible upload files and rows")

    args = parser.parse_args()
    command = args.command or "serve"
    if command == "worker-once":
        runner = _static_report_runner(args.report_url, args.report_path) if args.report_url or args.report_path else None
        print(json.dumps({"processed": process_delivery_queue(limit=args.limit, report_runner=runner, send_email=not args.no_email)}, ensure_ascii=True))
    elif command == "worker-loop":
        if args.report_url or args.report_path:
            while True:
                runner = _static_report_runner(args.report_url, args.report_path)
                results = process_delivery_queue(limit=args.limit, report_runner=runner, send_email=not args.no_email)
                if results:
                    print(json.dumps({"processed": results}, ensure_ascii=True), flush=True)
                time.sleep(args.interval)
        else:
            _run_worker_loop(interval_seconds=args.interval, limit=args.limit)
    elif command == "smoke-config":
        print(json.dumps(smoke_config_status(), ensure_ascii=True, indent=2))
    elif command == "readiness-check":
        readiness = live_readiness_status(
            check_network=not args.skip_network,
            check_pm2=not args.skip_pm2,
            check_local_service=not args.skip_local_service,
        )
        print(json.dumps(readiness, ensure_ascii=True, indent=2))
        if args.fail_on_blocked and not readiness["ready"]:
            sys.exit(3)
    elif command == "email-smoke":
        try:
            result = run_email_smoke(args.to, allow_send=args.allow_send)
        except ValueError as exc:
            print(json.dumps({"status": "error", "code": str(exc)}, ensure_ascii=True, indent=2))
            sys.exit(1)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        if args.allow_send and result["status"] != "smtp_sent":
            sys.exit(2)
    elif command == "checkout-smoke":
        if os.getenv("MOLLIE_API_KEY", "").strip().startswith("live_") and not args.allow_live:
            print(
                json.dumps(
                    {
                        "status": "refused",
                        "code": "live_key_requires_allow_live",
                        "checkout_created": False,
                    },
                    ensure_ascii=True,
                    indent=2,
                )
            )
            sys.exit(2)

        try:
            result = create_checkout_order(
                {
                    "product": args.product,
                    "company_name": args.company,
                    "customer_email": args.email,
                    "domain": args.domain,
                    "kvk_number": args.kvk,
                    "terms_accepted": args.terms_accepted,
                },
                client_ip="cli",
                user_agent="payment_server.py checkout-smoke",
            )
        except ValueError as exc:
            print(
                json.dumps(
                    {
                        "status": "error",
                        "code": str(exc),
                        "checkout_created": False,
                        "terms_version": TERMS_VERSION,
                        "privacy_version": PRIVACY_VERSION,
                    },
                    ensure_ascii=True,
                    indent=2,
                )
            )
            sys.exit(1)
        except HTTPException as exc:
            print(
                json.dumps(
                    {
                        "status": "error",
                        "code": "unsupported_product",
                        "error": str(exc.detail)[:160],
                        "checkout_created": False,
                    },
                    ensure_ascii=True,
                    indent=2,
                )
            )
            sys.exit(1)
        except Exception as exc:
            code = "mollie_payment_incomplete" if str(exc) == "mollie_payment_incomplete" else "mollie_unavailable"
            print(
                json.dumps(
                    {
                        "status": "error",
                        "code": code,
                        "error": "Mollie checkout could not be created.",
                        "checkout_created": False,
                    },
                    ensure_ascii=True,
                    indent=2,
                )
            )
            sys.exit(1)

        print(json.dumps(_redact_checkout_result(result), ensure_ascii=True, indent=2))
    elif command == "webhook-replay":
        result = asyncio.run(payment_webhook(id=args.payment_id))
        print(json.dumps(_redact_webhook_result(result), ensure_ascii=True, indent=2))
    elif command == "refund-smoke":
        try:
            result = create_mollie_refund_for_order(
                order_id=args.order_id,
                amount=args.amount,
                note=args.note,
                allow_live=args.allow_live,
            )
        except PermissionError as exc:
            print(json.dumps({"status": "refused", "code": str(exc), "refund_created": False}, ensure_ascii=True, indent=2))
            sys.exit(2)
        except ValueError as exc:
            print(json.dumps({"status": "error", "code": str(exc), "refund_created": False}, ensure_ascii=True, indent=2))
            sys.exit(1)
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "status": "error",
                        "code": str(exc)[:80],
                        "refund_created": False,
                    },
                    ensure_ascii=True,
                    indent=2,
                )
            )
            sys.exit(1)
        print(json.dumps(_redact_refund_result(result), ensure_ascii=True, indent=2))
    elif command == "cleanup-uploads":
        result = cleanup_stale_uploads(retention_hours=args.retention_hours, dry_run=not args.execute)
        print(json.dumps(_redact_cleanup_result(result), ensure_ascii=True, indent=2))
    else:
        uvicorn.run(
            "payment_server:app",
            host=getattr(args, "host", "127.0.0.1"),
            port=getattr(args, "port", 5051),
            reload=False,
            server_header=False,
            date_header=False,
        )
