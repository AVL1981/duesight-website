import re
from pathlib import Path

from tools import public_surface_gate


ROOT = Path(__file__).resolve().parents[1]
CURATED_FILES = {"flipbook.html", "hub.html", "index.html", "index-premium.html", "styles.css"}


def _sample_report_links(html: str) -> list[str]:
    return re.findall(r'href=["\']([^"\']*sample-report-[^"\']*)["\']', html)


def _resolve_sample_link(page: Path, href: str, artifact_root: Path) -> Path:
    href = href.split("#", 1)[0].split("?", 1)[0]
    if href.startswith("/"):
        path = artifact_root / href.lstrip("/")
    else:
        path = (page.parent / href).resolve()
    if path.is_dir() or href.endswith("/"):
        path = path / "index.html"
    return path


def test_built_public_pages_sample_report_links_resolve_to_curated_files(tmp_path):
    artifact = tmp_path / "_pages"
    public_surface_gate.build_public_artifact(ROOT, artifact)
    pages = [
        artifact / "index.html",
        artifact / "rapporten" / "index.html",
        artifact / "whitelabel-demo.html",
    ]

    checked = []
    for page in pages:
        html = page.read_text(encoding="utf-8", errors="ignore")
        for href in _sample_report_links(html):
            target = _resolve_sample_link(page, href, artifact)
            checked.append(target)
            assert target.exists(), f"{page.relative_to(artifact)} links missing sample artifact: {href}"
            assert target.parent.name.startswith("sample-report-")
            assert target.name in CURATED_FILES

    assert checked
