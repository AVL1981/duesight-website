"""
DueSight Contract Triage â€” FastAPI router

Endpoint: POST /api/contract/triage
Input:    JSON body with `text` (raw contract text) + optional `company_name`
Output:   Structured triage result met rode vlaggen, severity, risk score

âš ï¸  TRIAGE ONLY, GEEN legal review, GEEN clause-extractie.
Zie TRIAGE_DISCLAIMER constant in tools/contract_analyzer.py
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.contract_triage import (
    TRIAGE_DISCLAIMER,
    is_available,
    triage_text,
)

logger = logging.getLogger("duesight.contract_router")

router = APIRouter()


class TriageRequest(BaseModel):
    """Request body for /api/contract/triage."""

    text: str = Field(
        ...,
        min_length=10,
        max_length=5_000_000,  # ~5MB plain text cap
        description="Contract text (UTF-8). Plain-text only. PDF/DOCX support planned.",
    )
    company_name: str = Field(
        default="",
        max_length=200,
        description="Optional company context (e.g. target name) for scoring.",
    )
    source_label: str = Field(
        default="api_input",
        max_length=200,
        description="Identifier for the input (e.g. 'NDA_2024_acme.pdf').",
    )


@router.post("/contract/triage", summary="Pre-DD contract triage (red flags only)")
async def contract_triage_endpoint(payload: TriageRequest):
    """
    Run pre-DD red-flag triage on a contract (text input).

    âš ï¸  This is **triage only** â€” NOT a legal review. No clause extraction,
    no legal advice. Always validate flagged items with a qualified M&A lawyer.

    Detects (EN/NL/DE):
      - Unlimited liability / Indemnification broad
      - Change of control without notice
      - MAC clause too broad
      - Governing law offshore (Delaware/Cayman/BVI/CuraÃ§ao/Cyprus)
      - Non-compete duration/geography excessive
      - IP assignment broad
      - Data protection (GDPR/AVG) waiver
      - Escrow terms unfair
      - Auto-renewal without notice
      - Warranty disclaimer broad
      - + 7 more patterns
    """
    if not is_available():
        raise HTTPException(
            status_code=503,
            detail="Contract triage scanner unavailable (import error).",
        )

    result = await triage_text(
        text=payload.text,
        source_label=payload.source_label,
        company_name=payload.company_name,
    )

    # Always include the disclaimer in the response (positioning safety)
    result.setdefault("disclaimer", TRIAGE_DISCLAIMER)
    result.setdefault("status", "ok")

    return result


@router.get("/contract/health", summary="Contract triage health check")
async def contract_triage_health():
    """Health check + diagnostic info."""
    from app.services.contract_triage import get_pattern_count

    return {
        "status": "ok" if is_available() else "degraded",
        "scanner_available": is_available(),
        "pattern_count": get_pattern_count(),
        "disclaimer": TRIAGE_DISCLAIMER,
    }
