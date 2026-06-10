from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tools import legal_launch_surface_check


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "legal_launch_surface_check.py"


def _write_launch_root(root: Path, *, approved: bool) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "index.html").write_text(
        '<a href="privacy/">Privacy</a><a href="dpa/">DPA</a><a href="assurance/">Trust</a>',
        encoding="utf-8",
    )
    marker = '<meta name="duesight-legal-review" content="approved">' if approved else ""
    for slug in ["terms", "refund", "cookies", "sla", "incident"]:
        page_dir = root / slug
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.html").write_text(
            f"<!doctype html><html><head>{marker}</head><body>{slug} draft</body></html>",
            encoding="utf-8",
        )


def test_legal_launch_surface_report_is_read_only_contract() -> None:
    report = legal_launch_surface_check.build_report(ROOT)

    assert report["schema_version"] == "duesight.legal_launch_surface.verify.v1"
    assert report["mode"] == "verify"
    assert report["will_change_system"] is False
    assert report["homepage"]["exists"] is True
    assert isinstance(report["blockers"], list)
    assert report["ready_for_live_payments"] is False


def test_legal_launch_surface_detects_existing_support_pages() -> None:
    report = legal_launch_surface_check.build_report(ROOT)
    support = {page["slug"]: page for page in report["support_pages"]}

    for slug in [
        "privacy",
        "dpa",
        "dataretentie",
        "assurance",
        "security",
        "ai-transparantie",
        "subprocessors",
    ]:
        assert support[slug]["present"] is True
        assert support[slug]["existing_paths"]


def test_legal_launch_surface_keeps_counsel_drafts_as_open_blockers() -> None:
    report = legal_launch_surface_check.build_report(ROOT)
    live_pages = {page["slug"]: page for page in report["live_required_pages"]}

    for slug in ["terms", "refund", "cookies", "sla", "incident"]:
        assert live_pages[slug]["required_before_live"] is True
        assert live_pages[slug]["counsel_required"] is True
        assert live_pages[slug]["counsel_review_approved"] is False
        assert live_pages[slug]["present"] is True
        assert live_pages[slug]["existing_paths"]
        assert f"{slug}_page_missing" not in report["blockers"]
        assert f"{slug}_counsel_review_missing" in report["blockers"]


def test_legal_launch_surface_rejects_unapproved_counsel_page_drafts(tmp_path: Path) -> None:
    _write_launch_root(tmp_path, approved=False)

    report = legal_launch_surface_check.build_report(tmp_path)

    for slug in ["terms", "refund", "cookies", "sla", "incident"]:
        assert f"{slug}_page_missing" not in report["blockers"]
        assert f"{slug}_counsel_review_missing" in report["blockers"]
    assert report["ready_for_live_payments"] is False


def test_legal_launch_surface_accepts_explicit_approved_counsel_marker(tmp_path: Path) -> None:
    _write_launch_root(tmp_path, approved=True)

    report = legal_launch_surface_check.build_report(tmp_path)
    live_pages = {page["slug"]: page for page in report["live_required_pages"]}

    for slug in ["terms", "refund", "cookies", "sla", "incident"]:
        assert live_pages[slug]["present"] is True
        assert live_pages[slug]["counsel_review_approved"] is True
        assert live_pages[slug]["counsel_review_evidence"]
        assert f"{slug}_counsel_review_missing" not in report["blockers"]
    assert report["ready_for_live_payments"] is True


def test_legal_launch_surface_homepage_links_existing_legal_docs_directly() -> None:
    report = legal_launch_surface_check.build_report(ROOT)
    links = report["homepage"]["required_links"]

    assert links["privacy"]["present"] is True
    assert links["dpa"]["present"] is True
    assert links["trust_security"]["present"] is True
    assert "privacy_homepage_link_missing" not in report["blockers"]
    assert "dpa_homepage_link_missing" not in report["blockers"]
    assert "trust_security_homepage_link_missing" not in report["blockers"]


def test_homepage_avoids_unreviewed_legal_status_claims() -> None:
    report = legal_launch_surface_check.build_report(ROOT)
    html = (ROOT / "index.html").read_text(encoding="utf-8", errors="ignore")

    assert report["homepage"]["forbidden_legal_status_hits"] == []
    assert "AVG-conform" not in html
    assert "EU AI Act ready" not in html
    assert ">SLA</a>" not in html


def test_counsel_drafts_are_noindex_until_approved() -> None:
    for slug in ["terms", "refund", "cookies", "sla", "incident"]:
        html = (ROOT / slug / "index.html").read_text(encoding="utf-8", errors="ignore")
        assert 'name="robots" content="noindex,nofollow"' in html
        assert "duesight-legal-review" not in html


def test_active_legal_surfaces_use_vibe_the_code_entity() -> None:
    pages = [
        ROOT / "privacy" / "index.html",
        ROOT / "dpa" / "index.html",
        ROOT / "dataretentie" / "index.html",
        ROOT / "assurance" / "index.html",
        ROOT / "security" / "index.html",
        ROOT / "ai-transparantie" / "index.html",
        ROOT / "subprocessors" / "index.html",
        ROOT / "terms" / "index.html",
        ROOT / "refund" / "index.html",
        ROOT / "cookies" / "index.html",
        ROOT / "sla" / "index.html",
        ROOT / "incident" / "index.html",
        ROOT / "insurance" / "index.html",
        ROOT / "trademarks" / "index.html",
    ]

    for path in pages:
        html = path.read_text(encoding="utf-8", errors="ignore")
        assert "Vibe The Code" in html, path
        assert "99920301" in html, path
        assert "DueSight B.V." not in html, path
        assert "94847392" not in html, path
        assert "NL866219241B01" not in html, path


def test_legal_launch_surface_cli_outputs_json() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "duesight.legal_launch_surface.verify.v1"
    assert payload["ready_for_live_payments"] is False
