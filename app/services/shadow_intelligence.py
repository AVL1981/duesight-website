from __future__ import annotations

import importlib.util
import os
import sys
import time
from pathlib import Path
from typing import Any


DEFAULT_SHADOW_PATH = Path.home() / "OneDrive" / "Desktop" / "ds-gap-closure"
SHADOW_MODULES = (
    "sanctions_monitor",
    "ner_pipeline",
    "security_scanner",
    "pep_media_linker",
    "cyber_surface",
    "regulator_checker",
    "registry_client",
    "media_intel",
    "dark_web_monitor",
)


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        raw = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        raw = default
    return max(minimum, min(raw, maximum))


def _shadow_root() -> Path:
    return Path(os.getenv("DS_GAP_CLOSURE_PATH", str(DEFAULT_SHADOW_PATH))).expanduser()


def _module_path(root: Path, module_name: str) -> Path:
    return root / "modules" / f"{module_name}.py"


def _load_shadow_module(root: Path, module_name: str):
    path = _module_path(root, module_name)
    if not path.exists():
        raise FileNotFoundError(f"shadow module not found: {path}")

    spec_name = f"duesight_shadow_{module_name}"
    spec = importlib.util.spec_from_file_location(spec_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load shadow module: {module_name}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec_name] = module
    spec.loader.exec_module(module)
    return module


def _ready_root(root: Path) -> tuple[bool, str | None]:
    if not root.exists():
        return False, f"DS gap-closure path not found: {root}"
    if not (root / "modules").exists():
        return False, f"shadow modules directory not found: {root / 'modules'}"
    return True, None


def _safe_text(value: Any, limit: int = 220) -> str:
    text = str(value or "").strip()
    return text[:limit]


def _provider_status(status: str, detail: str = "") -> dict[str, Any]:
    return {"status": status, "detail": _safe_text(detail)}


def _business_context_articles(company_name: str, domain: str, articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    domain_exact = domain.replace("www.", "").lower() if domain else ""
    domain_base = domain_exact.split(".")[0] if domain_exact else ""
    context_terms = {
        "payment",
        "payments",
        "fintech",
        "startup",
        "funding",
        "investment",
        "investor",
        "acquisition",
        "merger",
        "valuation",
        "regulator",
        "license",
        "bank",
        "merchant",
        "commerce",
        "revenue",
        "lawsuit",
        "breach",
        "fraud",
        "security",
    }
    company_token = company_name.lower().split()[0] if company_name else ""
    filtered: list[dict[str, Any]] = []
    for item in articles:
        haystack = " ".join(
            str(item.get(key, "")) for key in ("title", "snippet", "source")
        ).lower()
        if company_token and company_token not in haystack:
            continue
        if domain_exact and domain_exact in haystack:
            filtered.append(item)
            continue
        if domain_base and domain_base != company_token and domain_base in haystack:
            filtered.append(item)
            continue
        if any(term in haystack for term in context_terms):
            filtered.append(item)
    return filtered


def configured_shadow_intelligence() -> dict[str, Any]:
    root = _shadow_root()
    ready, error = _ready_root(root)
    return {
        "enabled": _env_flag("DUESIGHT_SHADOW_INTEL_ENABLED", True),
        "live_enabled": _env_flag("DUESIGHT_SHADOW_LIVE_ENABLED", True),
        "active_scans_allowed": _env_flag("DS_GAP_ALLOW_ACTIVE_SCANS", False),
        "path": str(root),
        "available": ready,
        "error": error,
    }


def shadow_readiness() -> dict[str, Any]:
    config = configured_shadow_intelligence()
    root = Path(config["path"])
    if not config["enabled"]:
        return {**config, "status": "skipped", "modules": []}
    if not config["available"]:
        return {**config, "status": "unavailable", "modules": []}

    modules: list[dict[str, Any]] = []
    for module_name in SHADOW_MODULES:
        started = time.perf_counter()
        row: dict[str, Any] = {"module": module_name, "status": "error"}
        try:
            module = _load_shadow_module(root, module_name)
            run_test = getattr(module, "run_test", None)
            if callable(run_test):
                result = run_test()
                row.update(
                    {
                        "status": "ok",
                        "capability": result.get("capability", module_name) if isinstance(result, dict) else module_name,
                        "mode": result.get("mode", "offline") if isinstance(result, dict) else "offline",
                    }
                )
            else:
                row.update({"status": "missing_run_test", "capability": module_name, "mode": "unknown"})
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {_safe_text(exc)}"
        row["elapsed_ms"] = int((time.perf_counter() - started) * 1000)
        modules.append(row)

    ok_count = sum(1 for item in modules if item.get("status") == "ok")
    return {
        **config,
        "status": "ok" if ok_count else "degraded",
        "modules": modules,
        "summary": {
            "modules_ready": ok_count,
            "modules_total": len(modules),
            "live_passive_default": config["live_enabled"],
            "active_scans_allowed": config["active_scans_allowed"],
        },
    }


def gather_shadow_intelligence(company_name: str, *, domain: str = "", country_hint: str = "") -> dict[str, Any]:
    """Gather bounded, passive-by-default Shadow Intelligence signals.

    Active vulnerability probing is never run here. It remains gated by
    `DS_GAP_ALLOW_ACTIVE_SCANS=1` and should only be used with written target
    permission.
    """
    started = time.perf_counter()
    readiness = shadow_readiness()
    if readiness.get("status") in {"skipped", "unavailable"}:
        return {
            **readiness,
            "signals": {},
            "evidence": [],
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
        }

    root = Path(readiness["path"])
    live_enabled = bool(readiness.get("live_enabled"))
    signals: dict[str, Any] = {}
    evidence: list[dict[str, Any]] = []
    source_status: dict[str, dict[str, Any]] = {}

    # Lightweight NER smoke against the target context. This may return an empty
    # list when no local model is installed; that is a valid, non-blocking state.
    if _env_flag("DUESIGHT_SHADOW_NER_ENABLED", False):
        try:
            ner = _load_shadow_module(root, "ner_pipeline")
            entities = ner.extract_entities(
                f"{company_name} due diligence sanctions PEP adverse media regulator ownership",
                labels=["organization", "financial crime", "adverse event", "sanctioned entity"],
            )
            signals["entities"] = entities[:8]
            source_status["ner_pipeline"] = _provider_status("ok", f"{len(entities)} entities")
        except Exception as exc:
            signals["entities"] = []
            source_status["ner_pipeline"] = _provider_status("degraded", exc)
    else:
        signals["entities"] = []
        source_status["ner_pipeline"] = _provider_status("skipped", "set DUESIGHT_SHADOW_NER_ENABLED=true")

    if live_enabled:
        try:
            media = _load_shadow_module(root, "media_intel")
            media.REQUEST_TIMEOUT = min(getattr(media, "REQUEST_TIMEOUT", 30), 8)
            days = _bounded_int("DUESIGHT_SHADOW_MEDIA_DAYS", 14, 1, 60)
            domain_base = domain.replace("www.", "").split(".")[0] if domain else ""
            context_terms = (
                f"{domain_base} OR company OR business OR regulator OR acquisition OR funding OR breach OR fraud"
                if domain_base
                else "company OR business OR regulator OR acquisition OR funding OR breach OR fraud"
            )
            media_query = f'"{company_name}" ({context_terms})'
            articles = media.search_google_news(media_query, days=days)
            filtered_articles = _business_context_articles(company_name, domain, articles)
            compact_articles = [
                {
                    "title": item.get("title", ""),
                    "source": item.get("source", ""),
                    "url": item.get("url", ""),
                    "date": item.get("date", ""),
                }
                for item in filtered_articles[:5]
            ]
            signals["media"] = {
                "articles_found": len(filtered_articles),
                "raw_articles_found": len(articles),
                "top_articles": compact_articles,
            }
            for item in compact_articles[:3]:
                evidence.append({"source": "Google News RSS", **item})
            source_status["media_intel"] = _provider_status(
                "ok",
                f"{len(filtered_articles)} DD-context articles ({len(articles)} raw)",
            )
        except Exception as exc:
            signals["media"] = {"articles_found": 0, "top_articles": []}
            source_status["media_intel"] = _provider_status("degraded", exc)

        if domain:
            try:
                dark = _load_shadow_module(root, "dark_web_monitor")
                mon = dark.DarkWebMonitor(timeout=8)
                breaches = mon.check_breach(domain)
                signals["breach_darkweb"] = {
                    "domain": domain,
                    "breach_count": len(breaches),
                    "breaches": breaches[:5],
                    "ahmia_checked": False,
                }
                if _env_flag("DUESIGHT_SHADOW_AHMIA_ENABLED", False):
                    ahmia = mon.search_ahmia(company_name)
                    signals["breach_darkweb"]["ahmia_checked"] = True
                    signals["breach_darkweb"]["ahmia_hits"] = ahmia[:5]
                source_status["dark_web_monitor"] = _provider_status("ok", f"{len(breaches)} public breach hits")
            except Exception as exc:
                signals["breach_darkweb"] = {"domain": domain, "breach_count": 0, "breaches": []}
                source_status["dark_web_monitor"] = _provider_status("degraded", exc)

            if _env_flag("DUESIGHT_SHADOW_CYBER_SURFACE_ENABLED", False):
                try:
                    cyber = _load_shadow_module(root, "cyber_surface")
                    cyber.REQUEST_TIMEOUT = min(getattr(cyber, "REQUEST_TIMEOUT", 30), 8)
                    surface = cyber.discover_surface(domain)
                    signals["cyber_surface"] = {
                        "domain": domain,
                        "subdomains": surface.get("subdomains", [])[:20],
                        "subdomain_count": len(surface.get("subdomains", [])),
                        "ip_count": len(surface.get("ips", [])),
                        "certificate_count": len(surface.get("certificates", [])),
                        "risk_score": surface.get("risk_score", 0),
                        "active_checks_allowed": surface.get("active_checks_allowed", False),
                    }
                    source_status["cyber_surface"] = _provider_status(
                        "ok",
                        f"{signals['cyber_surface']['subdomain_count']} subdomains",
                    )
                except Exception as exc:
                    signals["cyber_surface"] = {"domain": domain, "subdomain_count": 0, "risk_score": 0}
                    source_status["cyber_surface"] = _provider_status("degraded", exc)

        if country_hint.upper() in {"US", "USA", "UNITED STATES"}:
            try:
                reg = _load_shadow_module(root, "regulator_checker")
                sec = reg.check_sec_edgar(company_name)
                signals["regulators"] = {"sec_edgar": sec}
                source_status["regulator_checker"] = _provider_status("ok", sec.get("status", "unknown"))
            except Exception as exc:
                signals["regulators"] = {}
                source_status["regulator_checker"] = _provider_status("degraded", exc)

    modules_ready = readiness.get("summary", {}).get("modules_ready", 0)
    modules_total = readiness.get("summary", {}).get("modules_total", len(SHADOW_MODULES))
    return {
        **readiness,
        "status": "ok" if modules_ready else "degraded",
        "company_name": company_name,
        "domain": domain,
        "country_hint": country_hint,
        "signals": signals,
        "evidence": evidence,
        "source_status": source_status,
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
        "commercial_claim": (
            "Passive Shadow Intelligence: sanctions-delta readiness, NER/entity extraction, "
            "PEP-media linkage readiness, live media/breach/cyber-surface signals, active scans consent-only."
        ),
        "summary": {
            **readiness.get("summary", {}),
            "evidence_count": len(evidence),
            "live_sources_checked": len(source_status),
            "active_scans_allowed": _env_flag("DS_GAP_ALLOW_ACTIVE_SCANS", False),
        },
    }
