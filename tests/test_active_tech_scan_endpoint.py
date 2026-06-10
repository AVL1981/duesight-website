from pathlib import Path
from types import ModuleType, SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routers import scan


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(scan.router, prefix="/api")
    return TestClient(app)


def _install_fake_scanner(monkeypatch, scanner_cls):
    tools_module = ModuleType("tools")
    scanner_module = ModuleType("tools.active_code_scanner")
    scanner_module.ActiveCodeScanner = scanner_cls
    monkeypatch.setitem(__import__("sys").modules, "tools", tools_module)
    monkeypatch.setitem(__import__("sys").modules, "tools.active_code_scanner", scanner_module)
    monkeypatch.setattr(scan, "_ensure_agent_tools_import_path", lambda: Path("fake-tools"))


def test_active_tech_scan_rejects_non_github_urls():
    response = _client().get("/api/tech-scan-active?github_url=https://example.com/private/repo")

    assert response.status_code == 400
    assert "github.com/owner/repo" in response.json()["detail"]


def test_active_tech_scan_reports_no_tools_without_running_scan(monkeypatch):
    class NoToolsScanner:
        def available_tools(self):
            return {"trivy": False, "opengrep": False, "trufflehog": False, "osv-scanner": False}

    _install_fake_scanner(monkeypatch, NoToolsScanner)

    response = _client().get("/api/tech-scan-active?github_url=https://github.com/acme/example")

    assert response.status_code == 200
    assert response.json()["status"] == "no_tools"


def test_active_tech_scan_normalizes_finding_preview(monkeypatch):
    class FakeScanner:
        def available_tools(self):
            return {"trivy": True, "opengrep": False, "trufflehog": False, "osv-scanner": False}

        def scan_repo(self, github_url, target_label):
            assert github_url == "https://github.com/acme/example"
            assert target_label == "Acme"
            finding = SimpleNamespace(
                tool="trivy",
                severity="HIGH",
                title="Outdated package",
                cve_id="CVE-2026-0001",
                package="demo-lib",
                fixed_version="1.2.3",
                file_path="package-lock.json",
                is_secret=False,
                cvss_score=8.2,
            )
            return SimpleNamespace(
                errors=[],
                findings=[finding],
                tools_run=["trivy"],
                tools_skipped=["opengrep", "trufflehog", "osv-scanner"],
                risk_score=82,
            )

    _install_fake_scanner(monkeypatch, FakeScanner)

    response = _client().get(
        "/api/tech-scan-active?github_url=https://github.com/acme/example&company_name=Acme"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["findings_total"] == 1
    assert data["findings_preview"][0]["title"] == "Outdated package"
    assert data["risk_score"] == 82


def test_active_tech_scan_router_has_no_hardcoded_local_agent_path():
    source = (Path(__file__).resolve().parents[1] / "app/api/routers/scan.py").read_text(encoding="utf-8")

    assert "C:\\Users\\arian" not in source
    assert "DUESIGHT_AGENT_TOOLS_DIR" in source
