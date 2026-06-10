from __future__ import annotations

import argparse
import fnmatch
import html
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]

EXCLUDED_DIR_NAMES = {
    ".agent",
    ".browser-smoke",
    ".browser-smoke2",
    ".browser-smoke3",
    ".chrome-headless-profile",
    ".chrome-headless-profile-smoke",
    ".chrome-headless-profile-smoke-http",
    ".chromeprofile-smoke",
    ".claude",
    ".edge-headless-profile",
    ".edgeprofile-smoke",
    ".git",
    ".github",
    ".pytest_cache",
    ".session-logs",
    "_audit_screenshots",
    "_audit_temp",
    "_chromium_profile_codex2",
    "_edge_profile_codex2",
    "_pages",
    "__pycache__",
    "app",
    "archive",
    "backtesting",
    "backups",
    "claude_playground",
    "company",
    "context",
    "data",
    "designs",
    "docs",
    "functions",
    "frontend",
    "node_modules",
    "output",
    "reports",
    "renders",
    "smoke-reports",
    "test-results",
    "tests",
    "tmp",
    "tools",
    "website_src",
}

EXCLUDED_DIR_GLOBS = (
    "_codex*",
    "_tmp*",
    "pytest-cache-files-*",
    "sample-hub-*",
    "sample-report-*",
)

EXCLUDED_FILE_GLOBS = (
    ".env*",
    ".gitattributes",
    ".gitignore",
    ".gitmodules",
    ".tmp*",
    "*.bak*",
    "*.backup*",
    "*.backup*.html",
    "*.bat",
    "*.csv",
    "*.db",
    "*.json",
    "*.log",
    "*.md",
    "*.pdf",
    "*.ps1",
    "*.py",
    "*.pyc",
    "*.sqlite",
    "*.tmp",
    "*.xlsx",
    "index_*.html",
    "index_backup*.html",
    "index_github.html",
    "index_gisteravond.html",
    "index_master_backup.html",
    "*_backup*.html",
    "_*.txt",
    "chrome-*.txt",
    "codex_*",
    "CONTEXT.*",
    "gasunie_structure.txt",
    "harvest_v2_results.txt",
    "requirements.txt",
    "scratch_analysis.txt",
    "sizes*.txt",
    "test_results.txt",
)

SCAN_SUFFIXES = {".css", ".html", ".js", ".json", ".txt", ".xml"}
LEGACY_SCAN_SUFFIXES = {".css", ".html", ".js", ".xml"}
UTF8_BOM = b"\xef\xbb\xbf"

SAMPLE_REPORT_DIR_GLOB = "sample-report-*"
CURATED_SAMPLE_REPORT_FILES = {
    "flipbook.html",
    "hub.html",
    "index-premium.html",
    "index.html",
    "styles.css",
}

LEGACY_AUDIT_DIR_NAMES = (
    "backtesting",
    "designs",
)

LEGACY_AUDIT_DIR_GLOBS = (
    "sample-report-*",
)

LEGACY_AUDIT_FILE_GLOBS = (
    "index_*.html",
    "index_github.html",
    "index_gisteravond.html",
    "index_master_backup.html",
    "*backup*.html",
)

LEGACY_KNOWN_EXCLUDED_PATHS = {
    # Tiny legacy redirect stubs with UTF-8 BOM; left in place by archive policy.
    "index_2edcc66a.html",
    "index_2faf5765.html",
    "index_4b8a92b4.html",
    "index_aed8a4a9.html",
    "index_c75afd89.html",
    "index_gisteravond.html",
    "index_github.html",
    # Untracked exact archive target skipped by policy; see archive/legacy_zone_2026-06-08/MANIFEST.md.
    "backtesting/reports/20260526_Mollie.html",
}

FORBIDDEN_PATTERNS = {
    "legacy 100/100 score": re.compile(r"100/100", re.I),
    "legacy 105/110 score": re.compile(r"105/110", re.I),
    "invalid 105/100 score": re.compile(r"105/100", re.I),
    "PwC comparison token": re.compile(r"\bPwC\b", re.I),
    "KPMG comparison token": re.compile(r"\bKPMG\b", re.I),
    "ISO 27001 claim token": re.compile(r"ISO\s*27001", re.I),
    "SOC 2 claim token": re.compile(r"SOC\s*2", re.I),
    "Big 4 comparison token": re.compile(r"Big\s*4|Big\s*Four", re.I),
    "DueSight Score token": re.compile(r"DueSight\s+Score", re.I),
    "provider/model disclosure token": re.compile(r"(?<![\w-])(?:OpenAI|Anthropic|Claude(?:\s+(?:Opus|Sonnet))?|Google\s+Gemini|Gemini(?:\s+(?:Pro|Flash|[0-9][\w.\-\s]*))?|GPT[-\s]?(?:4o|4|5)|DeepSeek(?:\s+R1)?|Llama(?:\s+3(?:\.1)?)?|Mistral|Qwen|Grok|Ollama|Cerebras|SambaNova|FinBERT|GLM[-\s]?\d*|MiniCPM(?:[-]?[A-Za-z][\w]*)?|Hugging\s*Face|LiteLLM)(?![\w-])", re.I),
    "engine-count claim token": re.compile(r"\b(?:[2-9]|1[0-9])[-\s]?(?:independent\s+|speciali[sz]ed\s+|specialistische\s+)?(?:AI[-\s]?)?(?:engines?|modellen|models?)\b|\b(?:[2-9]|1[0-9])[-\s]?engine\s+cross[-\s]?check\b|\bengine[-\s]?count\b", re.I),
    "multi-provider consensus claim token": re.compile(r"\bMulti[-\s]?Provider\s+AI\s+Consensus\b|\bmulti[-\s]?engine\s+consensus\b|\bAI\s+Consensus\s+Protocol\b|\bAI[-\s]?ensemble\b", re.I),
    "Shodan/InternetDB featureclaim token": re.compile(r"\b(?:Shodan|InternetDB)\b", re.I),
    "Benford product-claim token": re.compile(r"\bBenford(?:'|&#x27;|&rsquo;|\u2019)?s?\b|\bBenfords\b", re.I),
    "GDPR/AVG compliance-status token": re.compile(r"\b(?:GDPR|AVG)[-\s]?(?:compliant|conform|ready)\b|\b(?:GDPR|AVG)\s+(?:Compliant|Conform|Ready)\b", re.I),
    "EU AI Act compliance-status token": re.compile(r"\bEU\s+AI\s+Act[-\s]?(?:compliant|conform|ready)\b", re.I),
    "clean verdict badge text": re.compile(r">\s*(?:ALL\s+)?CLEAR\b[^<]*<|\b(?:ALL\s+)?CLEAR\s*(?:\u2014|-)|Breach\s+Exposure\s+Status\s*:\s*CLEAR", re.I),
    "breach exposure score token": re.compile(r"Breach\s+Exposure\s+Score", re.I),
    "clean breach scan token": re.compile(r"\bclean\s+breach\s+scan\b|Een\s+clean\s+breach\s+scan", re.I),
    "absolute anonymity guarantee token": re.compile(r"absolute\s+anonimiteit\s+is\s+gegarandeerd", re.I),
    "full ownership chain token": re.compile(r"volledige\s+eigendomsketens", re.I),
    "AI confidence score token": re.compile(r"\b(?:AI|DueSight)\s+Confidence\s+(?:Score|Index)\b|\bConfidence\s+Score\b", re.I),
    "AI visibility score token": re.compile(r"\bAI\s+Visibility\s+Score\b", re.I),
    "Get There entity drift token": re.compile(r"\bGet\s*There\s+B\.V\.|\bGetThere\s+Group\b", re.I),
    "DueSight old legal entity token": re.compile(r"\bDueSight\s+B\.V\.", re.I),
    "DueSight old KvK token": re.compile(r"\b94847392\b"),
    "DueSight old VAT token": re.compile(r"\bNL866219241B01\b", re.I),
    "placeholder INVULLEN token": re.compile(r"\[INVULLEN\]", re.I),
    "Vibe The Code wrong entity token": re.compile(r"\bVibe\s+The\s+Code\s+B\.V\.", re.I),
    "public sample score-framing token": re.compile(r"\b(?:Pipeline|Evidence)\s+score\b|\bmet\s+score,|\bHow\s+score\s+improves\b|\bScore\s+model\b|sample_report_score_model|scoremodel", re.I),
    "public uppercase score-verdict token": re.compile(r">\s*SCORE\b|\bSCORE\s*<strong|\bSCORE\s+\d"),
    "compliance grade token": re.compile(r"\bCompliance\s+Grade\b", re.I),
    "buy verdict token": re.compile(r">\s*BUY(?:\s*[\u2014-][^<]*)?\s*<|Consensus\s*:\s*BUY|\bBUY\s*/\s*HOLD\s*/\s*ABSTAIN\b|\bBUY\s*,\s*HOLD\s+of\s+ABSTAIN\b", re.I),
    "favorable outcome sample token": re.compile(r"\bGOLD\s+TIER\b|\bGOLD\s+Report\b|\bAI\s+VERDICT\b|VERDICT\s*:\s*<strong>\s*INVEST\b|\bINVEST\s*(?:\u00b7|</|<|\u2014|-)|\b5[-\s]?Engine\s+Unanimous\s+Consensus\b|\bstrong\s+investment\s+profile\b", re.I),
    "system certainty framing token": re.compile(r"zeker\s+het\s+systeem", re.I),
    "fixed engine-count cross-check token": re.compile(r"\b6[-\s]?engine\s+cross[-\s]?check\b", re.I),
    "legacy 64 plus sources token": re.compile(r"\b64\+?\s*(?:databronnen|bronnen|sources)\b", re.I),
    "Benford forensics token": re.compile(r"Benford(?:'|&rsquo;|\u2019)?s?\s+Law\s+(?:forensics|forensiek)", re.I),
    "hit-rate token": re.compile(r"Hit\s+Rate", re.I),
    "institutional grade token": re.compile(r"Institutioneel\s+Grade", re.I),
    "absolute certainty token": re.compile(r"100%\s+zekerheid", re.I),
    "absolute Wwft token": re.compile(r"100%\s+Wwft", re.I),
    "unbeatable token": re.compile(r"\bunbeatable\b", re.I),
    "browser save marker": re.compile(r"saved from url|data-lt-installed|suppresshydrationwarning", re.I),
    "browser saved resource": re.compile(r"saved_resource|script\s+src=[\"']/index\.html", re.I),
    "raw tracker script": re.compile(r"sc\.lfeeder\.com|lftracker|ldfdr|dealfront tracker", re.I),
    "certification schema token": re.compile(r'"@type"\s*:\s*"Certification"|certificationStatus', re.I),
    "certification framing token": re.compile(r"\bCertified\s+(?:Replay|short memo|extended dossier|sample replay|evidence replay)\b|\bExecutive\s+certification\b|\bcertified\s+(?:sample replay|with limitations|evidence replay)\b|\bpipeline-certified\b|\brerun\s+certified\s+replay\b", re.I),
    # --- Gap-hardening (2026-06-09): residual claim patterns from PUBLIC_SURFACE_TRIAGE_20260608.md ---
    "legacy 64+ datapunten token": re.compile(r"\b64\+?\s*datapunten\b", re.I),
    "legacy 64+ publieke bronnen token": re.compile(r"\b64\+?\s*publieke\s+bronnen\b", re.I),
    "legacy 64+ public data sources token": re.compile(r"\b64\+?\s*public\s+data\s+sources\b", re.I),
    "legacy 64+ sources split-tag window token": re.compile(r"\b64\+[\s\S]{0,200}?\b(?:databronnen|bronnen|datapunten|data\s+sources)\b", re.I),
    "legacy 64+ sources split-tag window token (reverse)": re.compile(r"\b(?:databronnen|bronnen|datapunten|data\s+sources)[\s\S]{0,200}?\b64\+", re.I),
    "bare Multi-Provider token": re.compile(r"\bMulti[-\s]?Provider\b", re.I),
    "bare AI Consensus token": re.compile(r"\bAI\s+Consensus\b", re.I),
    "Multi-Provider Consensus token": re.compile(r"\bMulti[-\s]?Provider\s+Consensus\b", re.I),
    "multi-engine cross-check token (no number)": re.compile(r"\bmulti[-\s]?engine\s+cross[-\s]?check\b", re.I),
    "AI agenten fixed-count token": re.compile(r"\b\d+\s+AI[-\s]?agenten\b", re.I),
    # --- Blindspot hardening (2026-06-09): AI-engines, source-count, gate-count ---
    "AI-engines disclosure token": re.compile(r"\bAI[-\s]?engines?\b", re.I),
    "source-count bronnen token": re.compile(r"\b\d+\s*bronnen\b", re.I),
    "fixed-count databases token": re.compile(r"\b(?!47\s)\d+\s*databases\b", re.I),
    "gate-count claim token": re.compile(r"\b\d+\s*[-\s]?Gate\b", re.I),
    "consensus-stack claim token": re.compile(r"\bconsensus[-\s]?stack\b", re.I),
    "dual-model AI claim token": re.compile(r"\bdual[-\s]?model\s+AI\b", re.I),
}

PERFECT_PATTERN = re.compile(r"\bperfect\b", re.I)
PERFECT_ALLOWED_FRAGMENTS = (
    "perfect model",
    "cleanperfect",
)

SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    "aws key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "openai key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b"),
    "anthropic key": re.compile(r"\bsk-ant-[A-Za-z0-9_-]{24,}\b"),
    "github token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b"),
    "google api key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "mollie live key": re.compile(r"\blive_[A-Za-z0-9]{20,}\b"),
    "slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
}

URL_CONTEXT_ALLOWED_LABELS = {
    "Benford product-claim token",
    "Shodan/InternetDB featureclaim token",
}

URL_ATTR_PATTERN = re.compile(
    r"\b(href|src|action|content|url)\s*=\s*([\"'])(.*?)\2",
    re.I | re.S,
)
LOCAL_LINK_ATTR_PATTERN = re.compile(
    r"\b(href|src|action)\s*=\s*([\"'])(.*?)\2",
    re.I | re.S,
)
JSON_URL_FIELD_PATTERN = re.compile(
    r'"(?:url|item|@id)"\s*:\s*"([^"]*)"',
    re.I | re.S,
)
SKIPPED_LOCAL_LINK_SCHEMES = {"about", "http", "https", "mailto", "tel", "data", "javascript", "blob"}


def _match_is_in_span(match_start: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= match_start < end for start, end in spans)


def _looks_like_url_value(value: str) -> bool:
    value = value.strip().lower()
    return bool(value) and (
        value.startswith(("http://", "https://", "/", "./", "../", "#", "data:", "mailto:"))
        or ("/" in value and " " not in value)
        or value.endswith((".html", ".xml"))
    )


def _url_context_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for match in URL_ATTR_PATTERN.finditer(text):
        attr = match.group(1).lower()
        value = match.group(3)
        if attr != "content" or _looks_like_url_value(value):
            spans.append((match.start(3), match.end(3)))
    for match in JSON_URL_FIELD_PATTERN.finditer(text):
        spans.append((match.start(1), match.end(1)))
    for match in re.finditer(r"<loc>\s*([^<]*?)\s*</loc>", text, re.I | re.S):
        spans.append((match.start(1), match.end(1)))
    return spans


def _matches_any(name: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def _is_excluded_dir(path: Path) -> bool:
    return path.name in EXCLUDED_DIR_NAMES or _matches_any(path.name, EXCLUDED_DIR_GLOBS)


def _is_excluded_file(path: Path) -> bool:
    return _matches_any(path.name, EXCLUDED_FILE_GLOBS)


def _is_sample_report_dir_name(name: str) -> bool:
    return fnmatch.fnmatch(name, SAMPLE_REPORT_DIR_GLOB)


def _is_curated_sample_report_file(rel: Path) -> bool:
    return (
        len(rel.parts) == 2
        and _is_sample_report_dir_name(rel.parts[0])
        and rel.name in CURATED_SAMPLE_REPORT_FILES
    )


def _iter_build_files(source: Path):
    try:
        result = subprocess.run(
            ["git", "-C", str(source), "ls-files", "-z"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        result = None

    if result and result.returncode == 0 and result.stdout:
        for rel_name in result.stdout.split("\0"):
            if not rel_name:
                continue
            path = source / rel_name
            if path.is_file():
                yield path
        return

    for path in source.rglob("*"):
        if path.is_file():
            yield path


def build_public_artifact(source: Path, target: Path) -> None:
    source = source.resolve()
    target = target.resolve()
    if source == target:
        raise ValueError("--root cannot be the same directory as --build-from")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    for path in _iter_build_files(source):
        rel = path.relative_to(source)
        if rel.parts and rel.parts[0] == target.name:
            continue
        if rel.parts and _is_sample_report_dir_name(rel.parts[0]):
            if path.is_file() and _is_curated_sample_report_file(rel):
                dest = target / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
            continue
        if any(part in EXCLUDED_DIR_NAMES for part in rel.parts):
            continue
        if any(_matches_any(part, EXCLUDED_DIR_GLOBS) for part in rel.parts):
            continue
        if _is_excluded_file(path):
            continue
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)


def _iter_scan_files(root: Path, suffixes: set[str] | None = None):
    suffixes = SCAN_SUFFIXES if suffixes is None else suffixes
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in suffixes:
            continue
        if path.stat().st_size > 3_000_000:
            continue
        yield path


def _iter_legacy_scan_files(root: Path):
    seen: set[Path] = set()

    for name in LEGACY_AUDIT_DIR_NAMES:
        path = root / name
        if not path.exists():
            continue
        for candidate in _iter_scan_files(path, LEGACY_SCAN_SUFFIXES):
            resolved = candidate.resolve()
            if resolved not in seen:
                seen.add(resolved)
                yield candidate

    for pattern in LEGACY_AUDIT_DIR_GLOBS:
        for path in root.glob(pattern):
            if not path.is_dir():
                continue
            for candidate in _iter_scan_files(path, LEGACY_SCAN_SUFFIXES):
                resolved = candidate.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    yield candidate

    for pattern in LEGACY_AUDIT_FILE_GLOBS:
        for candidate in root.glob(pattern):
            if not candidate.is_file():
                continue
            if candidate.suffix.lower() not in SCAN_SUFFIXES:
                continue
            if candidate.stat().st_size > 3_000_000:
                continue
            resolved = candidate.resolve()
            if resolved not in seen:
                seen.add(resolved)
                yield candidate


def _scan_content_file(path: Path, rel: str, strict: bool) -> list[str]:
    findings: list[str] = []
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return [f"could not read {rel}: {exc}"]

    if raw.startswith(UTF8_BOM):
        findings.append(f"{rel}: UTF-8 BOM marker")

    text = raw.decode("utf-8", errors="ignore")
    url_context_spans = _url_context_spans(text)

    for label, pattern in FORBIDDEN_PATTERNS.items():
        for match in pattern.finditer(text):
            if label in URL_CONTEXT_ALLOWED_LABELS and _match_is_in_span(match.start(), url_context_spans):
                continue
            line_no = text.count("\n", 0, match.start()) + 1
            findings.append(f"{rel}:{line_no}: {label}: {match.group(0)}")

    for match in PERFECT_PATTERN.finditer(text):
        line_start = text.rfind("\n", 0, match.start()) + 1
        line_end = text.find("\n", match.end())
        if line_end == -1:
            line_end = len(text)
        line = text[line_start:line_end].lower()
        if any(fragment in line for fragment in PERFECT_ALLOWED_FRAGMENTS):
            continue
        line_no = text.count("\n", 0, match.start()) + 1
        findings.append(f"{rel}:{line_no}: perfect token: {match.group(0)}")

    if strict:
        for label, pattern in SECRET_PATTERNS.items():
            for match in pattern.finditer(text):
                line_no = text.count("\n", 0, match.start()) + 1
                findings.append(f"{rel}:{line_no}: possible secret ({label})")

    return findings


def _local_link_exists(root: Path, current_file: Path, raw_url: str) -> bool:
    raw_url = html.unescape(raw_url).strip()
    if not raw_url or raw_url.startswith("#"):
        return True

    parsed = urlsplit(raw_url)
    if parsed.scheme.lower() in SKIPPED_LOCAL_LINK_SCHEMES or parsed.netloc:
        return True
    if not parsed.path:
        return True

    rel_path = unquote(parsed.path).replace("\\", "/")
    if rel_path.startswith("/duesight-website/"):
        rel_path = rel_path[len("/duesight-website/") :]
    elif rel_path.startswith("/"):
        rel_path = rel_path.lstrip("/")

    base = root if parsed.path.startswith("/") else current_file.parent
    target = (base / rel_path).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError:
        return False

    if target.is_file():
        return True
    if target.is_dir() and (target / "index.html").is_file():
        return True
    if not Path(rel_path).suffix and (target / "index.html").is_file():
        return True
    return False


def _scan_local_links(root: Path, path: Path, rel: str) -> list[str]:
    if path.suffix.lower() not in {".html", ".htm"}:
        return []

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        return [f"could not read links in {rel}: {exc}"]

    findings: list[str] = []
    for match in LOCAL_LINK_ATTR_PATTERN.finditer(text):
        raw_url = match.group(3)
        if _local_link_exists(root, path, raw_url):
            continue
        if not _missing_link_points_to_filtered_artifact(root, path, raw_url):
            continue
        line_no = text.count("\n", 0, match.start()) + 1
        findings.append(f"{rel}:{line_no}: missing local link target: {raw_url}")
    return findings


def _missing_link_points_to_filtered_artifact(root: Path, current_file: Path, raw_url: str) -> bool:
    raw_url = html.unescape(raw_url).strip()
    if not raw_url or raw_url.startswith("#") or "+" in raw_url or "{" in raw_url:
        return False

    parsed = urlsplit(raw_url)
    if parsed.scheme.lower() in SKIPPED_LOCAL_LINK_SCHEMES or parsed.netloc or not parsed.path:
        return False

    rel_path = unquote(parsed.path).replace("\\", "/")
    if rel_path.startswith("/duesight-website/"):
        rel_path = rel_path[len("/duesight-website/") :]
    elif rel_path.startswith("/"):
        rel_path = rel_path.lstrip("/")

    base = root if parsed.path.startswith("/") else current_file.parent
    target = (base / rel_path).resolve()
    root_resolved = root.resolve()
    try:
        rel_target = target.relative_to(root_resolved)
    except ValueError:
        return False

    if target.exists():
        return False
    if rel_target.parts and _is_sample_report_dir_name(rel_target.parts[0]):
        return not _is_curated_sample_report_file(rel_target)
    if any(part in EXCLUDED_DIR_NAMES for part in rel_target.parts):
        return True
    if any(_matches_any(part, EXCLUDED_DIR_GLOBS) for part in rel_target.parts):
        return True
    return _is_excluded_file(rel_target)


def scan_public_surface(root: Path, strict: bool) -> list[str]:
    findings: list[str] = []

    if not root.exists():
        return [f"public root does not exist: {root}"]

    for path in root.rglob("*"):
        rel = path.relative_to(root).as_posix()
        rel_path = path.relative_to(root)
        if path.is_dir() and _is_sample_report_dir_name(path.name):
            continue
        if path.is_dir() and _is_excluded_dir(path):
            findings.append(f"denied directory present in artifact: {rel}/")
        if path.is_file() and rel_path.parts and _is_sample_report_dir_name(rel_path.parts[0]) and not _is_curated_sample_report_file(rel_path):
            findings.append(f"non-curated sample-report file present in artifact: {rel}")
        elif path.is_file() and _is_excluded_file(path):
            findings.append(f"denied file present in artifact: {rel}")

    for path in _iter_scan_files(root):
        rel = path.relative_to(root).as_posix()
        findings.extend(_scan_content_file(path, rel, strict))
        findings.extend(_scan_local_links(root, path, rel))

    return findings


def scan_legacy_surface(root: Path, strict: bool) -> list[str]:
    findings: list[str] = []

    if not root.exists():
        return [f"legacy root does not exist: {root}"]

    for path in _iter_legacy_scan_files(root):
        rel = path.relative_to(root).as_posix()
        if rel in LEGACY_KNOWN_EXCLUDED_PATHS:
            continue
        findings.extend(_scan_content_file(path, rel, strict))

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and scan the DueSight public Pages surface.")
    parser.add_argument("--root", default="_pages", help="Public artifact root to scan.")
    parser.add_argument("--build-from", help="Optional source directory to copy into --root before scanning.")
    parser.add_argument("--legacy", action="store_true", help="Scan excluded legacy zones before publishing them.")
    parser.add_argument("--strict", action="store_true", help="Enable secret scan and fail on every finding.")
    args = parser.parse_args()

    root_arg = "." if args.legacy and args.root == "_pages" else args.root
    root = (ROOT / root_arg).resolve() if not Path(root_arg).is_absolute() else Path(root_arg)
    if args.build_from:
        source = (ROOT / args.build_from).resolve() if not Path(args.build_from).is_absolute() else Path(args.build_from)
        build_public_artifact(source, root)

    findings = scan_legacy_surface(root, args.strict) if args.legacy else scan_public_surface(root, args.strict)
    if findings:
        label = "legacy surface audit" if args.legacy else "public surface gate"
        print(f"DueSight {label}: BLOCK")
        for finding in findings[:200]:
            print(f"- {finding}")
        if len(findings) > 200:
            print(f"- ... {len(findings) - 200} more finding(s)")
        return 1

    label = "legacy surface audit" if args.legacy else "public surface gate"
    print(f"DueSight {label}: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
