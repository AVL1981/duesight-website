from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

LIVE_REQUIRED_PAGES = (
    {
        "slug": "terms",
        "label": "Algemene voorwaarden / Terms",
        "routes": ("terms/", "terms.html"),
        "counsel_required": True,
    },
    {
        "slug": "refund",
        "label": "Refund policy",
        "routes": ("refund/", "refund.html"),
        "counsel_required": True,
    },
    {
        "slug": "cookies",
        "label": "Cookie policy",
        "routes": ("cookies/", "cookies.html", "cookie-policy/"),
        "counsel_required": True,
    },
    {
        "slug": "sla",
        "label": "Service level agreement",
        "routes": ("sla/", "sla.html"),
        "counsel_required": True,
    },
    {
        "slug": "incident",
        "label": "Incident response procedure",
        "routes": ("incident/", "incident.html"),
        "counsel_required": True,
    },
)

SUPPORT_PAGES = (
    {"slug": "privacy", "label": "Privacyverklaring", "routes": ("privacy/",)},
    {"slug": "dpa", "label": "Data Processing Agreement", "routes": ("dpa/", "dpa.html")},
    {"slug": "dataretentie", "label": "Dataretentie", "routes": ("dataretentie/",)},
    {"slug": "assurance", "label": "Trust / assurance hub", "routes": ("assurance/",)},
    {"slug": "security", "label": "Security / responsible disclosure", "routes": ("security/",)},
    {"slug": "ai-transparantie", "label": "AI Act transparency", "routes": ("ai-transparantie/",)},
    {"slug": "subprocessors", "label": "Sub-processors", "routes": ("subprocessors/",)},
)

HOMEPAGE_REQUIRED_LINKS = {
    "privacy": ("privacy/",),
    "dpa": ("dpa/", "dpa.html"),
    "trust_security": ("assurance/", "security/"),
}

FORBIDDEN_LEGAL_STATUS_PATTERNS = {
    "avg_conform": re.compile(r"\bAVG[-\s]?conform\b", re.I),
    "gdpr_conform": re.compile(r"\bGDPR[-\s]?conform\b|\bGDPR[-\s]?compliant\b", re.I),
    "eu_ai_act_ready": re.compile(r"\bEU\s+AI\s+Act\s+ready\b", re.I),
    "eu_ai_act_conform": re.compile(r"\bEU\s+AI\s+Act[-\s]?conform\b|\bEU\s+AI\s+Act\s+compliant\b", re.I),
}

LEGAL_REVIEW_APPROVAL_PATTERNS = {
    "meta": re.compile(
        r"""<meta\s+[^>]*name=["']duesight-legal-review["'][^>]*content=["']approved["']""",
        re.I,
    ),
    "data_attr": re.compile(r"""data-legal-review=["']approved["']""", re.I),
    "html_comment": re.compile(r"""<!--\s*duesight-legal-review:\s*approved\s*-->""", re.I),
}


def _candidate_path(root: Path, route: str) -> Path:
    normalized = route.strip().lstrip("/")
    if normalized.endswith("/"):
        return root / normalized / "index.html"
    return root / normalized


def _page_status(root: Path, page: dict[str, Any], *, required_before_live: bool) -> dict[str, Any]:
    candidates = [_candidate_path(root, route) for route in page["routes"]]
    existing = [path for path in candidates if path.exists()]
    review_evidence = []
    if page.get("counsel_required"):
        for path in existing:
            html = path.read_text(encoding="utf-8", errors="ignore")
            for name, pattern in LEGAL_REVIEW_APPROVAL_PATTERNS.items():
                if pattern.search(html):
                    review_evidence.append({"path": str(path), "marker": name})
    return {
        "slug": page["slug"],
        "label": page["label"],
        "required_before_live": required_before_live,
        "counsel_required": bool(page.get("counsel_required", False)),
        "counsel_review_approved": bool(review_evidence),
        "counsel_review_evidence": review_evidence,
        "present": bool(existing),
        "routes": list(page["routes"]),
        "paths": [str(path) for path in candidates],
        "existing_paths": [str(path) for path in existing],
    }


def _hrefs(html: str) -> set[str]:
    return {
        match.group(1).strip().lstrip("./")
        for match in re.finditer(r"""href=["']([^"']+)["']""", html, re.I)
    }


def _has_any_link(hrefs: set[str], candidates: tuple[str, ...]) -> bool:
    normalized = {href.lstrip("/") for href in hrefs}
    for candidate in candidates:
        c = candidate.lstrip("/")
        if c in normalized or f"{c}index.html" in normalized:
            return True
    return False


def build_report(root: Path = ROOT) -> dict[str, Any]:
    index_path = root / "index.html"
    homepage = index_path.read_text(encoding="utf-8", errors="ignore") if index_path.exists() else ""
    hrefs = _hrefs(homepage)

    live_pages = [_page_status(root, page, required_before_live=True) for page in LIVE_REQUIRED_PAGES]
    support_pages = [_page_status(root, page, required_before_live=False) for page in SUPPORT_PAGES]

    blockers: list[str] = []
    for page in live_pages:
        if not page["present"]:
            blockers.append(f"{page['slug']}_page_missing")
        elif page["counsel_required"] and not page["counsel_review_approved"]:
            blockers.append(f"{page['slug']}_counsel_review_missing")

    homepage_links = {}
    for slug, candidates in HOMEPAGE_REQUIRED_LINKS.items():
        present = _has_any_link(hrefs, candidates)
        homepage_links[slug] = {
            "present": present,
            "accepted_routes": list(candidates),
        }
        if not present:
            blockers.append(f"{slug}_homepage_link_missing")

    forbidden_hits = []
    for name, pattern in FORBIDDEN_LEGAL_STATUS_PATTERNS.items():
        for match in pattern.finditer(homepage):
            forbidden_hits.append({"name": name, "match": match.group(0)})
            blockers.append(f"homepage_forbidden_legal_status_{name}")

    blockers = sorted(set(blockers))

    return {
        "schema_version": "duesight.legal_launch_surface.verify.v1",
        "mode": "verify",
        "will_change_system": False,
        "root": str(root),
        "homepage": {
            "path": str(index_path),
            "exists": index_path.exists(),
            "required_links": homepage_links,
            "forbidden_legal_status_hits": forbidden_hits,
        },
        "live_required_pages": live_pages,
        "support_pages": support_pages,
        "blockers": blockers,
        "ready_for_live_payments": not blockers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify DueSight legal launch surface without changing files.")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(build_report(args.root), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
