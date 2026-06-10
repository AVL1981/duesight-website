from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

try:
    from app.core.security_headers import SecurityHeadersMiddleware
except ImportError:
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).parent))
    from app.core.security_headers import SecurityHeadersMiddleware


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
SCAN_EVENTS_FILE = DATA_DIR / "scan_events.jsonl"
DDINTEL_BASE = os.getenv("DUESIGHT_DDINTEL_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

app = FastAPI(title="DueSight Scan Server", version="1.0.0")
# OWASP security headers for the public scan flow.
app.add_middleware(SecurityHeadersMiddleware)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")


async def _ddintel_connected() -> bool:
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            response = await client.get(f"{DDINTEL_BASE}/health")
        return response.status_code < 500
    except Exception:
        return False


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "DueSight Scan Server", "status": "ok"}


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "DueSight Scan Server",
        "ddintel_base": DDINTEL_BASE,
        "ddintel_connected": await _ddintel_connected(),
    }


@app.get("/api/checkout")
async def legacy_checkout(tier: str = "", domain: str = "", email: str = "") -> JSONResponse:
    return JSONResponse(
        status_code=410,
        content={
            "status": "disabled",
            "code": "legacy_checkout_disabled",
            "replacement": "/api/payment/create",
            "tier": tier,
            "domain": domain,
            "email": email,
        },
    )


@app.post("/api/scan")
async def create_scan(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}

    scan_id = "scan_" + secrets.token_urlsafe(12).replace("-", "").replace("_", "")[:18]
    event = {
        "type": "scan_requested",
        "scan_id": scan_id,
        "domain": str(body.get("domain") or ""),
        "tier": str(body.get("tier") or "quick_scan"),
        "lead_email": str(body.get("lead_email") or body.get("email") or ""),
        "lead_name": str(body.get("lead_name") or ""),
        "created_at": _now(),
    }
    _write_jsonl(SCAN_EVENTS_FILE, event)
    return {"scan_id": scan_id, "status": "pending"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "scan_server:app",
        host="127.0.0.1",
        port=5050,
        reload=False,
        server_header=False,
        date_header=False,
    )
