"""Webhook delivery + registration for scan_server.

Self-contained module: SQLite store + HMAC-SHA256 signature + retry/backoff.
Pattern mirrors duesight-agent/tools/webhook_delivery.py but works standalone
in the website service without cross-package imports.

Endpoints exposed via scan_server.py:
    POST   /api/v1/webhooks/register
    DELETE /api/v1/webhooks/{webhook_id}
    GET    /api/v1/webhooks
    POST   /api/v1/webhooks/{webhook_id}/test

Events emitted:
    search.completed â€” after every teaser_scan
    search.failed    â€” on scan exception
    payment.succeeded â€” after Mollie webhook
    monitoring.alert  â€” on counterparty delta (future)
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger("duesight.webhooks")

WEBHOOK_DB = Path(__file__).parent.parent.parent / ".webhook_store.db"
DEFAULT_TIMEOUT = 20  # seconds
MAX_RETRIES = 3
RETRY_DELAYS = [5, 30, 120]  # exponential-ish backoff
USER_AGENT = "DueSight-Webhook/1.0"
SUPPORTED_EVENTS = (
    "search.completed",
    "search.failed",
    "payment.succeeded",
    "monitoring.alert",
    "webhook.test",
)


def _init_db() -> None:
    conn = sqlite3.connect(str(WEBHOOK_DB))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS webhooks (
            webhook_id   TEXT PRIMARY KEY,
            url          TEXT NOT NULL,
            secret_hash  TEXT NOT NULL,
            secret_raw   TEXT NOT NULL,
            events       TEXT NOT NULL,
            owner_email  TEXT DEFAULT '',
            created_at   TEXT NOT NULL,
            last_delivery TEXT DEFAULT '',
            delivery_count INTEGER DEFAULT 0,
            failure_count INTEGER DEFAULT 0,
            enabled      INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS delivery_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            webhook_id   TEXT NOT NULL,
            event        TEXT NOT NULL,
            status_code  INTEGER DEFAULT 0,
            success      INTEGER DEFAULT 0,
            error        TEXT DEFAULT '',
            attempts     INTEGER DEFAULT 0,
            timestamp    TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_dlog_webhook ON delivery_log(webhook_id);
        CREATE INDEX IF NOT EXISTS idx_dlog_time ON delivery_log(timestamp);
    """)
    conn.commit()
    conn.close()


_init_db()


def sign_payload(payload: dict, secret: str) -> str:
    """HMAC-SHA256 signature of canonical JSON payload."""
    payload_bytes = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode()
    sig = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def verify_signature(payload: dict, signature: str, secret: str) -> bool:
    expected = sign_payload(payload, secret)
    return hmac.compare_digest(expected, signature)


def register_webhook(
    url: str,
    events: list[str] | None = None,
    owner_email: str = "",
) -> dict:
    """Register a new webhook. Returns webhook_id + secret (shown once)."""
    if not url.startswith(("http://", "https://")):
        raise ValueError("Webhook URL must be http(s)")

    # Reject internal/loopback URLs unless in dev mode
    import os as _os
    if _os.environ.get("DUESIGHT_ENV") != "development":
        lower = url.lower()
        if any(host in lower for host in ("localhost", "127.0.0.1", "0.0.0.0", "::1")):
            raise ValueError("Loopback URLs not allowed in production")

    if not events:
        events = ["search.completed", "search.failed"]

    # Validate events
    for e in events:
        if e not in SUPPORTED_EVENTS:
            raise ValueError(f"Unsupported event: {e}. Supported: {SUPPORTED_EVENTS}")

    webhook_id = "wh_" + hashlib.sha256((url + str(time.time())).encode()).hexdigest()[:24]
    secret = uuid.uuid4().hex + uuid.uuid4().hex  # 64 chars
    secret_hash = hashlib.sha256(secret.encode()).hexdigest()

    conn = sqlite3.connect(str(WEBHOOK_DB))
    conn.execute(
        """INSERT INTO webhooks (webhook_id, url, secret_hash, secret_raw, events,
                                  owner_email, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (webhook_id, url, secret_hash, secret, ",".join(events),
         owner_email, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()

    logger.info(f"Webhook registered: {webhook_id} â†’ {url}")
    return {
        "webhook_id": webhook_id,
        "secret": secret,  # ONLY returned once at registration
        "url": url,
        "events": events,
        "created_at": datetime.utcnow().isoformat(),
        "note": "Save the secret â€” it is only shown once. Use it to verify X-DueSight-Signature.",
    }


def unregister_webhook(webhook_id: str) -> bool:
    conn = sqlite3.connect(str(WEBHOOK_DB))
    cur = conn.execute("DELETE FROM webhooks WHERE webhook_id = ?", (webhook_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def list_webhooks(owner_email: str = "") -> list[dict]:
    conn = sqlite3.connect(str(WEBHOOK_DB))
    conn.row_factory = sqlite3.Row
    if owner_email:
        rows = conn.execute(
            """SELECT webhook_id, url, events, owner_email, created_at,
                      last_delivery, delivery_count, failure_count, enabled
               FROM webhooks WHERE owner_email = ?""",
            (owner_email,),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT webhook_id, url, events, owner_email, created_at,
                      last_delivery, delivery_count, failure_count, enabled
               FROM webhooks"""
        ).fetchall()
    conn.close()

    return [
        {
            "webhook_id": r["webhook_id"],
            "url": r["url"],
            "events": r["events"].split(","),
            "owner_email": r["owner_email"],
            "created_at": r["created_at"],
            "last_delivery": r["last_delivery"],
            "delivery_count": r["delivery_count"],
            "failure_count": r["failure_count"],
            "enabled": bool(r["enabled"]),
        }
        for r in rows
    ]


def _get_webhook(webhook_id: str) -> Optional[dict]:
    conn = sqlite3.connect(str(WEBHOOK_DB))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM webhooks WHERE webhook_id = ? AND enabled = 1",
        (webhook_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def _log_delivery(
    webhook_id: str,
    event: str,
    status_code: int,
    success: bool,
    error: str,
    attempts: int,
) -> None:
    conn = sqlite3.connect(str(WEBHOOK_DB))
    conn.execute(
        """INSERT INTO delivery_log (webhook_id, event, status_code, success,
                                      error, attempts, timestamp)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (webhook_id, event, status_code, int(success), error, attempts,
         datetime.utcnow().isoformat()),
    )
    if success:
        conn.execute(
            """UPDATE webhooks SET last_delivery = ?, delivery_count = delivery_count + 1
               WHERE webhook_id = ?""",
            (datetime.utcnow().isoformat(), webhook_id),
        )
    else:
        conn.execute(
            "UPDATE webhooks SET failure_count = failure_count + 1 WHERE webhook_id = ?",
            (webhook_id,),
        )
    conn.commit()
    conn.close()


async def _deliver_one(webhook: dict, event: str, payload: dict, timeout: int = DEFAULT_TIMEOUT) -> bool:
    """Single webhook delivery with retry/backoff. Logs every attempt."""
    url = webhook["url"]
    secret = webhook["secret_raw"]
    webhook_id = webhook["webhook_id"]

    body = {
        "event": event,
        "delivery_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "webhook_id": webhook_id,
        "data": payload,
    }
    headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json",
        "X-DueSight-Version": "1.0",
        "X-DueSight-Event": event,
        "X-DueSight-Signature": sign_payload(body, secret),
        "X-Delivery-ID": body["delivery_id"],
    }

    last_error = ""
    status_code = 0

    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                resp = await client.post(url, json=body, headers=headers)
                status_code = resp.status_code
                if 200 <= resp.status_code < 400:
                    _log_delivery(webhook_id, event, resp.status_code, True, "", attempt + 1)
                    logger.info(f"Webhook OK: {webhook_id} {event} â†’ {url} [{resp.status_code}]")
                    return True
                last_error = f"HTTP {resp.status_code}"
                # Retry only on 5xx
                if resp.status_code >= 500 and attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)])
                    continue
                break
        except httpx.TimeoutException:
            last_error = f"timeout after {timeout}s"
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)])
        except Exception as e:
            last_error = f"{type(e).__name__}: {str(e)[:100]}"
            break

    _log_delivery(webhook_id, event, status_code, False, last_error, attempt + 1)
    logger.warning(f"Webhook FAIL: {webhook_id} {event} â†’ {url}: {last_error}")
    return False


async def emit_event(event: str, payload: dict) -> None:
    """Fire-and-forget event emission to all subscribed webhooks.

    Use after scan completion:
        await emit_event("search.completed", {"company": ..., "scan_time": ...})

    Non-blocking: spawned as background task per webhook so the API response
    doesn't wait for downstream delivery.
    """
    if event not in SUPPORTED_EVENTS:
        logger.warning(f"emit_event: unsupported event {event}")
        return

    conn = sqlite3.connect(str(WEBHOOK_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM webhooks WHERE enabled = 1 AND events LIKE ?",
        (f"%{event}%",),
    ).fetchall()
    conn.close()

    if not rows:
        return

    # Fire all in parallel, don't block caller
    for row in rows:
        wh = dict(row)
        if event in wh["events"].split(","):
            asyncio.create_task(_deliver_one(wh, event, payload))


async def test_webhook(webhook_id: str) -> dict:
    """Send a test event to a webhook and return result synchronously."""
    wh = _get_webhook(webhook_id)
    if not wh:
        return {"success": False, "error": "webhook not found or disabled"}

    test_payload = {
        "message": "DueSight webhook verification ping",
        "instructions": "If you receive this, your webhook is correctly configured. Verify the X-DueSight-Signature header using HMAC-SHA256 with your secret.",
    }
    start = time.monotonic()
    success = await _deliver_one(wh, "webhook.test", test_payload, timeout=10)
    elapsed = round((time.monotonic() - start) * 1000, 1)
    return {
        "success": success,
        "elapsed_ms": elapsed,
        "url": wh["url"],
        "event": "webhook.test",
    }


def get_delivery_log(webhook_id: str, limit: int = 50) -> list[dict]:
    """Recent delivery attempts for a webhook (audit log)."""
    conn = sqlite3.connect(str(WEBHOOK_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT event, status_code, success, error, attempts, timestamp
           FROM delivery_log WHERE webhook_id = ?
           ORDER BY id DESC LIMIT ?""",
        (webhook_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
