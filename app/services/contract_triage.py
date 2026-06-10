"""
DueSight Contract Triage â€” Website service wrapper.

Pre-DD red flag detection for M&A contracts. Triage-only, NOT legal review.

âš ï¸  POSITIONERINGS-DISCLAIMER (NIET VERWIJDEREN):
  Dit is GEEN contract review tool. Geen clause-extractie, geen legal advice.
  Alleen regex-based red flag detection. Vereist handmatige verificatie door
  juridisch expert.

Wire-in: app/api/routers/contract.py
Bron: tools/contract_analyzer.py (duesight-agent, single source of truth)
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("duesight.contract_triage_service")

FALLBACK_TRIAGE_DISCLAIMER = (
    "Dit is een geautomatiseerde pre-DD triage op basis van regex-patronen. "
    "GEEN legal advice, GEEN clause review, GEEN vervanging voor M&A-advocaat. "
    "Gevonden flags vereisen handmatige verificatie door juridisch expert."
)

TRIAGE_DISCLAIMER = FALLBACK_TRIAGE_DISCLAIMER
RED_FLAG_PATTERNS: Dict[str, Any] = {}


def _ensure_agent_path() -> None:
    """Ensure the duesight-agent tools/ directory is on sys.path.

    Allows the website service to import ContractTriageScanner without
    duplicating the implementation. The agent is the canonical source.
    """
    repo_root = Path(__file__).resolve().parents[2]
    candidates = [
        Path(__file__).resolve().parents[3] / "duesight-agent",
        repo_root,
    ]
    for candidate in candidates:
        if (candidate / "tools" / "contract_analyzer.py").exists():
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            return
    searched = ", ".join(str(candidate / "tools") for candidate in candidates)
    raise RuntimeError(
        f"ContractTriageScanner not found. Searched: {searched}."
    )


try:
    _ensure_agent_path()
    from tools.contract_analyzer import (
        ContractTriageScanner,
        TRIAGE_DISCLAIMER as _CANONICAL_TRIAGE_DISCLAIMER,
        RED_FLAG_PATTERNS as _CANONICAL_RED_FLAG_PATTERNS,
    )

    TRIAGE_DISCLAIMER = _CANONICAL_TRIAGE_DISCLAIMER
    RED_FLAG_PATTERNS = _CANONICAL_RED_FLAG_PATTERNS
    _IMPORT_OK = True
    _IMPORT_ERROR: Optional[str] = None
except Exception as e:  # noqa: BLE001 - defensive at boot
    _IMPORT_OK = False
    _IMPORT_ERROR = repr(e)
    logger.warning(f"[ContractTriage] Could not import ContractTriageScanner: {e}")


def is_available() -> bool:
    """Health check: scanner importable from agent path."""
    return _IMPORT_OK


async def triage_text(
    text: str,
    source_label: str = "api_input",
    company_name: str = "",
) -> Dict[str, Any]:
    """Run pre-DD triage on raw contract text.

    Args:
        text: Contract text (UTF-8).
        source_label: Identifier for the input (filename, upload name, etc.).
        company_name: Optional company context for scoring.

    Returns:
        Structured TriageResult dict (see tools/contract_analyzer.py).
        On import error: dict with error key + empty flags.
    """
    if not _IMPORT_OK:
        return {
            "status": "error",
            "error": f"Triage scanner unavailable: {_IMPORT_ERROR}",
            "disclaimer": TRIAGE_DISCLAIMER,
            "flags": [],
        }
    scanner = ContractTriageScanner(company_name=company_name)
    result = await scanner.triage_text(text=text, source_label=source_label)
    return result.to_dict()


def get_pattern_count() -> int:
    """Return number of red flag patterns loaded (for diagnostics)."""
    return len(RED_FLAG_PATTERNS) if _IMPORT_OK else 0
