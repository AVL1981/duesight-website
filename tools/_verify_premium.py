from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    from tools import public_surface_gate
except ImportError:  # pragma: no cover - direct execution from unusual cwd
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools import public_surface_gate


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_REPORT_COUNT = 12
REQUIRED_ENTRYPOINTS = ("index.html", "hub.html", "flipbook.html", "index-premium.html")
PREMIUM_MARKERS = (
    "Conservative:",
    "Normal:",
    "Optimistic:",
    "Not a score or outcome forecast.",
)
GETTHERE_REQUIRED = (
    "Get There ICT Solutions B.V.",
    "Get There ICT professionals",
    "02066288",
    "Trade name",
    "KvK",
)
GETTHERE_FORBIDDEN = (
    re.compile(r"\bGetThere\s+B\.V\.", re.I),
    re.compile(r"\bGet\s+There\s+B\.V\.", re.I),
    re.compile(r"\bGetthere\s+B\.V\.", re.I),
    re.compile(r"\bGetThere\s+Group\b", re.I),
)
SCENARIO_PERCENT_RE = re.compile(r"\b\d{1,3}-\d{1,3}%")
SCENARIO_PRICE_RE = re.compile(r"\bEUR\s+\d{2,4}-\d{2,4}\b")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _scan_forbidden(path: Path, root: Path) -> list[str]:
    text = _read(path)
    rel = path.relative_to(root).as_posix()
    findings: list[str] = []
    for label, pattern in public_surface_gate.FORBIDDEN_PATTERNS.items():
        if pattern.search(text):
            findings.append(f"{rel}: forbidden {label}")
    for label, pattern in public_surface_gate.SECRET_PATTERNS.items():
        if pattern.search(text):
            findings.append(f"{rel}: secret-like {label}")
    if public_surface_gate.PERFECT_PATTERN.search(text):
        lowered = text.lower()
        if not any(fragment in lowered for fragment in public_surface_gate.PERFECT_ALLOWED_FRAGMENTS):
            findings.append(f"{rel}: forbidden perfect token")
    return findings


def _verify_premium_page(report_dir: Path, root: Path) -> list[str]:
    premium = report_dir / "index-premium.html"
    rel = premium.relative_to(root).as_posix()
    text = _read(premium)
    findings: list[str] = []

    for marker in PREMIUM_MARKERS:
        if marker not in text:
            findings.append(f"{rel}: missing premium marker {marker!r}")
    if not SCENARIO_PERCENT_RE.search(text):
        findings.append(f"{rel}: missing scenario percent range")
    if not SCENARIO_PRICE_RE.search(text):
        findings.append(f"{rel}: missing scenario EUR price range")

    if report_dir.name == "sample-report-getthere":
        for marker in GETTHERE_REQUIRED:
            if marker not in text:
                findings.append(f"{rel}: missing Get There identity marker {marker!r}")
        for pattern in GETTHERE_FORBIDDEN:
            if pattern.search(text):
                findings.append(f"{rel}: forbidden Get There drift variant {pattern.pattern}")

    return findings


def verify(root: Path) -> list[str]:
    root = root.resolve()
    findings: list[str] = []
    report_dirs = sorted(path for path in root.glob("sample-report-*") if path.is_dir())

    if len(report_dirs) != EXPECTED_REPORT_COUNT:
        findings.append(f"expected {EXPECTED_REPORT_COUNT} sample-report dirs, found {len(report_dirs)}")

    for report_dir in report_dirs:
        for name in REQUIRED_ENTRYPOINTS:
            path = report_dir / name
            if not path.exists():
                findings.append(f"{report_dir.name}: missing {name}")
                continue
            findings.extend(_scan_forbidden(path, root))
        if (report_dir / "index-premium.html").exists():
            findings.extend(_verify_premium_page(report_dir, root))

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify DueSight premium sample-report integrity.")
    parser.add_argument("--root", type=Path, default=ROOT, help="Website repo root.")
    args = parser.parse_args()

    findings = verify(args.root)
    if findings:
        print("DueSight premium verifier: FAIL")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print(f"DueSight premium verifier: PASS ({EXPECTED_REPORT_COUNT}/{EXPECTED_REPORT_COUNT})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
