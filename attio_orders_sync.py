from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from attio_connector import AttioClient
import payment_server


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
ORDER_SYNC_LOG_PATH = Path(
    os.getenv("DUESIGHT_ATTIO_ORDER_SYNC_LOG_PATH", str(DATA_DIR / "attio_order_sync_log.json"))
)

FREE_EMAIL_DOMAINS = {
    "aol.com",
    "gmail.com",
    "googlemail.com",
    "hotmail.com",
    "icloud.com",
    "live.com",
    "me.com",
    "msn.com",
    "outlook.com",
    "pm.me",
    "proton.me",
    "protonmail.com",
    "yahoo.com",
    "yahoo.co.uk",
    "yandex.com",
    "zoho.com",
}

log = logging.getLogger("attio_orders")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _env_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "y", "on"}


def attio_live_push_allowed() -> bool:
    """Require both sync enablement and the DPA precondition before live pushes."""
    return _env_enabled("DUESIGHT_ATTIO_ORDER_SYNC_ENABLED") and _env_enabled(
        "DUESIGHT_ATTIO_DPA_CONFIRMED"
    )


def _read_sync_log(path: Path = ORDER_SYNC_LOG_PATH) -> set[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    values = data.get("synced_order_ids", [])
    return {str(value) for value in values if str(value).strip()}


def _write_sync_log(order_ids: set[str], path: Path = ORDER_SYNC_LOG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "duesight.attio_order_sync.v1",
        "last_sync": _now(),
        "synced_order_ids": sorted(order_ids),
        "total_synced": len(order_ids),
    }
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def _clean_email(value: Any) -> str:
    email = str(value or "").strip().lower()
    return email if "@" in email and email.rsplit("@", 1)[-1] else ""


def _email_domain(email: str) -> str:
    return email.rsplit("@", 1)[-1].strip().lower() if "@" in email else ""


def _is_free_email_domain(domain: str) -> bool:
    normalized = domain.lower().strip()
    return normalized in FREE_EMAIL_DOMAINS


def _company_name_from_domain(domain: str) -> str:
    base = domain.split(".")[0] if domain else ""
    parts = [part for part in re.split(r"[^a-zA-Z0-9]+", base) if part]
    return " ".join(part.capitalize() for part in parts) or domain


def _product_label(order: dict[str, Any]) -> str:
    product_key = str(order.get("product") or "").strip()
    product = payment_server.PRODUCTS.get(product_key)
    if product:
        return product["name"]
    amount = str(order.get("amount") or "").strip()
    currency = str(order.get("currency") or "EUR").strip() or "EUR"
    for item in payment_server.PRODUCTS.values():
        if item.get("amount") == amount and item.get("currency") == currency:
            return item["name"]
    return product_key or "DueSight order"


def _order_target_label(order: dict[str, Any]) -> str:
    company = str(order.get("company_name") or "").strip() or "onbekend target"
    kvk = str(order.get("kvk_number") or "").strip()
    return f"{company} (KvK {kvk})" if kvk else company


def _order_note_content(order: dict[str, Any]) -> str:
    lines = [
        "DueSight order",
        f"Order ID: {order.get('order_id', '')}",
        f"Product: {_product_label(order)}",
        f"Bedrag: {order.get('amount', '')} {order.get('currency', 'EUR')}",
        f"Orderstatus: {order.get('status', '')}",
        f"Scanstatus: {order.get('scan_status', '')}",
        f"Delivery status: {order.get('delivery_status', '')}",
        "",
        "Scan-target / onderwerp van scan:",
        f"- Bedrijf: {str(order.get('company_name') or '').strip() or 'onbekend'}",
        f"- KvK: {str(order.get('kvk_number') or '').strip() or 'niet opgegeven'}",
    ]
    created_at = str(order.get("created_at") or "").strip()
    if created_at:
        lines.extend(["", f"Aangemaakt: {created_at}"])
    return "\n".join(lines)


def _record_id(result: dict[str, Any]) -> str:
    data = result.get("data", {}) if isinstance(result, dict) else {}
    record_id = data.get("id", {}).get("record_id", "") if isinstance(data, dict) else ""
    return str(record_id or "")


def _order_row_to_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return dict(row)
    try:
        return dict(row)
    except Exception:
        return {}


def fetch_syncable_orders(limit: int = 100) -> list[dict[str, Any]]:
    """Read paid orders that can be synced by the separate CRM job."""
    payment_server._init_db()
    conn = payment_server._db()
    rows = conn.execute(
        """SELECT *
           FROM orders
           WHERE status = 'paid'
           ORDER BY created_at ASC, order_id ASC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [_order_row_to_dict(row) for row in rows]


class AttioOrderSync:
    def __init__(
        self,
        client: AttioClient | Any | None = None,
        *,
        api_key: str = "",
        sync_log_path: Path = ORDER_SYNC_LOG_PATH,
        live_enabled: bool | None = None,
    ) -> None:
        self.client = client or AttioClient(api_key=api_key or os.getenv("ATTIO_API_KEY", ""))
        self.sync_log_path = sync_log_path
        self.synced_order_ids = _read_sync_log(sync_log_path)
        self.live_enabled = attio_live_push_allowed() if live_enabled is None else live_enabled

    def status(self, orders: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        rows = orders if orders is not None else fetch_syncable_orders()
        open_orders = [
            str(row.get("order_id") or "")
            for row in rows
            if str(row.get("order_id") or "") not in self.synced_order_ids
        ]
        return {
            "status": "enabled" if self.live_enabled else "disabled",
            "orders": len(rows),
            "synced": len(self.synced_order_ids),
            "open": len(open_orders),
            "open_order_ids": open_orders,
        }

    def _mark_synced(self, order_id: str) -> None:
        self.synced_order_ids.add(order_id)
        _write_sync_log(self.synced_order_ids, self.sync_log_path)

    async def close(self) -> None:
        close = getattr(self.client, "close", None)
        if close:
            result = close()
            if hasattr(result, "__await__"):
                await result

    async def push_order(self, order: dict[str, Any]) -> dict[str, Any]:
        order_id = str(order.get("order_id") or "").strip()
        if not order_id:
            return {"status": "skipped", "reason": "missing_order_id"}
        if order_id in self.synced_order_ids:
            return {"status": "already_synced", "order_id": order_id}
        if not self.live_enabled:
            return {"status": "disabled", "order_id": order_id}
        if not str(getattr(self.client, "api_key", "") or "").strip():
            return {"status": "no_api_key", "order_id": order_id}

        try:
            result = await self._push_order_live(order)
        except Exception as exc:
            log.warning("Attio order sync failed for %s: %s", order_id, exc)
            return {"status": "failed", "order_id": order_id, "error": str(exc)[:200]}

        self._mark_synced(order_id)
        return {"status": "synced", "order_id": order_id, **result}

    async def _push_order_live(self, order: dict[str, Any]) -> dict[str, Any]:
        customer_email = _clean_email(order.get("customer_email"))
        delivery_email = _clean_email(order.get("delivery_email"))
        if not customer_email and not delivery_email:
            return {"status": "skipped", "reason": "missing_customer_email"}

        emails = []
        for email in (customer_email, delivery_email):
            if email and email not in emails:
                emails.append(email)

        person_result = await self._upsert_person(emails)
        person_id = _record_id(person_result)
        if not person_id:
            raise RuntimeError("attio_person_missing_record_id")

        company_id = ""
        customer_domain = _email_domain(customer_email or delivery_email)
        if customer_domain and not _is_free_email_domain(customer_domain):
            company_result = await self._upsert_customer_company(customer_domain)
            company_id = _record_id(company_result)

        deal_result = await self._create_order_deal(order, person_id, company_id)
        deal_id = _record_id(deal_result)

        parent_object = "companies" if company_id else "people"
        parent_id = company_id or person_id
        note_result = await self._add_order_note(order, parent_object, parent_id)
        note_id = _record_id(note_result)

        return {
            "person_record_id": person_id,
            "company_record_id": company_id,
            "deal_record_id": deal_id,
            "note_record_id": note_id,
        }

    async def _upsert_person(self, emails: list[str]) -> dict[str, Any]:
        primary = emails[0]
        local_part = primary.split("@", 1)[0].replace(".", " ").replace("_", " ").strip()
        values: dict[str, Any] = {
            "email_addresses": [{"email_address": email} for email in emails],
            "description": [{"value": "Bron: DueSight order"}],
        }
        if local_part:
            values["name"] = [{"full_name": local_part.title()}]
        return await self.client._post(
            "/objects/people/records",
            {"data": {"values": values}, "matching_attribute": "email_addresses"},
        )

    async def _upsert_customer_company(self, domain: str) -> dict[str, Any]:
        values = {
            "name": [{"value": _company_name_from_domain(domain)}],
            "domains": [{"domain": domain}],
            "description": [{"value": "Bron: DueSight order"}],
        }
        return await self.client._post(
            "/objects/companies/records",
            {"data": {"values": values}, "matching_attribute": "domains"},
        )

    async def _create_order_deal(
        self,
        order: dict[str, Any],
        person_id: str,
        company_id: str,
    ) -> dict[str, Any]:
        values = {
            "name": [{"value": f"{_product_label(order)} - {order.get('order_id', '')}"}],
            "description": [{"value": _order_note_content(order)}],
        }
        amount = str(order.get("amount") or "").strip()
        currency = str(order.get("currency") or "EUR").strip() or "EUR"
        if amount:
            values["value"] = [{"amount": amount, "currency_code": currency}]
        if person_id:
            values["associated_people"] = [{"target_record_id": person_id}]
        if company_id:
            values["associated_company"] = [{"target_record_id": company_id}]
        return await self.client._post("/objects/deals/records", {"data": {"values": values}})

    async def _add_order_note(
        self,
        order: dict[str, Any],
        parent_object: str,
        parent_record_id: str,
    ) -> dict[str, Any]:
        body = {
            "data": {
                "parent_object": parent_object,
                "parent_record_id": parent_record_id,
                "title": f"DueSight order - {_order_target_label(order)}",
                "format": "plaintext",
                "content": _order_note_content(order),
            }
        }
        return await self.client._post("/notes", body)

    async def sync_orders(self, orders: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        rows = orders if orders is not None else fetch_syncable_orders()
        results = {"synced": 0, "skipped": 0, "failed": 0, "details": []}
        for order in rows:
            result = await self.push_order(order)
            status = result.get("status")
            if status == "synced":
                results["synced"] += 1
            elif status == "failed":
                results["failed"] += 1
            else:
                results["skipped"] += 1
            results["details"].append(result)
        return results


async def main() -> None:
    parser = argparse.ArgumentParser(description="DueSight orders to Attio CRM sync")
    parser.add_argument("--sync", action="store_true", help="Sync paid orders to Attio")
    parser.add_argument("--status", action="store_true", help="Show order sync status")
    parser.add_argument("--limit", type=int, default=100, help="Maximum paid orders to inspect")
    parser.add_argument("--token", type=str, default="", help="Attio API key override")
    args = parser.parse_args()

    orders = fetch_syncable_orders(limit=args.limit)
    syncer = AttioOrderSync(api_key=args.token)
    try:
        if args.status:
            print(json.dumps(syncer.status(orders), ensure_ascii=True, indent=2))
            return
        if args.sync:
            result = await syncer.sync_orders(orders)
            print(json.dumps(result, ensure_ascii=True, indent=2))
            return
        parser.print_help()
    finally:
        await syncer.close()


if __name__ == "__main__":
    asyncio.run(main())
