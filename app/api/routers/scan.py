import asyncio
import logging
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query

from app.services.ddintel import call_ddintel

router = APIRouter()


def _agent_tools_candidates() -> list[Path]:
    configured = os.getenv("DUESIGHT_AGENT_TOOLS_DIR", "").strip()
    candidates = []
    if configured:
        candidates.append(Path(configured).expanduser())

    repo_root = Path(__file__).resolve().parents[3]
    workspace_root = repo_root.parent
    candidates.extend([
        workspace_root / "duesight-agent" / "tools",
        repo_root / "tools",
    ])
    return candidates


def _ensure_agent_tools_import_path() -> Path | None:
    for tools_dir in _agent_tools_candidates():
        if tools_dir.exists():
            package_root = tools_dir.parent
            if str(package_root) not in sys.path:
                sys.path.insert(0, str(package_root))
            return tools_dir
    return None


def _derive_domain(company_name: str) -> str:
    clean = re.sub(
        r"\b(B\.?V\.?|N\.?V\.?|BV|NV|Holding|Group)\b",
        "",
        company_name,
        flags=re.IGNORECASE,
    ).strip(" ,")
    slug = re.sub(r"[^a-zA-Z0-9]", "", clean.lower())
    return f"{slug}.nl" if slug else "example.com"


def _is_public_github_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
        return False
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    return len(parts) >= 2 and all(parts[:2])


@router.get("/kvk")
async def kvk_scan_endpoint(company_name: str = Query(..., description="Target company")):
    result = await call_ddintel("kvk_screen", {"company_name": company_name})
    if "error" in result:
        return {"status": "error", "error": result["error"]}
    return {
        "status": "ok",
        "module": "entity",
        "kvk_number": result.get("kvk_number", ""),
        "trade_name": result.get("trade_name", company_name),
        "status_active": result.get("active", True),
        "founding_date": result.get("founding_date", ""),
        "legal_form": result.get("legal_form", ""),
        "city": result.get("city", ""),
        "sbi_code": result.get("sbi_code", ""),
        "sbi_description": result.get("sbi_description", ""),
        "risk_flags": result.get("risk_flags", []),
        "data_quality": result.get("data_quality", ""),
    }

@router.get("/tech")
async def tech_scan_endpoint(domain: str = Query(...)):
    result = await call_ddintel("scan_tech_stack", {"domain": domain})
    if "error" in result:
        return {"status": "error", "error": result["error"]}

    technologies = result.get("technologies", result.get("detected", []))
    if isinstance(technologies, dict):
        flat = []
        for category, techs in technologies.items():
            if isinstance(techs, list):
                flat.extend(techs)
            elif isinstance(techs, str):
                flat.append(techs)
        technologies = flat

    return {
        "status": "ok",
        "module": "tech_stack",
        "count": len(technologies),
        "technologies": technologies[:10],
        "summary": ", ".join(str(t) for t in technologies[:4]) + ("..." if len(technologies) > 4 else ""),
    }

@router.get("/tech-scan-active")
async def tech_scan_active_endpoint(
    github_url: str = Query(..., min_length=12, max_length=300, description="Public GitHub repo URL of the target company"),
    company_name: str = Query("", max_length=160, description="Optional target label for memo context"),
):
    """
    ACTIVE code scan: Trivy SCA + OpenGrep SAST + TruffleHog secrets on public GitHub repo.
    ONLY use on public repos (no auth required). For private code, target consent is needed.

    Free preview mode: returns top 3 findings + risk score only (full report = paid tier).
    """
    if not _is_public_github_url(github_url):
        raise HTTPException(
            status_code=400,
            detail="Only public https://github.com/owner/repo URLs are accepted for active code scans.",
        )

    tools_dir = _ensure_agent_tools_import_path()
    try:
        from tools.active_code_scanner import ActiveCodeScanner  # type: ignore
    except ImportError as e:
        return {
            "status": "error",
            "error": "active_code_scanner module unavailable",
            "tools_dir": str(tools_dir) if tools_dir else "",
            "detail": str(e),
        }

    scanner = ActiveCodeScanner()
    available = scanner.available_tools()
    if not any(available.values()):
        return {
            "status": "no_tools",
            "available": available,
            "summary": "Geen actieve security-tools geïnstalleerd. Valt terug op passieve NVD/InternetDB scan via /tech endpoint.",
            "install_hint": "Windows: winget install AquaSecurity.Trivy + scoop install opengrep trufflehog",
        }

    result = await asyncio.to_thread(scanner.scan_repo, github_url, company_name or github_url)
    findings = result.findings if hasattr(result, "findings") else []

    # Free preview: top 3 only
    top3 = sorted(findings, key=lambda f: ({"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(f.severity, 4), -float(f.cvss_score or 0)))[:3]

    return {
        "status": "ok" if not result.errors else "partial",
        "module": "active_code_scan",
        "target": github_url,
        "company_name": company_name,
        "tools_run": result.tools_run,
        "tools_skipped": result.tools_skipped,
        "available": available,
        "risk_score": result.risk_score,
        "findings_total": len(findings),
        "findings_preview": [
            {
                "tool": f.tool,
                "severity": f.severity,
                "title": f.title,
                "cve_id": f.cve_id,
                "package": f.package,
                "fixed_version": f.fixed_version,
                "file_path": f.file_path,
                "is_secret": f.is_secret,
            } for f in top3
        ],
        "cta": {
            "message": f"{len(findings)} findings gevonden. Volledige Tech-DD rapport + risk-radar €79.",
            "url": "/tech-security-scanner.html?upgrade=1",
        },
    }

@router.get("/security")
async def security_scan_endpoint(domain: str = Query(...)):
    headers_result, cyber_result = await asyncio.gather(
        call_ddintel("check_security_headers", {"domain": domain}),
        call_ddintel("cyber_assess", {"domain": domain}),
        return_exceptions=True,
    )

    headers_score = 0
    missing_headers = []
    if isinstance(headers_result, dict) and "error" not in headers_result:
        headers_score = headers_result.get("score", headers_result.get("security_score", 0))
        missing = headers_result.get("missing_headers", headers_result.get("missing", []))
        if isinstance(missing, list):
            missing_headers = missing

    exposure_score = 0
    cve_count = 0
    open_ports = 0
    risk_level = "Unknown"
    if isinstance(cyber_result, dict) and "error" not in cyber_result:
        exposure_score = cyber_result.get("exposure_score", 0)
        cve_count = len(cyber_result.get("cves", cyber_result.get("vulnerabilities", [])))
        open_ports = len(cyber_result.get("open_ports", cyber_result.get("ports", [])))
        risk_level = cyber_result.get("risk_level", "Unknown")

    flags = []
    if missing_headers:
        flags.append(f"{len(missing_headers)} ontbrekende security headers")
    if cve_count > 0:
        flags.append(f"{cve_count} bekende kwetsbaarheden (CVE)")
    if open_ports > 5:
        flags.append(f"{open_ports} open poorten gedetecteerd")

    return {
        "status": "ok",
        "module": "cyber",
        "headers_score": headers_score,
        "exposure_score": exposure_score,
        "cve_count": cve_count,
        "open_ports": open_ports,
        "risk_level": risk_level,
        "flags_count": len(flags),
        "flags": flags,
        "missing_headers": missing_headers[:3],
    }


@router.post("/teaser-scan")
async def teaser_scan_endpoint(
    company_name: str = Query(..., min_length=2, max_length=160, description="Company name to scan"),
    domain: str = Query("", max_length=255, description="Optional domain override"),
):
    """Public preview scan contract used by the homepage.

    The response exposes full low-risk preview cards and keeps deeper financial,
    cyber and sanction detail behind checkout.
    """
    start = time.time()
    normalized_domain = domain.strip() or _derive_domain(company_name)

    kvk_result, tech_result, security_result, financial_result = await asyncio.gather(
        call_ddintel("kvk_screen", {"company_name": company_name}),
        call_ddintel("scan_tech_stack", {"domain": normalized_domain}),
        call_ddintel("check_security_headers", {"domain": normalized_domain}),
        call_ddintel("financial_proxy_analysis", {"company_name": company_name}),
        return_exceptions=True,
    )

    def ok_dict(result):
        return result if isinstance(result, dict) else {"status": "error", "error": str(result)}

    kvk = ok_dict(kvk_result)
    tech = ok_dict(tech_result)
    security = ok_dict(security_result)
    financial = ok_dict(financial_result)

    technologies = tech.get("technologies", tech.get("detected", []))
    if isinstance(technologies, dict):
        flat = []
        for techs in technologies.values():
            if isinstance(techs, list):
                flat.extend(techs)
            elif isinstance(techs, str):
                flat.append(techs)
        technologies = flat
    if not isinstance(technologies, list):
        technologies = []

    security_flags = []
    missing = security.get("missing_headers", security.get("missing", []))
    if isinstance(missing, list) and missing:
        security_flags.append(f"{len(missing)} ontbrekende security headers")
    if security.get("score", security.get("security_score", 100)) < 60:
        security_flags.append("lage security-header score")

    financial_flags = financial.get("risk_flags", [])
    if not isinstance(financial_flags, list):
        financial_flags = []

    total_flags = len(security_flags) + len(financial_flags)
    active = kvk.get("active", kvk.get("status_active", True))
    legal_form = kvk.get("legal_form", kvk.get("rechtsvorm", ""))
    city = kvk.get("city", kvk.get("plaats", ""))

    return {
        "status": "ok",
        "company": company_name,
        "domain": normalized_domain,
        "scan_time_seconds": round(time.time() - start, 2),
        "source_scope": "public-source preview",
        "total_flags": total_flags,
        "entity": {
            "status": "ok" if "error" not in kvk else "error",
            "trade_name": kvk.get("trade_name", kvk.get("name", company_name)),
            "kvk_number": kvk.get("kvk_number", ""),
            "status_active": bool(active),
            "legal_form": legal_form,
            "city": city,
            "risk_flags": kvk.get("risk_flags", []) if isinstance(kvk.get("risk_flags", []), list) else [],
        },
        "tech_stack": {
            "status": "ok" if "error" not in tech else "error",
            "count": len(technologies),
            "technologies": technologies[:10],
            "summary": ", ".join(str(t) for t in technologies[:4]) + ("..." if len(technologies) > 4 else ""),
        },
        "financial": {
            "status": "ok" if "error" not in financial else "error",
            "has_data": "error" not in financial,
            "hint": "Financiele proxy beschikbaar" if "error" not in financial else "Geen openbare proxydata",
            "flags_count": len(financial_flags),
        },
        "cyber": {
            "status": "ok" if "error" not in security else "error",
            "has_data": "error" not in security,
            "flags_count": len(security_flags),
            "risk_level": security.get("risk_level", "Preview"),
        },
    }

@router.get("/nis2-scan")
async def nis2_scan_endpoint(domain: str = Query(...)):
    headers_result, cyber_result, mitre_result = await asyncio.gather(
        call_ddintel("check_security_headers", {"domain": domain}),
        call_ddintel("cyber_assess", {"domain": domain}),
        call_ddintel("mitre_attack_mapping", {"domain": domain}),
        return_exceptions=True,
    )

    headers_score = 0
    headers_grade = "?"
    missing_headers = []
    if isinstance(headers_result, dict) and "error" not in headers_result:
        headers_score = headers_result.get("score", 0)
        headers_grade = headers_result.get("grade", "?")
        missing = headers_result.get("headers_missing", [])
        if isinstance(missing, list):
            missing_headers = [h if isinstance(h, str) else h.get("name", "") for h in missing]

    exposure_score = 0
    exposure_level = "UNKNOWN"
    open_ports = 0
    cve_count = 0
    dangerous_ports = []
    recommendations = []
    if isinstance(cyber_result, dict) and "error" not in cyber_result:
        exposure_score = cyber_result.get("exposure_score", 0)
        exposure_level = cyber_result.get("exposure_level", "UNKNOWN")
        host_info = cyber_result.get("host_info", {})
        open_ports = host_info.get("port_count", 0)
        cve_count = cyber_result.get("cve_count", 0)
        risk_flags = cyber_result.get("risk_flags", [])
        dangerous_ports = [
            f for f in risk_flags
            if isinstance(f, dict) and f.get("type") == "DANGEROUS_PORT"
        ]
        recommendations = cyber_result.get("recommendations", [])

    mitre_techniques = 0
    kill_chain_phases = []
    if isinstance(mitre_result, dict) and "error" not in mitre_result:
        mitre_techniques = mitre_result.get("total_techniques", 0)
        kill_chain_phases = list(mitre_result.get("kill_chain_coverage", {}).keys())

    headers_compliance = min(headers_score, 100)
    exposure_compliance = max(0, 100 - exposure_score)
    mitre_compliance = max(0, 100 - (mitre_techniques * 10))
    nis2_score = int(
        (headers_compliance * 0.30)
        + (exposure_compliance * 0.40)
        + (mitre_compliance * 0.30)
    )

    flags = []
    if headers_score < 50:
        flags.append({
            "severity": "HIGH",
            "category": "NIS2 Art. 21(2)(d)",
            "description": f"Security headers scoren {headers_grade} â€” supply chain risico",
        })
    if cve_count > 0:
        flags.append({
            "severity": "CRITICAL",
            "category": "NIS2 Art. 21(2)(e)",
            "description": f"{cve_count} bekende kwetsbaarhe(i)d(en) â€” patch management",
        })
    if len(dangerous_ports) > 0:
        ports_str = ", ".join(str(p.get("port", "?")) for p in dangerous_ports[:5])
        flags.append({
            "severity": "HIGH",
            "category": "NIS2 Art. 21(2)(a)",
            "description": f"Gevaarlijke poorten extern: {ports_str}",
        })
    if open_ports > 20:
        flags.append({
            "severity": "MEDIUM",
            "category": "NIS2 Art. 21(2)(a)",
            "description": f"{open_ports} open poorten â€” groot aanvalsoppervlak",
        })

    if nis2_score >= 75:
        verdict = "COMPLIANT"
        verdict_label = "âœ… Leverancier voldoet aan NIS2 basislijn"
    elif nis2_score >= 50:
        verdict = "PARTIAL"
        verdict_label = "âš ï¸ Gedeeltelijke naleving â€” aanvullende maatregelen vereist"
    else:
        verdict = "NON_COMPLIANT"
        verdict_label = "âŒ Leverancier voldoet NIET aan NIS2 basislijn"

    return {
        "status": "ok",
        "module": "nis2",
        "domain": domain,
        "nis2_score": nis2_score,
        "verdict": verdict,
        "verdict_label": verdict_label,
        "components": {
            "headers": {
                "score": headers_score,
                "grade": headers_grade,
                "missing": missing_headers[:5],
            },
            "exposure": {
                "score": exposure_score,
                "level": exposure_level,
                "open_ports": open_ports,
                "cve_count": cve_count,
            },
            "mitre": {
                "techniques_mapped": mitre_techniques,
                "kill_chain_phases": kill_chain_phases[:5],
            },
        },
        "risk_flags": flags,
        "recommendations": recommendations[:5],
        "methodology": "DueSight NIS2 Supplier Screening v1.0",
    }
