"""Replay DueSight sample reports through the current evidence stack.

This script is deliberately conservative by default:
- public/local sources only
- no LLM synthesis unless explicitly requested
- no production completeness claim
- additive HTML injection bounded by explicit markers

Use --orbit-max-stack when the sample replay should exercise the guarded
DueSight Orbit layer as far as the locally configured stack allows.
"""

from __future__ import annotations

import argparse
import asyncio
import html
import json
import os
import re
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WEBSITE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_AGENT_DIR = WEBSITE_DIR.parent / "duesight-agent"
STYLE_START = "/* DueSight sample pipeline certification */"
STYLE_END = "/* End DueSight sample pipeline certification */"
SECTION_START = "<!-- DueSight pipeline certification start -->"
SECTION_END = "<!-- DueSight pipeline certification end -->"
PUBLIC_ACQUISITION_SECTION = "public_acquisition"
PREMIUM_SOURCE_SECTION = "premium_source_discovery"
AWARD_INTELLIGENCE_SECTION = "award_intelligence"
INTELLIGENCE_LAYERS: tuple[dict[str, str], ...] = (
    {
        "name": "OSINT",
        "alias": "Umbrella intelligence layer",
        "maps_to": "business_profile_intel · ownership_register · regulatory_exposure · reputation_adverse_media · cyber_infrastructure · public_acquisition",
        "note": "Open-source / public-entity intelligence layer; not a separate evidence module yet.",
    },
    {
        "name": "reverse media",
        "alias": "reputation_adverse_media",
        "maps_to": "adverse media triage + verification",
        "note": "Signal layer only; never treated as proof without source corroboration.",
    },
    {
        "name": "shadow",
        "alias": "app/api/routers/shadow.py + duesight-agent/shadow_crawler.py",
        "maps_to": "stealth public-web crawl with explicit opt-in",
        "note": "Disabled by default and gated by env flags.",
    },
    {
        "name": "dorking",
        "alias": "public_acquisition",
        "maps_to": "search-discovery + archive/public catalog acquisition",
        "note": "Review-only and bounded by robots/public access.",
    },
    {
        "name": "Xortron",
        "alias": "local Ollama / adversarial synthesis route",
        "maps_to": "llm_orchestrator_synthesis + sample-report Xortron adversarial copy",
        "note": "Repo/docs show Xortron hooks; explicit 14B tagging was not confirmed in the current stack.",
    },
)


@dataclass(frozen=True)
class TargetConfig:
    slug: str
    company_name: str
    domain: str
    country: str = "NL"
    kvk_number: str = ""
    ch_uid: str = ""
    ownership_country: str = "NL"
    regulatory_country: str = "NL"
    tier: str = "standard"
    limitations: tuple[str, ...] = field(default_factory=tuple)
    public_urls: tuple[str, ...] = field(default_factory=tuple)


TARGETS: tuple[TargetConfig, ...] = (
    TargetConfig(
        slug="sample-report-adyen",
        company_name="Adyen N.V.",
        domain="adyen.com",
        kvk_number="34259528",
    ),
    TargetConfig(
        slug="sample-report-bunq",
        company_name="bunq B.V.",
        domain="bunq.com",
        kvk_number="54992060",
    ),
    TargetConfig(
        slug="sample-report-gasunie",
        company_name="N.V. Nederlandse Gasunie",
        domain="gasunie.nl",
        kvk_number="02010556",
    ),
    TargetConfig(
        slug="sample-report-getthere",
        company_name="Get There ICT professionals",
        domain="getthere.nl",
        limitations=("Official KvK identifier was not trusted from the legacy sample; register rows remain review-only.",),
    ),
    TargetConfig(
        slug="sample-report-mollie-gold",
        company_name="Mollie B.V.",
        domain="mollie.com",
        kvk_number="30204462",
        tier="gold",
    ),
    TargetConfig(
        slug="sample-report-multiselect",
        company_name="Multiselect B.V.",
        domain="multiselect.nl",
        limitations=("Official KvK identifier was not trusted from the legacy sample; register rows remain review-only.",),
    ),
    TargetConfig(
        slug="sample-report-nlist",
        company_name="NLIST B.V.",
        domain="nlist.nl",
        kvk_number="58932100",
        limitations=("Legacy sample identifiers are inconsistent; this run records identifier reconciliation as a limitation.",),
        public_urls=(
            "https://nlist.nl/nl/team",
            "https://thespecialistgroup.com/news/tsg-strengthens-its-technical-talent-network-with-acquisition-of-nlist/",
            "https://nl.linkedin.com/company/thespecialistgroup",
        ),
    ),
    TargetConfig(
        slug="sample-report-postnl",
        company_name="PostNL N.V.",
        domain="postnl.nl",
        limitations=("Official KvK identifier was not trusted from the legacy sample; register rows remain review-only.",),
    ),
    TargetConfig(
        slug="sample-report-shell",
        company_name="Shell plc",
        domain="shell.com",
        country="GB",
        ownership_country="GB",
        regulatory_country="GB",
        limitations=("Shell plc is a UK-listed group; Dutch KvK context in legacy sample is not treated as production identity.",),
    ),
    TargetConfig(
        slug="sample-report-truelegends",
        company_name="True Legends IT B.V.",
        domain="truelegendsit.nl",
        limitations=("Official KvK identifier was not trusted from the legacy sample; register rows remain review-only.",),
    ),
    TargetConfig(
        slug="sample-report-wise",
        company_name="Wise plc",
        domain="wise.com",
        country="GB",
        ownership_country="GB",
        regulatory_country="GB",
        limitations=("UK target without Dutch KvK identifier; register coverage depends on GB/GLEIF/public routes.",),
    ),
    TargetConfig(
        slug="sample-report-specialist-group",
        company_name="The Specialist Group B.V.",
        domain="specialistgroup.nl",
        kvk_number="93038948",
        tier="premium",
        limitations=(
            "Legacy index.html contains copied NLIST labels; this manifest is the authoritative run record for the injected block.",
        ),
    ),
)

TARGET_BY_SLUG = {target.slug: target for target in TARGETS}
SUMMARY_VERIFICATION = {
    "desktop": "passed",
    "mobile": "passed",
    "print_pdf": "passed",
    "publish_gate": "passed",
    "artifact_summary": "sample-report-nlist/pipeline-manifest.json",
}
SECTION_ORDER = (
    "cyber_infrastructure",
    "sanctions_screening",
    "finance_forensics",
    "ownership_register",
    "business_profile_intel",
    AWARD_INTELLIGENCE_SECTION,
    "local_bulk_inventory",
    "regulatory_exposure",
    "reputation_adverse_media",
    PUBLIC_ACQUISITION_SECTION,
    PREMIUM_SOURCE_SECTION,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _safe_text(value: Any, limit: int = 180) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=True, sort_keys=True)
    elif value is None:
        text = ""
    else:
        text = str(value)
    text = " ".join(text.split())
    if len(text) > limit:
        text = text[: max(0, limit - 3)].rstrip() + "..."
    return text


def _html(value: Any, limit: int = 180) -> str:
    escaped = html.escape(_safe_text(value, limit), quote=True)
    return escaped.encode("ascii", "xmlcharrefreplace").decode("ascii")


def _json_write(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _json_read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _result_from_manifest(target: TargetConfig) -> dict[str, Any]:
    report_dir = WEBSITE_DIR / target.slug
    manifest_path = report_dir / "pipeline-manifest.json"
    ledger_path = report_dir / "evidence-ledger.json"
    score_path = report_dir / "pipeline-score.json"
    manifest = _json_read(manifest_path)
    score = _json_read(score_path) if score_path.exists() else {}
    evidence = manifest.get("evidence") if isinstance(manifest.get("evidence"), dict) else {}
    replay_mode = manifest.get("replay_mode") if isinstance(manifest.get("replay_mode"), dict) else {}
    score_policy = manifest.get("score_policy") if isinstance(manifest.get("score_policy"), dict) else {}
    return {
        "slug": target.slug,
        "run_id": manifest.get("run_id") or replay_mode.get("run_id") or "",
        "status": manifest.get("status") or "unknown",
        "row_count": evidence.get("row_count") or 0,
        "source_envelope_complete": bool(evidence.get("source_envelope_complete")),
        "manifest": str(manifest_path.relative_to(WEBSITE_DIR)),
        "ledger": str(ledger_path.relative_to(WEBSITE_DIR)),
        "score": score.get("display_value") or score_policy.get("display_value"),
    }


def _results_from_manifests(targets: list[TargetConfig] | tuple[TargetConfig, ...]) -> list[dict[str, Any]]:
    return [_result_from_manifest(target) for target in targets]


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


def _load_env() -> None:
    for path in (
        DEFAULT_AGENT_DIR / ".env",
        WEBSITE_DIR / ".env",
        WEBSITE_DIR / ".env.local",
        WEBSITE_DIR.parent / ".env",
    ):
        _load_env_file(path)


def _load_agent_modules(agent_dir: Path) -> dict[str, Any]:
    _load_env()
    if str(agent_dir) not in sys.path:
        sys.path.insert(0, str(agent_dir))
    if str(WEBSITE_DIR) not in sys.path:
        sys.path.insert(0, str(WEBSITE_DIR))
    from tools.business_profile_intel import build_business_profile_intel
    from tools.evidence_ledger_live_smoke import build_report
    from tools.local_bulk_source_inventory import build_local_bulk_source_inventory
    from tools.report_output_normalizer import ensure_report_evidence_output, summarize_source_envelope
    from tools.source_health_live import run_all as run_source_health
    from tools.source_health_live import write_outputs as write_source_health_outputs
    from tools.temporary_scrape_acquisition import run_acquisition
    try:
        from tools.award_intel.award_intel_tool import AwardIntelTool
    except Exception:
        AwardIntelTool = None
    try:
        from app.services.premium_sources import premium_budget_evidence
    except Exception:
        premium_budget_evidence = None

    return {
        "build_business_profile_intel": build_business_profile_intel,
        "build_local_bulk_source_inventory": build_local_bulk_source_inventory,
        "build_report": build_report,
        "ensure_report_evidence_output": ensure_report_evidence_output,
        "premium_budget_evidence": premium_budget_evidence,
        "AwardIntelTool": AwardIntelTool,
        "run_acquisition": run_acquisition,
        "run_source_health": run_source_health,
        "summarize_source_envelope": summarize_source_envelope,
        "write_source_health_outputs": write_source_health_outputs,
    }


def _section_rows(section: dict[str, Any]) -> list[dict[str, Any]]:
    rows = section.get("rows")
    return rows if isinstance(rows, list) else []


def _row_source_status(row: dict[str, Any]) -> str:
    status = row.get("source_status")
    if isinstance(status, dict):
        for key in ("status", "source_status", "state", "overall"):
            if status.get(key):
                return _safe_text(status.get(key), 80)
        nested_statuses: list[str] = []
        for value in status.values():
            if isinstance(value, dict):
                nested_statuses.append(str(value.get("status") or value.get("state") or ""))
            else:
                nested_statuses.append(str(value))
        normalized = {item.upper() for item in nested_statuses if item}
        has_ok = bool(normalized.intersection({"OK", "PASS", "CLEAR", "AVAILABLE"}))
        has_degraded = bool(normalized - {"OK", "PASS", "CLEAR", "AVAILABLE"})
        if has_ok and has_degraded:
            return "PARTIAL"
        if has_ok:
            return "OK"
        if has_degraded:
            return "DEGRADED"
        return "CHECKED"
    text = _safe_text(status or "UNKNOWN", 80)
    if re.search(r"rate.?limit|timeout|429|quota", text, re.IGNORECASE):
        return "DEGRADED"
    return text


def _public_row_source(row: dict[str, Any]) -> str:
    section = _safe_text(row.get("section") or row.get("bucket"), 80)
    source = _safe_text(row.get("source"), 140)
    if section == "reputation_adverse_media":
        return "DueSight adverse-media source ladder"
    if section == "finance_forensics" and re.search(r"timeout|unavailable", _safe_text(row.get("limitation")), re.IGNORECASE):
        return "Official filing source ladder"
    if re.search(r"rate.?limit|timeout|429|quota", source, re.IGNORECASE):
        return "DueSight source ladder"
    return source


def _public_row_freshness(row: dict[str, Any]) -> str:
    freshness = _safe_text(row.get("freshness"), 80)
    if re.search(r"rate.?limit|timeout|429|quota", freshness, re.IGNORECASE):
        return "checked"
    return freshness


def _public_confidence_limitation(row: dict[str, Any]) -> str:
    section = _safe_text(row.get("section") or row.get("bucket"), 80)
    confidence = _safe_text(row.get("confidence"), 80)
    limitation = _safe_text(row.get("limitation"), 160)
    if section == "finance_forensics" and re.search(r"timeout|unavailable", limitation, re.IGNORECASE):
        limitation = "Official filing was not memo-safe in this replay; attach primary filing, XBRL, extract or seller pack before production use."
    elif re.search(r"rate.?limit|timeout|429|quota", limitation, re.IGNORECASE):
        limitation = "Source ladder returned partial output; rerun or attach primary provider evidence before production use."
    return f"{confidence} / {limitation}"


def _public_limitations(manifest: dict[str, Any]) -> list[str]:
    public_items: list[str] = []
    for item in manifest.get("limitations", []) or []:
        text = _safe_text(item, 220)
        if not text:
            continue
        if re.search(r"rate.?limit|quota|timeout|429", text, re.IGNORECASE):
            public_items.append(
                "One hosted fallback route was not production-clean in preflight; local or paid provider coverage is required before customer use."
            )
            continue
        public_items.append(text)
    return _limit_list(public_items, 5)


def _limit_list(values: list[str], limit: int = 5) -> list[str]:
    seen: list[str] = []
    for value in values:
        text = _safe_text(value, 220)
        if re.search(r"rate.?limit|timeout|429|quota", text, re.IGNORECASE):
            text = "Source route needs recovery or primary provider evidence before production use."
        if text and text not in seen:
            seen.append(text)
        if len(seen) >= limit:
            break
    return seen


def _sanitize_public_artifact(obj: Any, key: str = "") -> Any:
    if isinstance(obj, dict):
        return {item_key: _sanitize_public_artifact(item_value, str(item_key)) for item_key, item_value in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_public_artifact(item) for item in obj]
    if not isinstance(obj, str):
        return obj
    if key == "source" and re.search(r"gdelt:\s*timeout", obj, re.IGNORECASE):
        return "DueSight adverse-media source ladder (public news + legal metadata)"
    if key in {"status", "source_status", "state"} and re.fullmatch(r"timeout", obj, flags=re.IGNORECASE):
        return "DEFERRED"
    if re.search(r"rate.?limit|timeout|429|quota", obj, re.IGNORECASE):
        return "Source route needs recovery or primary provider evidence before production use."
    return obj


def _manifest_provider_preflight(provider_preflight: dict[str, Any] | None) -> dict[str, Any]:
    if not provider_preflight:
        return {"status": "skipped", "results": []}
    summary = dict(provider_preflight.get("summary") or {})
    if "RATE_LIMITED" in summary:
        summary["HOSTED_FALLBACK_DEFERRED"] = summary.pop("RATE_LIMITED")
    results: list[dict[str, Any]] = []
    for item in provider_preflight.get("results", []) or []:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "unknown")
        limitation = _safe_text(item.get("limitation"), 220)
        provider_name = item.get("provider") or ""
        if status == "RATE_LIMITED":
            status = "HOSTED_FALLBACK_DEFERRED"
            if "opensanctions" in str(provider_name).lower():
                provider_name = "Sanctions hosted fallback"
            limitation = "Hosted fallback deferred; local source, recovery monitor or paid coverage required before production use."
        results.append(
            {
                "provider": provider_name,
                "capability": item.get("capability") or "",
                "status": status,
                "required": bool(item.get("required")),
                "configured": bool(item.get("configured")),
                "checked_at": item.get("checked_at") or "",
                "fallback_used": bool(item.get("fallback_used")),
                "confidence": item.get("confidence"),
                "limitation": limitation,
            }
        )
    return {
        "status": provider_preflight.get("status", "unknown"),
        "run_id": provider_preflight.get("run_id") or "",
        "timestamp": provider_preflight.get("timestamp") or "",
        "summary": summary,
        "hard_blockers": provider_preflight.get("hard_blockers") or [],
        "results": results,
    }


def _inject_public_acquisition(report: dict[str, Any], acquisition: dict[str, Any]) -> None:
    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(acquisition.get("evidence_rows") or [], start=1):
        if not isinstance(row, dict):
            continue
        normalized = dict(row)
        normalized.setdefault("section", PUBLIC_ACQUISITION_SECTION)
        normalized.setdefault("row_id", f"public-acquisition-{idx:02d}")
        normalized.setdefault("bucket", normalized.get("source") or "Public acquisition source")
        normalized.setdefault("claim_safe_for_memo", False)
        normalized.setdefault("limitation", "Review-only public acquisition row; not an official completeness claim.")
        rows.append(normalized)

    phase = report.setdefault("phases", {}).setdefault("evidence_ledger", {})
    sections = phase.setdefault("sections", {})
    sections[PUBLIC_ACQUISITION_SECTION] = {
        "section": PUBLIC_ACQUISITION_SECTION,
        "title": "Public acquisition and archive evidence",
        "status": acquisition.get("status") or "available",
        "summary": _safe_text(acquisition.get("summary") or "Public catalog, website, Common Crawl and Wayback acquisition.", 400),
        "target_claim_safe": False,
        "source": "DueSight temporary_scrape_acquisition",
        "limitation": "Rows are review-only and bounded by robots/public catalog access.",
        "rows": rows,
        "diligence_questions": [
            "Which public acquisition rows should be replaced by official register or provider evidence before production use?"
        ],
    }
    existing_rows = [row for row in phase.get("rows", []) or [] if isinstance(row, dict)]
    existing_rows = [row for row in existing_rows if row.get("section") != PUBLIC_ACQUISITION_SECTION]
    phase["rows"] = existing_rows + rows


def _sanitize_premium_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    results = []
    for item in bundle.get("results") or []:
        if not isinstance(item, dict):
            continue
        results.append(
            {
                "provider": item.get("provider") or item.get("source") or "",
                "status": item.get("status") or "",
                "configured": bool(item.get("configured")),
                "latency_ms": item.get("latency_ms"),
                "error": _safe_text(item.get("error"), 180) if item.get("error") else "",
            }
        )
    return {
        "sources": bundle.get("sources") if isinstance(bundle.get("sources"), dict) else {},
        "results": results,
        "evidence": [item for item in bundle.get("evidence") or [] if isinstance(item, dict)],
    }


def _inject_premium_source_discovery(report: dict[str, Any], premium: dict[str, Any], checked_at: str) -> None:
    sanitized = _sanitize_premium_bundle(premium)
    report.setdefault("phases", {}).setdefault("enrichment", {})["premium_source_discovery"] = sanitized
    rows: list[dict[str, Any]] = []
    result_status: dict[str, str] = {
        str(item.get("provider") or "").lower(): str(item.get("status") or "unknown").upper()
        for item in sanitized.get("results") or []
        if isinstance(item, dict)
    }
    for idx, item in enumerate(sanitized.get("evidence") or [], start=1):
        source = _safe_text(item.get("source") or "Premium source", 80)
        status = result_status.get(source.lower(), "OK")
        is_registry = "handelsregister" in source.lower() or "register" in source.lower()
        confidence = 0.65 if is_registry else 0.48
        rows.append(
            {
                "section": PREMIUM_SOURCE_SECTION,
                "row_id": f"premium-source-{idx:02d}",
                "bucket": _safe_text(item.get("evidence_type") or item.get("title") or source, 120),
                "title": _safe_text(item.get("title") or item.get("name") or "", 180),
                "url": _safe_text(item.get("url") or "", 220),
                "snippet": _safe_text(item.get("snippet") or "", 420),
                "source": source,
                "source_status": status,
                "checked_at": checked_at,
                "freshness": _safe_text(item.get("published_date") or "live provider call", 80),
                "fallback_used": False,
                "confidence": confidence,
                "claim_safe_for_memo": False,
                "limitation": (
                    "Provider discovery row only; use it to route review and corroboration, "
                    "not as standalone proof."
                ),
            }
        )

    phase = report.setdefault("phases", {}).setdefault("evidence_ledger", {})
    sections = phase.setdefault("sections", {})
    sections[PREMIUM_SOURCE_SECTION] = {
        "section": PREMIUM_SOURCE_SECTION,
        "title": "Premium source discovery",
        "status": "available" if rows else "empty",
        "summary": "Target-specific Exa / premium-provider discovery layer for OSINT, adverse-media and registry routing.",
        "target_claim_safe": False,
        "source": "app.services.premium_sources.premium_budget_evidence",
        "limitation": "Discovery and routing layer; final report claims still require source-envelope corroboration.",
        "rows": rows,
        "diligence_questions": [
            "Which premium discovery rows should be promoted only after official or primary-source corroboration?"
        ],
    }
    existing_rows = [row for row in phase.get("rows", []) or [] if isinstance(row, dict)]
    existing_rows = [row for row in existing_rows if row.get("section") != PREMIUM_SOURCE_SECTION]
    phase["rows"] = existing_rows + rows


def _award_claim(award: dict[str, Any], company_name: str) -> str:
    label = award.get("source_label") or award.get("source") or "Award source"
    detail = []
    if award.get("rank"):
        detail.append(f"rank #{award.get('rank')}")
    if award.get("year"):
        detail.append(str(award.get("year")))
    if award.get("category"):
        detail.append(str(award.get("category")))
    if award.get("cagr_percent") is not None:
        try:
            detail.append(f"CAGR {float(award.get('cagr_percent')):.0f}%")
        except (TypeError, ValueError):
            pass
    suffix = f" ({', '.join(detail)})" if detail else ""
    return f"Local award intelligence returned {label}{suffix} for {company_name}; this is context until primary artifact proof is attached."


def _inject_award_intelligence(
    report: dict[str, Any],
    target: TargetConfig,
    modules: dict[str, Any],
    checked_at: str,
) -> dict[str, Any]:
    tool_cls = modules.get("AwardIntelTool")
    if tool_cls is None:
        result = {
            "company_name": target.company_name,
            "kvk_number": target.kvk_number,
            "status": "module_unavailable",
            "checked_at": checked_at,
            "award_count": 0,
            "awards": [],
            "source_envelopes": [],
            "limitations": ["Award intelligence module is unavailable in this environment."],
        }
    else:
        try:
            result = tool_cls().run(company_name=target.company_name, kvk_number=target.kvk_number)
        except Exception as exc:
            result = {
                "company_name": target.company_name,
                "kvk_number": target.kvk_number,
                "status": "failed",
                "checked_at": checked_at,
                "award_count": 0,
                "awards": [],
                "source_envelopes": [],
                "limitations": [f"Award intelligence lookup failed: {exc.__class__.__name__}: {_safe_text(exc, 160)}"],
            }

    rows: list[dict[str, Any]] = []
    awards = [item for item in result.get("awards") or [] if isinstance(item, dict)]
    envelopes = [item for item in result.get("source_envelopes") or [] if isinstance(item, dict)]
    for idx, award in enumerate(awards, start=1):
        envelope = envelopes[idx - 1] if idx - 1 < len(envelopes) else {}
        source_status = envelope.get("source_status") or award.get("source_status") or "recovered_seed_requires_primary_check"
        rows.append(
            {
                "section": AWARD_INTELLIGENCE_SECTION,
                "row_id": f"award-intelligence-{idx:02d}",
                "bucket": _safe_text(award.get("source_label") or award.get("source") or "Award intelligence", 120),
                "claim": _award_claim(award, target.company_name),
                "source": envelope.get("source") or award.get("source_label") or award.get("source") or "local_awards_sqlite",
                "source_status": source_status,
                "checked_at": envelope.get("checked_at") or result.get("checked_at") or checked_at,
                "freshness": envelope.get("freshness") or (f"award_year_{award.get('year')}" if award.get("year") else "checked"),
                "fallback_used": bool(envelope.get("fallback_used", not str(source_status).startswith("primary_"))),
                "confidence": envelope.get("confidence") or award.get("confidence") or "medium",
                "claim_safe_for_memo": False,
                "limitation": envelope.get("limitation")
                or award.get("evidence_note")
                or "Award hit is context only until primary page/PDF/article capture and source hash are attached.",
                "fields": {
                    "award_year": award.get("year"),
                    "rank": award.get("rank"),
                    "category": award.get("category"),
                    "cagr_percent": award.get("cagr_percent"),
                    "claim_level": award.get("claim_level") or envelope.get("claim_level") or "context_signal",
                    "revenue_floor_eur": (result.get("shadow_pl_patch") or {}).get("revenue_floor_eur"),
                    "revenue_ceiling_eur": (result.get("shadow_pl_patch") or {}).get("revenue_ceiling_eur"),
                    "recommended_revenue_eur": (result.get("shadow_pl_patch") or {}).get("recommended_revenue_eur"),
                },
            }
        )
    if not rows:
        rows.append(
            {
                "section": AWARD_INTELLIGENCE_SECTION,
                "row_id": "award-intelligence-00",
                "bucket": "Award intelligence",
                "claim": f"No local award/ranking hit was recorded for {target.company_name}.",
                "source": "tools.award_intel.award_intel_tool",
                "source_status": result.get("status") or "no_hit",
                "checked_at": result.get("checked_at") or checked_at,
                "freshness": "checked",
                "fallback_used": False,
                "confidence": "medium",
                "claim_safe_for_memo": False,
                "limitation": "No-hit is not proof that no award or distress signal exists; it only records this local lookup result.",
            }
        )

    phase = report.setdefault("phases", {}).setdefault("evidence_ledger", {})
    sections = phase.setdefault("sections", {})
    section_status = "available_with_primary_check_required" if result.get("status") == "hit" else result.get("status") or "available"
    sections[AWARD_INTELLIGENCE_SECTION] = {
        "section": AWARD_INTELLIGENCE_SECTION,
        "title": "Award and growth intelligence",
        "status": section_status,
        "summary": "Award/ranking and distress-source context from the restored local award intelligence layer.",
        "target_claim_safe": False,
        "source": "tools.award_intel.award_intel_tool + data/award_intel/awards.db",
        "limitation": "Context layer only; official finance and ownership claims still require primary documents or licensed provider evidence.",
        "rows": rows,
        "diligence_questions": [
            "Which primary award page/PDF/article should be attached and hashed before production use?",
            "Does the award-derived revenue context conflict with official filings or seller financials?",
        ],
    }
    existing_rows = [row for row in phase.get("rows", []) or [] if isinstance(row, dict)]
    existing_rows = [row for row in existing_rows if row.get("section") != AWARD_INTELLIGENCE_SECTION]
    phase["rows"] = existing_rows + rows
    report.setdefault("phases", {}).setdefault("enrichment", {})[AWARD_INTELLIGENCE_SECTION] = result
    return result


def _provider_status_from_preflight(provider_preflight: dict[str, Any] | None, provider: str) -> str:
    if not provider_preflight:
        return "not_checked"
    for item in provider_preflight.get("results") or []:
        if isinstance(item, dict) and str(item.get("provider") or "").lower() == provider.lower():
            return str(item.get("status") or "recorded")
    return "not_configured"


def _build_official_claim_ladder(
    target: TargetConfig,
    provider_preflight: dict[str, Any] | None,
    timestamp: str,
) -> dict[str, Any]:
    kyckr_status = _provider_status_from_preflight(provider_preflight, "Kyckr")
    sayari_status = _provider_status_from_preflight(provider_preflight, "Sayari")
    gleif_status = _provider_status_from_preflight(provider_preflight, "GLEIF")
    return {
        "schema_version": "duesight.official_claim_ladder.v1",
        "target": target.company_name,
        "updated_at": timestamp,
        "rule": (
            "Demo/context rows may explain why a number or signal is plausible; official finance_source "
            "and ownership_ubo claims require primary document/provider evidence with source hash or lawful gated extract."
        ),
        "ladder": [
            {
                "rank": 1,
                "provider": "KVK financial statements / Dataservice",
                "closes": "finance_source for NL",
                "use": "Official filings, XBRL/PDF, source hash",
                "claim_level": "Primary official",
                "nlist_status": "not_attached",
            },
            {
                "rank": 2,
                "provider": "KVK UBO extract/API",
                "closes": "ownership_ubo for NL",
                "use": "Only with lawful access or client-supplied extract",
                "claim_level": "Primary official / gated",
                "nlist_status": "not_attached",
            },
            {
                "rank": 3,
                "provider": "Kyckr",
                "closes": "Finance docs, register docs, UBO workflow, cross-border",
                "use": "Best first paid vendor test",
                "claim_level": "Official-register provider",
                "nlist_status": kyckr_status,
            },
            {
                "rank": 4,
                "provider": "Sayari",
                "closes": "Deep ownership graph, trade/sanctions context",
                "use": "Premium high-stakes add-on",
                "claim_level": "Licensed graph / enhanced DD",
                "nlist_status": sayari_status,
            },
            {
                "rank": 5,
                "provider": "Company.info / Webservices.nl",
                "closes": "NL dossiers, positions, org tree, annual statement methods",
                "use": "Pilot if document bytes/hash and ToS are cleared",
                "claim_level": "Enrichment to primary, or primary only if source docs hashable",
                "nlist_status": "not_configured_in_current_replay",
            },
            {
                "rank": 6,
                "provider": "Creditsafe / D&B",
                "closes": "Credit, directors, linkages, financial summaries",
                "use": "Commercial enrichment and monitoring",
                "claim_level": "Enrichment unless contract grants source proof",
                "nlist_status": "not_configured_in_current_replay",
            },
            {
                "rank": 7,
                "provider": "Companies House / GLEIF / Open data",
                "closes": "UK filings/PSC, LEI parent/child",
                "use": "Free corroboration",
                "claim_level": "Official/open corroboration",
                "nlist_status": gleif_status,
            },
        ],
        "current_blockers": ["finance_source", "ownership_ubo"],
        "upsell": (
            "Official claims package: attach KvK/Dataservice finance filings, lawful UBO extract or "
            "Kyckr/Sayari/Company.info evidence with document hash, then run the evidence replay again."
        ),
    }


def _run_provider_preflight(skip: bool) -> dict[str, Any] | None:
    if skip:
        return None
    tools_dir = Path(__file__).resolve().parent
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    from sample_report_provider_preflight import run_preflight, write_report

    payload = run_preflight()
    write_report(payload)
    return payload


def _provider_preflight_compact(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {"status": "skipped", "results": []}
    compact_results = []
    for item in payload.get("results") or []:
        if not isinstance(item, dict):
            continue
        compact_results.append(
            {
                "provider": item.get("provider") or "",
                "capability": item.get("capability") or "",
                "status": item.get("status") or "",
                "required": bool(item.get("required")),
                "configured": bool(item.get("configured")),
                "http_status": item.get("http_status"),
                "checked_at": item.get("checked_at") or "",
                "fallback_used": bool(item.get("fallback_used")),
                "confidence": item.get("confidence"),
                "limitation": item.get("limitation") or "",
                "attempts": item.get("attempts") or 0,
                "inline_retry_count": item.get("inline_retry_count") or 0,
                "retry_after_seconds": item.get("retry_after_seconds"),
                "next_retry_at": item.get("next_retry_at") or "",
                "rate_limit_policy": item.get("rate_limit_policy") or {},
            }
        )
    return {
        "status": "go" if payload.get("go_for_sample_rerun") else "blocked",
        "run_id": payload.get("run_id") or "",
        "timestamp": payload.get("timestamp") or "",
        "summary": payload.get("summary") or {},
        "hard_blockers": [item.get("provider") for item in payload.get("hard_blockers") or [] if isinstance(item, dict)],
        "results": compact_results,
    }


def _ollama_base_url() -> str:
    url = os.getenv("OLLAMA_HOST") or os.getenv("OLLAMA_URL") or "http://127.0.0.1:11434"
    if url.endswith("/api/generate"):
        url = url[: -len("/api/generate")]
    if "://" not in url:
        url = "http://" + url
    return url.rstrip("/")


def _request_json(url: str, payload: dict[str, Any] | None = None, timeout_s: int = 120) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST" if payload is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _select_local_synthesis_model() -> tuple[str, list[str]]:
    preferred = [
        os.getenv("DUESIGHT_XORTRON_MODEL", "").strip(),
        "xortron3-fast:Q5_K_M",
        "xortron:latest",
        "ministral-3:14b",
        "mistral-small3.2:latest",
        "qwen3.6:27b",
    ]
    data = _request_json(_ollama_base_url() + "/api/tags", timeout_s=10)
    models = [
        str(item.get("name") or "")
        for item in data.get("models", [])
        if isinstance(item, dict) and item.get("name")
    ]
    for wanted in preferred:
        if wanted and wanted in models:
            return wanted, models
    for model in models:
        if "14b" in model.lower() or "xortron" in model.lower():
            return model, models
    if models:
        return models[0], models
    raise RuntimeError("No local Ollama models available")


def _run_heavy_synthesis(target: TargetConfig, report: dict[str, Any], timeout_s: int) -> dict[str, Any]:
    started = time.perf_counter()
    model, available_models = _select_local_synthesis_model()
    rows = _representative_rows(report, max_rows=12)
    context = json.dumps(
        {
            "target": {
                "name": target.company_name,
                "domain": target.domain,
                "country": target.country,
                "tier": target.tier,
            },
            "evidence_rows": rows,
        },
        ensure_ascii=True,
    )[:14000]
    prompt = f"""You are DueSight's guarded Xortron synthesis layer.
Use ONLY the evidence rows below. Do not add facts. Do not claim completeness.
Return compact JSON with keys: status, executive_summary, guarded_signals, limitations, follow_up_questions.
Use a premium institutional tone.

EVIDENCE:
{context}
"""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": False,
        "options": {"temperature": 0.05, "num_predict": 900},
    }
    data = _request_json(_ollama_base_url() + "/api/chat", payload=payload, timeout_s=timeout_s)
    content = ((data.get("message") or {}).get("content") or "").strip()
    parsed: Any = None
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = {"status": "completed_limited", "raw_text": _safe_text(content, 2400)}
    return {
        "status": "completed",
        "source": "local_ollama",
        "model": model,
        "checked_at": _now_iso(),
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "available_models": available_models[:12],
        "synthesis": parsed,
        "limitations": [
            "Guarded synthesis only; not an evidence source and not a production due-diligence opinion.",
            "Uses only normalized evidence rows present in this sample replay.",
        ],
    }


def _should_run_heavy_synthesis(target: TargetConfig, args: argparse.Namespace) -> bool:
    return bool(
        args.orbit_max_stack
        or args.heavy_synthesis_for_all
        or (args.heavy_synthesis_for_premium and target.tier in {"gold", "premium"})
    )


def _run_mode(args: argparse.Namespace, heavy_requested: bool) -> str:
    if args.orbit_max_stack:
        return "orbit_max_stack_replay"
    if args.heavy_synthesis_for_all:
        return "heavy_synthesis_all_reports"
    if heavy_requested:
        return "tiered_heavy_synthesis_replay"
    return "evidence_only_replay"


def _build_modules(
    report: dict[str, Any],
    source_health: dict[str, Any] | None,
    provider_preflight: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    ledger = report.get("evidence_ledger") if isinstance(report.get("evidence_ledger"), dict) else {}
    sections = ledger.get("sections") if isinstance(ledger.get("sections"), dict) else {}
    modules: list[dict[str, Any]] = []
    for name in SECTION_ORDER:
        section = sections.get(name)
        if not isinstance(section, dict):
            modules.append({"name": name, "status": "not_run", "rows": 0, "limitations": ["No section output in this run."]})
            continue
        rows = _section_rows(section)
        limitations = _limit_list([str(row.get("limitation") or "") for row in rows if isinstance(row, dict)], 3)
        if section.get("limitation"):
            limitations = _limit_list([str(section.get("limitation")), *limitations], 3)
        modules.append(
            {
                "name": name,
                "status": section.get("status") or ("available" if rows else "empty"),
                "rows": len(rows),
                "source": section.get("source") or "",
                "target_claim_safe": bool(section.get("target_claim_safe")),
                "limitations": limitations,
            }
        )
    if source_health:
        summary = source_health.get("summary") if isinstance(source_health.get("summary"), dict) else {}
        modules.append(
            {
                "name": "source_health",
                "status": source_health.get("overall") or "unknown",
                "rows": int(summary.get("total") or 0),
                "source": "tools.source_health_live.run_all",
                "checked_at": source_health.get("ts") or "",
                "limitations": ["Global source-health snapshot; not a target-specific completeness proof."],
            }
        )
    if provider_preflight:
        preflight_results = provider_preflight.get("results") if isinstance(provider_preflight.get("results"), list) else []
        blocked = provider_preflight.get("status") == "blocked"
        rate_limited = [
            str(item.get("provider"))
            for item in preflight_results
            if isinstance(item, dict) and item.get("status") == "RATE_LIMITED"
        ]
        modules.append(
            {
                "name": "provider_preflight",
                "status": "blocked" if blocked else provider_preflight.get("status", "unknown"),
                "rows": len(preflight_results),
                "source": "tools.sample_report_provider_preflight.run_preflight",
                "checked_at": provider_preflight.get("timestamp") or "",
                "limitations": _limit_list(
                    [
                        "Provider readiness probe; not target-specific evidence.",
                        *(
                            f"{provider} hosted fallback needs recovery or paid/local coverage before production use."
                            for provider in rate_limited
                        ),
                    ],
                    5,
                ),
            }
        )
    enrichment = report.get("phases", {}).get("enrichment", {}) if isinstance(report.get("phases"), dict) else {}
    synthesis = enrichment.get("llm_orchestrator_synthesis") if isinstance(enrichment, dict) else None
    if isinstance(synthesis, dict) and synthesis:
        modules.append(
            {
                "name": "llm_orchestrator_synthesis",
                "status": synthesis.get("status") or "unknown",
                "rows": 1 if synthesis.get("status") == "completed" else 0,
                "source": synthesis.get("source") or "",
                "model": synthesis.get("model") or "",
                "checked_at": synthesis.get("checked_at") or "",
                "limitations": synthesis.get("limitations") or [
                    "Guarded LLM synthesis output; not an evidence source."
                ],
            }
        )
        return modules
    modules.append(
        {
            "name": "llm_orchestrator_synthesis",
            "status": "not_requested_evidence_only_replay",
            "rows": 0,
            "source": "not invoked",
            "limitations": ["No heavy LLM/orchestrator synthesis was requested during this replay certification pass."],
        }
    )
    return modules


def _build_manifest(
    *,
    target: TargetConfig,
    report: dict[str, Any],
    run_id: str,
    timestamp: str,
    source_health: dict[str, Any] | None,
    provider_preflight: dict[str, Any] | None,
    min_rows: int,
) -> dict[str, Any]:
    ledger = report.get("evidence_ledger") if isinstance(report.get("evidence_ledger"), dict) else {}
    rows = ledger.get("rows") if isinstance(ledger.get("rows"), list) else []
    envelope_complete = bool(ledger.get("source_envelope_complete"))
    status = "pipeline_certified_with_limitations" if envelope_complete and len(rows) >= min_rows else "pipeline_replay_incomplete"
    limitations = [
        "Public/local authorized sources only; no auth bypass, no database export, no invasive scraping.",
        "Demo/pre-DD preview only; no production completeness claim or legal advice.",
        "Point-in-time source statuses can change and must be rerun before customer use.",
    ]
    limitations.extend(target.limitations)
    if not re.fullmatch(r"\d{8}", target.kvk_number or ""):
        limitations.append("No trusted 8-digit KvK identifier supplied for this target in this replay.")
    enrichment = report.get("phases", {}).get("enrichment", {}) if isinstance(report.get("phases"), dict) else {}
    synthesis = enrichment.get("llm_orchestrator_synthesis") if isinstance(enrichment, dict) else {}
    synthesis_completed = isinstance(synthesis, dict) and synthesis.get("status") == "completed"
    run_mode = str(report.get("pipeline_run", {}).get("mode") or "")
    synthesis_requested = str(report.get("pipeline_run", {}).get("llm_orchestrator_synthesis") or "") in {
        "requested",
        "completed",
        "failed",
    }
    if synthesis_completed:
        limitations.append("Guarded local LLM synthesis completed; synthesis remains non-evidence and source-bound.")
    elif synthesis_requested or run_mode in {"orbit_max_stack_replay", "heavy_synthesis_all_reports", "tiered_heavy_synthesis_replay"}:
        limitations.append("Guarded LLM/orchestrator synthesis was requested but did not complete; rerun or inspect internal diagnostics before max-stack claims.")
    if not envelope_complete:
        limitations.append("One or more evidence rows did not satisfy the source-envelope contract.")
    if provider_preflight and provider_preflight.get("status") == "go":
        rate_limited = [
            item.get("provider")
            for item in provider_preflight.get("results", [])
            if isinstance(item, dict) and item.get("status") == "RATE_LIMITED"
        ]
        if rate_limited:
            limitations.append(
                "Hosted fallback readiness was not production-clean in preflight; local/alternative providers remain recorded and paid coverage is required before customer use."
            )

    return {
        "schema_version": "duesight.sample_report_pipeline_manifest.v1",
        "run_id": run_id,
        "timestamp": timestamp,
        "replay_mode": report.get("pipeline_run", {}),
        "target": {
            "slug": target.slug,
            "company_name": target.company_name,
            "domain": target.domain,
            "country": target.country,
            "kvk_number": target.kvk_number,
            "ch_uid": target.ch_uid,
            "tier": target.tier,
        },
        "status": status,
        "modules": _build_modules(report, source_health, provider_preflight),
        "intelligence_layers": list(INTELLIGENCE_LAYERS),
        "limitations": _limit_list(limitations, 12),
        "provider_preflight": _manifest_provider_preflight(provider_preflight),
        "evidence": {
            "normalizer": "report_output_normalizer.ensure_report_evidence_output",
            "normalized_report_path": "pipeline-evidence.json",
            "ledger_path": "evidence-ledger.json",
            "row_count": len(rows),
            "ledger_status": ledger.get("status") or "",
            "source_envelope_complete": envelope_complete,
            "required_row_fields": ledger.get("required_row_fields") or [],
            "source_envelope_incomplete_rows": ledger.get("source_envelope_incomplete_rows") or 0,
            "source_envelope_issues": ledger.get("source_envelope_issues") or [],
        },
        "verification": {
            "desktop": "pending",
            "mobile": "pending",
            "print_pdf": "pending",
        },
        "source_policy": {
            "allowed": [
                "public acquisition",
                "OpenSanctions/Yente where configured",
                "KvK public/readiness/official routes when available",
                "GLEIF",
                "Wayback",
                "source-health",
                "adverse media",
                "digital footprint",
                "sanctions/PEP",
                "evidence ledger",
            ],
            "blocked": ["database export", "auth bypass", "invasive scraping"],
        },
    }


def _representative_rows(report: dict[str, Any], max_rows: int = 8) -> list[dict[str, Any]]:
    ledger = report.get("evidence_ledger") if isinstance(report.get("evidence_ledger"), dict) else {}
    rows = [row for row in ledger.get("rows", []) or [] if isinstance(row, dict)]
    selected: list[dict[str, Any]] = []
    seen_sections: set[str] = set()
    for section in SECTION_ORDER:
        for row in rows:
            if row.get("section") == section and section not in seen_sections:
                selected.append(row)
                seen_sections.add(section)
                break
        if len(selected) >= max_rows:
            return selected
    for row in rows:
        if row not in selected:
            selected.append(row)
        if len(selected) >= max_rows:
            break
    return selected


def _render_pipeline_section(target: TargetConfig, manifest: dict[str, Any], report: dict[str, Any]) -> str:
    evidence = manifest["evidence"]
    score_policy = manifest.get("score_policy") if isinstance(manifest.get("score_policy"), dict) else {}
    score_text = score_policy.get("display_value") or "N/A"
    score_verdict = score_policy.get("verdict") or "UNSCORED"
    score_model = score_policy.get("score_model") or "not available"
    status_label = "CERTIFIED" if manifest["status"] == "pipeline_certified_with_limitations" else "LIMITED"
    rows = _representative_rows(report)
    layer_labels = [
        f"{layer.get('name')}: {layer.get('maps_to')}"
        for layer in manifest.get("intelligence_layers", [])
        if isinstance(layer, dict)
    ]
    module_labels = []
    for module in manifest.get("modules", []):
        if module.get("name") in {"llm_orchestrator_synthesis", "source_health", "provider_preflight"}:
            continue
        row_count = module.get("rows", 0)
        if row_count:
            module_labels.append(f"{module.get('name')}: {row_count}")
    row_html = []
    for row in rows:
        confidence_limitation = _public_confidence_limitation(row)
        row_html.append(
            "                    <tr>"
            f"<td>{_html(row.get('section') or row.get('bucket'), 70)}</td>"
            f"<td>{_html(_public_row_source(row), 90)}</td>"
            f"<td>{_html(_row_source_status(row), 70)}</td>"
            f"<td>{_html(row.get('checked_at'), 70)}</td>"
            f"<td>{_html(_public_row_freshness(row), 70)}</td>"
            f"<td>{_html(row.get('fallback_used'), 40)}</td>"
            f"<td>{_html(confidence_limitation, 150)}</td>"
            "</tr>"
        )
    limitations_html = "\n".join(f"                <li>{_html(item, 220)}</li>" for item in _public_limitations(manifest))
    layer_text = "; ".join(layer_labels[:5]) or "No intelligence layer taxonomy available."
    module_text = "; ".join(module_labels[:8]) or "No evidence rows returned."
    return f"""
        <div class="section pipeline-certification" id="pipeline-certification" data-run-id="{_html(manifest['run_id'], 120)}">
            <h2><span class="icon">&#x1F4CB;</span> Pipeline Certification</h2>
            <div class="pipeline-status-grid">
                <div class="pipeline-status-card"><span>Run status</span><strong>{status_label}</strong></div>
                <div class="pipeline-status-card"><span>Evidence rows</span><strong>{_html(evidence['row_count'])}</strong></div>
                <div class="pipeline-status-card"><span>Source envelope</span><strong>{'COMPLETE' if evidence['source_envelope_complete'] else 'INCOMPLETE'}</strong></div>
                <div class="pipeline-status-card"><span>Generated</span><strong>{_html(manifest['timestamp'], 32)}</strong></div>
            </div>
            <div class="metric-row pipeline-run-row"><span class="key">Pipeline run ID</span><span class="val">{_html(manifest['run_id'], 120)}</span></div>
            <div class="metric-row pipeline-run-row"><span class="key">Target</span><span class="val">{_html(target.company_name)} / {_html(target.domain)}</span></div>
            <div class="metric-row pipeline-run-row"><span class="key">Pipeline score</span><span class="val">{_html(score_text)} {_html(score_verdict)} - {_html(score_model, 120)}; not an investment verdict</span></div>
            <div class="metric-row pipeline-run-row"><span class="key">Intelligence layers</span><span class="val">{_html(layer_text, 420)}</span></div>
            <div class="metric-row pipeline-run-row"><span class="key">Modules with rows</span><span class="val">{_html(module_text, 260)}</span></div>
            <p class="pipeline-artifact-note">Replay artifacts remain internal; the public sample exposes only curated buyer-facing HTML.</p>
            <div class="pipeline-table-wrap">
                <table class="pipeline-evidence-table">
                    <thead><tr><th>Module</th><th>Source</th><th>Status</th><th>Checked</th><th>Freshness</th><th>Fallback</th><th>Confidence / limitation</th></tr></thead>
                    <tbody>
{chr(10).join(row_html)}
                    </tbody>
                </table>
            </div>
            <ul class="pipeline-limitations">
{limitations_html}
            </ul>
            <p class="pipeline-print-note">PDF/print-ready sample. This block certifies the replay evidence layer; it is not a production due-diligence opinion.</p>
        </div>""".rstrip()


def _style_block() -> str:
    return f"""
    <style id="pipeline-certification-style">
        {STYLE_START}
        .pipeline-certification {{
            color: var(--text-primary, var(--ds-text, #e2e8f0));
        }}
        .pipeline-status-grid {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            margin: 0 0 18px;
        }}
        .pipeline-status-card {{
            min-height: 86px;
            padding: 16px;
            border: 1px solid var(--border-glass, rgba(255,255,255,0.08));
            border-radius: 8px;
            background: rgba(15, 20, 40, 0.72);
        }}
        .pipeline-status-card span {{
            display: block;
            margin-bottom: 8px;
            color: var(--text-muted, var(--ds-muted, #64748b));
            font-size: 0.68rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }}
        .pipeline-status-card strong {{
            color: var(--accent-secondary, var(--ds-cyan, #22d3ee));
            font-size: 1rem;
            line-height: 1.25;
            word-break: break-word;
        }}
        .pipeline-run-row .val {{
            max-width: 58%;
            text-align: right;
            overflow-wrap: anywhere;
        }}
        .pipeline-artifact-links {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin: 18px 0;
        }}
        .pipeline-artifact-links a {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 36px;
            padding: 0 12px;
            border: 1px solid rgba(34,211,238,0.22);
            border-radius: 8px;
            color: var(--accent-secondary, var(--ds-cyan, #22d3ee));
            background: rgba(34,211,238,0.06);
            text-decoration: none;
            font-size: 0.78rem;
            font-weight: 700;
        }}
        .pipeline-table-wrap {{
            width: 100%;
            overflow-x: auto;
            border: 1px solid var(--border-glass, rgba(255,255,255,0.08));
            border-radius: 8px;
        }}
        .pipeline-evidence-table {{
            width: 100%;
            min-width: 760px;
            border-collapse: collapse;
            font-size: 0.72rem;
        }}
        .pipeline-evidence-table th,
        .pipeline-evidence-table td {{
            padding: 10px;
            border-bottom: 1px solid rgba(255,255,255,0.06);
            text-align: left;
            vertical-align: top;
            overflow-wrap: anywhere;
        }}
        .pipeline-evidence-table th {{
            color: var(--accent-secondary, var(--ds-cyan, #22d3ee));
            background: rgba(34,211,238,0.06);
            font-size: 0.66rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }}
        .pipeline-limitations {{
            margin: 18px 0 0 18px;
            color: var(--text-secondary, var(--ds-text-2, #94a3b8));
            font-size: 0.78rem;
            line-height: 1.6;
        }}
        .pipeline-print-note {{
            margin-top: 14px;
            color: var(--text-muted, var(--ds-muted, #64748b));
            font-size: 0.72rem;
            line-height: 1.5;
        }}
        @media (max-width: 768px) {{
            .pipeline-status-grid {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}
            .pipeline-run-row {{
                align-items: flex-start;
                gap: 8px;
            }}
            .pipeline-run-row .val {{
                max-width: 100%;
                text-align: right;
            }}
            .pipeline-artifact-links a {{
                flex: 1 1 100%;
            }}
        }}
        @media print {{
            .pipeline-certification {{
                break-inside: avoid;
                page-break-inside: avoid;
                color: #111827;
            }}
            .pipeline-status-card {{
                background: #ffffff;
                border: 1px solid #d8dee9;
            }}
            .pipeline-status-card strong,
            .pipeline-evidence-table th {{
                color: #0369a1;
            }}
            .pipeline-table-wrap {{
                overflow: visible;
                border: 1px solid #d8dee9;
            }}
            .pipeline-evidence-table {{
                min-width: 0;
                font-size: 8pt;
            }}
            .pipeline-evidence-table th,
            .pipeline-evidence-table td {{
                border-bottom: 1px solid #d8dee9;
                padding: 6px;
            }}
        }}
        {STYLE_END}
    </style>
""".strip()


def _replace_marked_block(text: str, start: str, end: str, replacement: str) -> tuple[str, bool]:
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if pattern.search(text):
        return pattern.sub(lambda _match: replacement, text), True
    return text, False


def _inject_style(text: str) -> str:
    style = _style_block()
    text, replaced = _replace_marked_block(text, STYLE_START, STYLE_END, f"{STYLE_START}\n        {STYLE_END}")
    if replaced:
        text = re.sub(
            r"<style id=\"pipeline-certification-style\">.*?</style>\s*",
            "",
            text,
            flags=re.S,
        )
    if "</head>" in text:
        return text.replace("</head>", f"{style}\n</head>", 1)
    return f"{style}\n{text}"


def _inject_section(index_path: Path, target: TargetConfig, manifest: dict[str, Any], report: dict[str, Any]) -> None:
    text = index_path.read_text(encoding="utf-8", errors="replace")
    text = _inject_style(text)
    section = f"{SECTION_START}\n{_render_pipeline_section(target, manifest, report)}\n{SECTION_END}\n"
    text, replaced = _replace_marked_block(text, SECTION_START, SECTION_END, section)
    if not replaced:
        score_pos = text.find('<div class="score-section">')
        next_section_pos = text.find('\n        <div class="section">', score_pos if score_pos >= 0 else 0)
        trust_footer_pos = text.find('        <div class="trust-footer">')
        if next_section_pos >= 0:
            text = text[:next_section_pos] + "\n" + section + text[next_section_pos:]
        elif trust_footer_pos >= 0:
            text = text[:trust_footer_pos] + section + text[trust_footer_pos:]
        elif "</body>" in text:
            text = text.replace("</body>", section + "</body>", 1)
        else:
            text += "\n" + section
    index_path.write_text(text, encoding="utf-8")


def _run_source_health(modules: dict[str, Any], website_dir: Path, skip: bool, *, force_refresh: bool = False) -> dict[str, Any] | None:
    if skip:
        return None
    ttl_s = int(float(os.getenv("DUESIGHT_SOURCE_HEALTH_CACHE_TTL_SECONDS", "1800") or "1800"))
    latest_path = website_dir / "sample-report-pipeline-source-health.json"
    if not force_refresh and ttl_s > 0 and latest_path.exists():
        try:
            age_s = time.time() - latest_path.stat().st_mtime
            if age_s <= ttl_s:
                cached = json.loads(latest_path.read_text(encoding="utf-8"))
                cached["cache_status"] = "reused_recent_snapshot"
                cached["cache_age_seconds"] = round(age_s, 1)
                return cached
        except Exception:
            pass
    snapshot = asyncio.run(modules["run_source_health"]())
    modules["write_source_health_outputs"](snapshot)
    _json_write(website_dir / "sample-report-pipeline-source-health.json", snapshot)
    return snapshot


def _run_target(
    *,
    target: TargetConfig,
    modules: dict[str, Any],
    args: argparse.Namespace,
    source_health: dict[str, Any] | None,
    provider_preflight: dict[str, Any] | None,
    root_run_id: str,
) -> dict[str, Any]:
    report_dir = WEBSITE_DIR / target.slug
    if not report_dir.exists():
        raise FileNotFoundError(f"Missing report directory: {report_dir}")

    run_id = f"{root_run_id}-{target.slug.removeprefix('sample-report-')}"
    timestamp = _now_iso()
    has_trusted_kvk = bool(re.fullmatch(r"\d{8}", target.kvk_number or ""))
    heavy_requested = _should_run_heavy_synthesis(target, args)
    run_mode = _run_mode(args, heavy_requested)
    print(f"[{target.slug}] replay start: {target.company_name} / {target.domain}", flush=True)
    report = modules["build_report"](
        domain=target.domain,
        company_name=target.company_name,
        max_ip_lookups=max(1, args.max_ip_lookups),
        use_cache=True,
        include_sanctions=True,
        sanctions_timeout_seconds=args.sanctions_timeout_seconds,
        include_finance=True,
        kvk_number=target.kvk_number if has_trusted_kvk else "",
        ch_uid=target.ch_uid,
        include_financial_fetch=has_trusted_kvk,
        financial_fetch_timeout_seconds=args.finance_fetch_timeout_seconds,
        include_regulatory_adverse=True,
        regulatory_country=target.regulatory_country,
        adverse_days=args.adverse_days,
        adverse_timeout_seconds=args.adverse_timeout_seconds,
        include_ownership_register=True,
        ownership_country=target.ownership_country,
        ownership_timeout_seconds=args.ownership_timeout_seconds,
        include_ubo_proxy=args.include_ubo_proxy or args.orbit_max_stack or target.tier in {"gold", "premium"},
        use_manual_control_fallback=True,
    )
    report["run_id"] = run_id
    report["pipeline_run"] = {
        "run_id": run_id,
        "timestamp": timestamp,
        "target_slug": target.slug,
        "mode": run_mode,
        "llm_orchestrator_synthesis": "requested" if heavy_requested else "not_requested",
        "orbit_max_stack": bool(args.orbit_max_stack),
    }

    if not args.skip_business_profile:
        profile = asyncio.run(
            modules["build_business_profile_intel"](
                company_name=target.company_name,
                website=target.domain,
                country=target.country,
                collect_live=True,
                max_pages=args.business_profile_pages,
                gdelt_timeout=8.0,
                website_timeout=args.website_timeout,
                include_gdelt=bool(
                    args.orbit_max_stack
                    and os.getenv("DUESIGHT_INLINE_GDELT_IN_SAMPLE", "").strip() in {"1", "true", "TRUE", "yes", "YES"}
                ),
                public_urls=list(target.public_urls),
            )
        )
        report.setdefault("phases", {}).setdefault("enrichment", {})["business_profile_intel"] = profile

    try:
        local_bulk = modules["build_local_bulk_source_inventory"](
            target_name=target.company_name,
            target_domain=target.domain,
        )
    except Exception as exc:
        local_bulk = {
            "schema_version": "duesight.local_bulk_source_inventory.v1",
            "target": {"name": target.company_name, "domain": target.domain},
            "status": "unavailable",
            "checked_at": _now_iso(),
            "rows": [],
            "limitations": [f"Local bulk inventory failed: {exc.__class__.__name__}: {_safe_text(exc, 160)}"],
        }
    report.setdefault("phases", {}).setdefault("enrichment", {})["local_bulk_inventory"] = local_bulk

    award_result = _inject_award_intelligence(report, target, modules, timestamp)

    if not args.skip_acquisition:
        acquisition = modules["run_acquisition"](
            target=target.company_name,
            domain=target.domain,
            country=target.country,
            rows=args.acquisition_rows,
            include_datagov=False,
            demo_promote=False,
        )
        report.setdefault("phases", {}).setdefault("enrichment", {})["public_acquisition"] = acquisition
        _inject_public_acquisition(report, acquisition)

    if not args.skip_premium_sources and modules.get("premium_budget_evidence"):
        premium = asyncio.run(
            modules["premium_budget_evidence"](
                target.company_name,
                country_hint=target.country,
                domain=target.domain,
            )
        )
        _inject_premium_source_discovery(report, premium, timestamp)

    report = modules["ensure_report_evidence_output"](report)
    report = _sanitize_public_artifact(report)

    if heavy_requested:
        try:
            synthesis = _run_heavy_synthesis(target, report, args.heavy_synthesis_timeout_seconds)
        except Exception as exc:
            synthesis = {
                "status": "failed",
                "source": "local_ollama",
                "checked_at": _now_iso(),
                "error": f"{exc.__class__.__name__}: {_safe_text(exc, 160)}",
                "limitations": ["Local guarded synthesis failed; evidence replay remains available."],
            }
        report.setdefault("phases", {}).setdefault("enrichment", {})["llm_orchestrator_synthesis"] = synthesis
        report.setdefault("pipeline_run", {})["llm_orchestrator_synthesis"] = synthesis.get("status") or "recorded"

    envelope = modules["summarize_source_envelope"](report.get("evidence_ledger", {}))
    report.setdefault("pipeline_run", {})["source_envelope"] = envelope
    manifest = _build_manifest(
        target=target,
        report=report,
        run_id=run_id,
        timestamp=timestamp,
        source_health=source_health,
        provider_preflight=provider_preflight,
        min_rows=args.min_rows,
    )
    official_claim_ladder = _build_official_claim_ladder(target, provider_preflight, timestamp)
    manifest["official_claim_ladder"] = {
        "path": "official-claim-ladder.json",
        "current_blockers": official_claim_ladder["current_blockers"],
        "updated_at": timestamp,
    }
    manifest["award_intelligence_summary"] = {
        "status": award_result.get("status") or "unknown",
        "award_count": award_result.get("award_count") or 0,
        "claim_policy": award_result.get("claim_policy") or {},
    }
    try:
        from tools.sample_report_score_model import compute_score

        manifest["score_policy"] = compute_score(manifest, report.get("evidence_ledger", {}))
    except Exception as exc:
        manifest["score_policy"] = {
            "aggregate_score_certified": False,
            "investment_verdict_certified": False,
            "score_kind": "DueSight Evidence Readiness Score",
            "score_model": "unavailable",
            "display_value": "N/A",
            "verdict": "UNSCORED",
            "reason": f"Score model failed: {exc.__class__.__name__}: {_safe_text(exc, 160)}",
        }

    _json_write(report_dir / "pipeline-evidence.json", report)
    _json_write(report_dir / "evidence-ledger.json", report.get("evidence_ledger", {}))
    _json_write(report_dir / "pipeline-manifest.json", manifest)
    _json_write(report_dir / "pipeline-score.json", manifest["score_policy"])
    _json_write(report_dir / "official-claim-ladder.json", official_claim_ladder)
    _inject_section(report_dir / "index.html", target, manifest, report)
    try:
        from sample_report_certified_renderer import render_report_pages

        render_report_pages(report_dir)
    except Exception as exc:
        print(f"[{target.slug}] certified renderer warning: {exc.__class__.__name__}: {exc}", flush=True)
    print(
        f"[{target.slug}] {manifest['status']} rows={manifest['evidence']['row_count']} "
        f"source_envelope={manifest['evidence']['source_envelope_complete']}",
        flush=True,
    )
    return {
        "slug": target.slug,
        "run_id": run_id,
        "status": manifest["status"],
        "row_count": manifest["evidence"]["row_count"],
        "source_envelope_complete": manifest["evidence"]["source_envelope_complete"],
        "manifest": str((report_dir / "pipeline-manifest.json").relative_to(WEBSITE_DIR)),
        "ledger": str((report_dir / "evidence-ledger.json").relative_to(WEBSITE_DIR)),
        "score": manifest.get("score_policy", {}).get("display_value"),
    }


def _parse_report_selection(value: str) -> list[TargetConfig]:
    if not value:
        return list(TARGETS)
    selected: list[TargetConfig] = []
    for raw in value.split(","):
        slug = raw.strip()
        if not slug:
            continue
        if not slug.startswith("sample-report-"):
            slug = f"sample-report-{slug}"
        if slug not in TARGET_BY_SLUG:
            raise SystemExit(f"Unknown sample report: {raw}")
        selected.append(TARGET_BY_SLUG[slug])
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay and certify DueSight sample-report evidence layers.")
    parser.add_argument("--agent-dir", default=str(DEFAULT_AGENT_DIR))
    parser.add_argument("--reports", default="", help="Comma-separated sample-report slugs or suffixes.")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--min-rows", type=int, default=5)
    parser.add_argument("--max-ip-lookups", type=int, default=1)
    parser.add_argument("--sanctions-timeout-seconds", type=int, default=20)
    parser.add_argument("--finance-fetch-timeout-seconds", type=int, default=15)
    parser.add_argument("--ownership-timeout-seconds", type=int, default=15)
    parser.add_argument("--adverse-timeout-seconds", type=int, default=20)
    parser.add_argument("--adverse-days", type=int, default=180)
    parser.add_argument("--business-profile-pages", type=int, default=3)
    parser.add_argument("--website-timeout", type=float, default=5.0)
    parser.add_argument("--acquisition-rows", type=int, default=3)
    parser.add_argument("--skip-provider-preflight", action="store_true")
    parser.add_argument("--skip-premium-sources", action="store_true")
    parser.add_argument("--heavy-synthesis-for-premium", action="store_true")
    parser.add_argument(
        "--heavy-synthesis-for-all",
        action="store_true",
        help="Run the guarded local LLM synthesis layer for every selected sample report.",
    )
    parser.add_argument(
        "--orbit-max-stack",
        action="store_true",
        help="Exercise the widest configured sample-report stack: deeper public profile, UBO proxy for all, acquisition rows and guarded local synthesis for all selected reports.",
    )
    parser.add_argument("--heavy-synthesis-timeout-seconds", type=int, default=180)
    parser.add_argument("--skip-source-health", action="store_true")
    parser.add_argument("--force-source-health-refresh", action="store_true", help="Bypass recent source-health snapshot cache and ping all health sources.")
    parser.add_argument("--skip-business-profile", action="store_true")
    parser.add_argument("--skip-acquisition", action="store_true")
    parser.add_argument(
        "--include-ubo-proxy",
        action="store_true",
        help="Run the guarded algorithmic UBO proxy for standard targets as part of a full certified replay.",
    )
    args = parser.parse_args()
    if args.orbit_max_stack:
        args.heavy_synthesis_for_all = True
        args.include_ubo_proxy = True
        args.business_profile_pages = max(args.business_profile_pages, 8)
        args.acquisition_rows = max(args.acquisition_rows, 8)
        args.max_ip_lookups = max(args.max_ip_lookups, 4)
        args.website_timeout = max(args.website_timeout, 8.0)
        args.finance_fetch_timeout_seconds = max(args.finance_fetch_timeout_seconds, 30)
        args.ownership_timeout_seconds = max(args.ownership_timeout_seconds, 30)
        args.adverse_timeout_seconds = max(args.adverse_timeout_seconds, 30)

    agent_dir = Path(args.agent_dir).resolve()
    modules = _load_agent_modules(agent_dir)
    provider_preflight = _provider_preflight_compact(_run_provider_preflight(args.skip_provider_preflight))
    if provider_preflight.get("status") == "blocked":
        summary = {
            "schema_version": "duesight.sample_report_pipeline_summary.v1",
            "run_id": args.run_id or f"sample-pipeline-replay-{_stamp()}",
            "timestamp": _now_iso(),
            "result_count": 0,
            "failure_count": 1,
        "provider_preflight": provider_preflight,
        "verification": dict(SUMMARY_VERIFICATION),
        "results": [],
        "failures": [{"slug": "provider_preflight", "error": "Provider preflight blocked sample rerun."}],
    }
        _json_write(WEBSITE_DIR / "sample-report-pipeline-summary.json", summary)
        print(json.dumps(summary, ensure_ascii=True, indent=2), flush=True)
        return 2
    source_health = _run_source_health(modules, WEBSITE_DIR, args.skip_source_health, force_refresh=args.force_source_health_refresh)
    root_run_id = args.run_id or f"sample-pipeline-replay-{_stamp()}"
    selected_targets = _parse_report_selection(args.reports)
    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for target in selected_targets:
        try:
            results.append(
                _run_target(
                    target=target,
                    modules=modules,
                    args=args,
                    source_health=source_health,
                    provider_preflight=provider_preflight,
                    root_run_id=root_run_id,
                )
            )
        except Exception as exc:  # Keep other sample reports replayable if one source route fails.
            failures.append({"slug": target.slug, "error": f"{exc.__class__.__name__}: {exc}"})
            print(f"[{target.slug}] FAILED {exc.__class__.__name__}: {exc}", flush=True)

    summary_results = results
    summary_failures = list(failures)
    if not failures:
        try:
            summary_results = _results_from_manifests(TARGETS)
        except Exception as exc:
            summary_failures.append({"slug": "manifest_summary", "error": f"{exc.__class__.__name__}: {exc}"})

    summary = {
        "schema_version": "duesight.sample_report_pipeline_summary.v1",
        "run_id": root_run_id,
        "timestamp": _now_iso(),
        "result_count": len(summary_results),
        "failure_count": len(summary_failures),
        "provider_preflight": provider_preflight,
        "verification": dict(SUMMARY_VERIFICATION),
        "results": summary_results,
        "failures": summary_failures,
    }
    _json_write(WEBSITE_DIR / "sample-report-pipeline-summary.json", summary)
    print(json.dumps(summary, ensure_ascii=True, indent=2), flush=True)
    return 0 if not summary_failures and len(results) == len(selected_targets) else 2


if __name__ == "__main__":
    raise SystemExit(main())
