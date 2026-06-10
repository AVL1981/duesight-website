from __future__ import annotations

import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAN_SUFFIXES = {
    ".css",
    ".env.example",
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
EXCLUDED_DIRS = {
    ".git",
    "_codex_screenshots",
    "_codex_backups",
    "_audit_screenshots",
    "_audit_temp",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".session-logs",
    ".venv",
    "__pycache__",
    "archive",
    "backtesting",
    "backups",
    "node_modules",
    "output",
    "reports",
    "renders",
    "smoke-reports",
    "test-results",
}
EXCLUDED_DIR_PREFIXES = (
    ".browser-smoke",
    ".chrome-headless-profile",
    ".edge-headless-profile",
    "pytest-cache-files-",
)
SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "openai_key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b"),
    "anthropic_key": re.compile(r"\bsk-ant-[A-Za-z0-9_-]{24,}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b"),
    "google_api_key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "mollie_live_key": re.compile(r"\blive_[A-Za-z0-9]{20,}\b"),
    "mollie_test_key": re.compile(r"\btest_[A-Za-z0-9]{20,}\b"),
    "slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
}
ALLOWLIST_FRAGMENTS = {
    "test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "dev_replace_with_random_api_key",
    "dev_replace_with_random_admin_key",
    "<your-google-api-key>",
    "<your-smtp-password>",
    "<generate-a-random-32-char-string>",
}


def _iter_scan_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [
            name
            for name in dirnames
            if name not in EXCLUDED_DIRS
            and not any(name.startswith(prefix) for prefix in EXCLUDED_DIR_PREFIXES)
        ]
        base = Path(dirpath)
        if any(part in EXCLUDED_DIRS for part in base.parts):
            continue
        if any(
            part.startswith(prefix)
            for part in base.parts
            for prefix in EXCLUDED_DIR_PREFIXES
        ):
            continue
        for filename in filenames:
            path = base / filename
            if path.name == ".env":
                continue
            suffix = ".env.example" if path.name.endswith(".env.example") else path.suffix.lower()
            if suffix not in SCAN_SUFFIXES:
                continue
            if path.stat().st_size > 2_000_000:
                continue
            yield path


def test_no_high_confidence_secrets_in_deploy_surface():
    findings: list[str] = []

    for path in _iter_scan_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for label, pattern in SECRET_PATTERNS.items():
            for match in pattern.finditer(text):
                token = match.group(0)
                if any(fragment in token for fragment in ALLOWLIST_FRAGMENTS):
                    continue
                rel = path.relative_to(ROOT).as_posix()
                findings.append(f"{label} in {rel}")

    assert findings == []
