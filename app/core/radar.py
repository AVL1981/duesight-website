"""DueSight Radar â€” â‚¬19/mnd MRR subscription module.

Wires the existing Delta Engine (duesight-agent/tools/delta_engine.py) into a
customer-facing TPRM monitoring product. Per STRATEGY_RADAR_MRR.md:
- â‚¬19/mnd per counterparty
- 99% marge (kosten ~â‚¬0.15/maand)
- NIS2 + Wwft compliance driver

This module handles:
- Subscription lifecycle (trial â†’ active â†’ cancelled / past_due)
- Per-subscription monitored targets (with severity threshold + alert channels)
- Alert history (audit log per target)
- Mollie recurring subscription integration (when MOLLIE_API_KEY set)

Stays standalone â€” depends only on stdlib + optional httpx for Mollie.
SQLite persistence at .radar_store.db (root of website project).
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger("duesight.radar")

RADAR_DB = Path(__file__).parent.parent.parent / ".radar_store.db"

PLANS = {
    "radar_monthly": {"label": "Radar Monitoring", "cents": 1900, "interval": "1 month"},
    "radar_yearly":  {"label": "Radar Monitoring (Yearly)", "cents": 19000, "interval": "12 months"},
}

SEVERITY_LEVELS = ("low", "medium", "high", "critical")
ALERT_CHANNELS = ("email", "webhook", "slack")
SUBSCRIPTION_STATUSES = ("trialing", "active", "cancelled", "past_due", "pending")
TRIAL_DAYS = 14


def _init_db() -> None:
    conn = sqlite3.connect(str(RADAR_DB))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            subscription_id     TEXT PRIMARY KEY,
            customer_email      TEXT NOT NULL,
            customer_name       TEXT DEFAULT '',
            organization        TEXT DEFAULT '',
            plan                TEXT NOT NULL,
            status              TEXT NOT NULL DEFAULT 'pending',
            mollie_customer_id  TEXT DEFAULT '',
            mollie_subscription_id TEXT DEFAULT '',
            trial_ends_at       TEXT DEFAULT '',
            created_at          TEXT NOT NULL,
            cancelled_at        TEXT DEFAULT '',
            notes               TEXT DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_subs_email ON subscriptions(customer_email);
        CREATE INDEX IF NOT EXISTS idx_subs_status ON subscriptions(status);

        CREATE TABLE IF NOT EXISTS targets (
            target_id           TEXT PRIMARY KEY,
            subscription_id     TEXT NOT NULL,
            company_name        TEXT NOT NULL,
            kvk_number          TEXT DEFAULT '',
            domain              TEXT DEFAULT '',
            severity_threshold  TEXT NOT NULL DEFAULT 'medium',
            alert_channels      TEXT NOT NULL DEFAULT 'email',
            alert_email         TEXT DEFAULT '',
            alert_webhook_url   TEXT DEFAULT '',
            alert_slack_url     TEXT DEFAULT '',
            check_frequency     TEXT NOT NULL DEFAULT 'daily',
            last_check_at       TEXT DEFAULT '',
            last_alert_at       TEXT DEFAULT '',
            last_check_status   TEXT DEFAULT '',
            check_count         INTEGER DEFAULT 0,
            alert_count         INTEGER DEFAULT 0,
            enabled             INTEGER DEFAULT 1,
            created_at          TEXT NOT NULL,
            FOREIGN KEY(subscription_id) REFERENCES subscriptions(subscription_id)
        );
        CREATE INDEX IF NOT EXISTS idx_tgt_sub ON targets(subscription_id);
        CREATE INDEX IF NOT EXISTS idx_tgt_enabled ON targets(enabled, check_frequency);

        CREATE TABLE IF NOT EXISTS radar_alerts (
            alert_id            TEXT PRIMARY KEY,
            target_id           TEXT NOT NULL,
            subscription_id     TEXT NOT NULL,
            severity            TEXT NOT NULL,
            changes_json        TEXT NOT NULL,
            fired_at            TEXT NOT NULL,
            delivered_email     INTEGER DEFAULT 0,
            delivered_webhook   INTEGER DEFAULT 0,
            delivered_slack     INTEGER DEFAULT 0,
            acknowledged_at     TEXT DEFAULT '',
            FOREIGN KEY(target_id) REFERENCES targets(target_id),
            FOREIGN KEY(subscription_id) REFERENCES subscriptions(subscription_id)
        );
        CREATE INDEX IF NOT EXISTS idx_alerts_target ON radar_alerts(target_id);
        CREATE INDEX IF NOT EXISTS idx_alerts_sub ON radar_alerts(subscription_id);
        CREATE INDEX IF NOT EXISTS idx_alerts_time ON radar_alerts(fired_at);
    """)
    conn.commit()
    conn.close()


_init_db()


# â”€â”€â”€ Subscription management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def create_subscription(
    customer_email: str,
    plan: str = "radar_monthly",
    customer_name: str = "",
    organization: str = "",
) -> dict:
    """Create a new Radar subscription. Returns subscription_id + status.

    Starts in 'pending' status. After Mollie payment confirmation it moves to
    'trialing' (14 days free) then 'active'. If Mollie not configured, manual
    onboarding flow (Arian confirms by hand).
    """
    if plan not in PLANS:
        raise ValueError(f"Unknown plan: {plan}. Available: {list(PLANS)}")
    if "@" not in customer_email:
        raise ValueError("Invalid email")

    subscription_id = "sub_" + uuid.uuid4().hex[:24]
    trial_ends = (datetime.utcnow() + timedelta(days=TRIAL_DAYS)).isoformat()

    conn = sqlite3.connect(str(RADAR_DB))
    conn.execute(
        """INSERT INTO subscriptions (subscription_id, customer_email, customer_name,
                                       organization, plan, status, trial_ends_at, created_at)
           VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)""",
        (subscription_id, customer_email, customer_name, organization, plan,
         trial_ends, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()

    logger.info(f"Radar subscription created: {subscription_id} for {customer_email} ({plan})")
    return {
        "subscription_id": subscription_id,
        "status": "pending",
        "plan": plan,
        "plan_label": PLANS[plan]["label"],
        "price_eur": PLANS[plan]["cents"] / 100,
        "interval": PLANS[plan]["interval"],
        "trial_ends_at": trial_ends,
        "trial_days": TRIAL_DAYS,
        "next_step": "Bevestigingsmail volgt â€” onze ops bevestigt binnen 1 werkdag en activeert je 14-daagse trial.",
    }


def get_subscription(subscription_id: str) -> Optional[dict]:
    conn = sqlite3.connect(str(RADAR_DB))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM subscriptions WHERE subscription_id = ?",
        (subscription_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def list_subscriptions(customer_email: str = "", status: str = "") -> list[dict]:
    conn = sqlite3.connect(str(RADAR_DB))
    conn.row_factory = sqlite3.Row
    sql = "SELECT * FROM subscriptions WHERE 1=1"
    params: list = []
    if customer_email:
        sql += " AND customer_email = ?"
        params.append(customer_email)
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY created_at DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_subscription_status(subscription_id: str, status: str, mollie_id: str = "") -> bool:
    if status not in SUBSCRIPTION_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    conn = sqlite3.connect(str(RADAR_DB))
    updates = ["status = ?"]
    params: list = [status]
    if mollie_id:
        updates.append("mollie_subscription_id = ?")
        params.append(mollie_id)
    if status == "cancelled":
        updates.append("cancelled_at = ?")
        params.append(datetime.utcnow().isoformat())
    params.append(subscription_id)
    cur = conn.execute(
        f"UPDATE subscriptions SET {', '.join(updates)} WHERE subscription_id = ?",
        params,
    )
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def cancel_subscription(subscription_id: str) -> bool:
    """Cancel subscription + disable all targets."""
    ok = update_subscription_status(subscription_id, "cancelled")
    if ok:
        conn = sqlite3.connect(str(RADAR_DB))
        conn.execute(
            "UPDATE targets SET enabled = 0 WHERE subscription_id = ?",
            (subscription_id,),
        )
        conn.commit()
        conn.close()
    return ok


# â”€â”€â”€ Target management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def add_target(
    subscription_id: str,
    company_name: str,
    kvk_number: str = "",
    domain: str = "",
    severity_threshold: str = "medium",
    alert_channels: list[str] | None = None,
    alert_email: str = "",
    alert_webhook_url: str = "",
    alert_slack_url: str = "",
    check_frequency: str = "daily",
) -> dict:
    """Add a counterparty to monitor under a subscription."""
    if severity_threshold not in SEVERITY_LEVELS:
        raise ValueError(f"Invalid severity: {severity_threshold}. Use one of {SEVERITY_LEVELS}")

    sub = get_subscription(subscription_id)
    if not sub:
        raise ValueError(f"Subscription not found: {subscription_id}")
    if sub["status"] in ("cancelled",):
        raise ValueError(f"Subscription is {sub['status']} â€” reactivate first")

    channels = alert_channels or ["email"]
    for c in channels:
        if c not in ALERT_CHANNELS:
            raise ValueError(f"Invalid channel: {c}. Use {ALERT_CHANNELS}")

    target_id = "tgt_" + uuid.uuid4().hex[:24]
    conn = sqlite3.connect(str(RADAR_DB))
    conn.execute(
        """INSERT INTO targets (target_id, subscription_id, company_name, kvk_number,
                                domain, severity_threshold, alert_channels,
                                alert_email, alert_webhook_url, alert_slack_url,
                                check_frequency, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (target_id, subscription_id, company_name, kvk_number, domain,
         severity_threshold, ",".join(channels),
         alert_email or sub["customer_email"],
         alert_webhook_url, alert_slack_url,
         check_frequency, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()

    logger.info(f"Target added: {target_id} ({company_name}) under {subscription_id}")
    return {
        "target_id": target_id,
        "subscription_id": subscription_id,
        "company_name": company_name,
        "severity_threshold": severity_threshold,
        "alert_channels": channels,
        "check_frequency": check_frequency,
    }


def list_targets(subscription_id: str = "", enabled_only: bool = True) -> list[dict]:
    conn = sqlite3.connect(str(RADAR_DB))
    conn.row_factory = sqlite3.Row
    sql = "SELECT * FROM targets WHERE 1=1"
    params: list = []
    if subscription_id:
        sql += " AND subscription_id = ?"
        params.append(subscription_id)
    if enabled_only:
        sql += " AND enabled = 1"
    sql += " ORDER BY created_at DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [_target_to_dict(r) for r in rows]


def _target_to_dict(row) -> dict:
    d = dict(row)
    d["alert_channels"] = [c for c in d.get("alert_channels", "").split(",") if c]
    d["enabled"] = bool(d.get("enabled"))
    return d


def get_target(target_id: str) -> Optional[dict]:
    conn = sqlite3.connect(str(RADAR_DB))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM targets WHERE target_id = ?", (target_id,)).fetchone()
    conn.close()
    return _target_to_dict(row) if row else None


def remove_target(target_id: str) -> bool:
    conn = sqlite3.connect(str(RADAR_DB))
    cur = conn.execute("DELETE FROM targets WHERE target_id = ?", (target_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def list_active_targets_due(frequency: str = "daily", min_age_hours: int = 20) -> list[dict]:
    """Used by scheduler â€” targets that need a fresh check.

    Returns targets where:
    - enabled = 1
    - subscription.status in (trialing, active)
    - check_frequency = `frequency`
    - last_check_at is empty OR older than `min_age_hours`
    """
    threshold = (datetime.utcnow() - timedelta(hours=min_age_hours)).isoformat()
    conn = sqlite3.connect(str(RADAR_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT t.* FROM targets t
           JOIN subscriptions s ON s.subscription_id = t.subscription_id
           WHERE t.enabled = 1
             AND s.status IN ('trialing', 'active')
             AND t.check_frequency = ?
             AND (t.last_check_at = '' OR t.last_check_at < ?)
           ORDER BY t.last_check_at ASC""",
        (frequency, threshold),
    ).fetchall()
    conn.close()
    return [_target_to_dict(r) for r in rows]


def mark_check(target_id: str, status: str = "ok") -> None:
    conn = sqlite3.connect(str(RADAR_DB))
    conn.execute(
        """UPDATE targets
           SET last_check_at = ?, last_check_status = ?, check_count = check_count + 1
           WHERE target_id = ?""",
        (datetime.utcnow().isoformat(), status, target_id),
    )
    conn.commit()
    conn.close()


# â”€â”€â”€ Alert tracking â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def record_alert(
    target_id: str,
    severity: str,
    changes: list[dict],
    delivered_email: bool = False,
    delivered_webhook: bool = False,
    delivered_slack: bool = False,
) -> str:
    """Record an alert fired by Delta Engine for a target."""
    target = get_target(target_id)
    if not target:
        raise ValueError(f"Target not found: {target_id}")

    alert_id = "alert_" + uuid.uuid4().hex[:24]
    conn = sqlite3.connect(str(RADAR_DB))
    conn.execute(
        """INSERT INTO radar_alerts (alert_id, target_id, subscription_id, severity,
                                      changes_json, fired_at, delivered_email,
                                      delivered_webhook, delivered_slack)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (alert_id, target_id, target["subscription_id"], severity,
         json.dumps(changes, ensure_ascii=False, default=str),
         datetime.utcnow().isoformat(),
         int(delivered_email), int(delivered_webhook), int(delivered_slack)),
    )
    conn.execute(
        """UPDATE targets SET last_alert_at = ?, alert_count = alert_count + 1
           WHERE target_id = ?""",
        (datetime.utcnow().isoformat(), target_id),
    )
    conn.commit()
    conn.close()
    logger.info(f"Alert recorded: {alert_id} for target {target_id} severity={severity}")
    return alert_id


def list_alerts(
    subscription_id: str = "",
    target_id: str = "",
    limit: int = 50,
) -> list[dict]:
    conn = sqlite3.connect(str(RADAR_DB))
    conn.row_factory = sqlite3.Row
    sql = "SELECT * FROM radar_alerts WHERE 1=1"
    params: list = []
    if subscription_id:
        sql += " AND subscription_id = ?"
        params.append(subscription_id)
    if target_id:
        sql += " AND target_id = ?"
        params.append(target_id)
    sql += " ORDER BY fired_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["changes"] = json.loads(d.pop("changes_json", "[]"))
        except Exception:
            d["changes"] = []
        out.append(d)
    return out


def acknowledge_alert(alert_id: str) -> bool:
    conn = sqlite3.connect(str(RADAR_DB))
    cur = conn.execute(
        "UPDATE radar_alerts SET acknowledged_at = ? WHERE alert_id = ?",
        (datetime.utcnow().isoformat(), alert_id),
    )
    conn.commit()
    conn.close()
    return cur.rowcount > 0


# â”€â”€â”€ Stats â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def get_stats() -> dict:
    conn = sqlite3.connect(str(RADAR_DB))
    cur = conn.cursor()
    stats = {
        "subscriptions": {
            s: cur.execute("SELECT COUNT(*) FROM subscriptions WHERE status = ?", (s,)).fetchone()[0]
            for s in SUBSCRIPTION_STATUSES
        },
        "targets_total": cur.execute("SELECT COUNT(*) FROM targets WHERE enabled = 1").fetchone()[0],
        "alerts_24h": cur.execute(
            "SELECT COUNT(*) FROM radar_alerts WHERE fired_at >= ?",
            ((datetime.utcnow() - timedelta(hours=24)).isoformat(),),
        ).fetchone()[0],
        "alerts_total": cur.execute("SELECT COUNT(*) FROM radar_alerts").fetchone()[0],
    }
    conn.close()
    # Estimated MRR (active + trialing as if converting)
    active = stats["subscriptions"]["active"]
    trialing = stats["subscriptions"]["trialing"]
    stats["mrr_eur_active"] = active * 19
    stats["mrr_eur_trial_potential"] = trialing * 19
    return stats
