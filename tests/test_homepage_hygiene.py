from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _existing(paths: list[Path]) -> list[Path]:
    return [path for path in paths if path.exists()]


def _public_homepage_surfaces() -> list[Path]:
    surfaces = [ROOT / "index.html", ROOT / "robots.txt"]
    surfaces.extend([ROOT / "_pages" / "index.html", ROOT / "_pages" / "changelog.html"])
    surfaces.extend(
        path
        for path in ROOT.glob("index*.html")
        if "backup" not in path.name.lower() and ".bak" not in path.name.lower()
    )
    surfaces.append(ROOT / "duesight_improved.html")
    surfaces.append(ROOT / "designs" / "des-14.html")
    surfaces.append(ROOT / "changelog.html")
    return sorted({path for path in surfaces if path.exists()})


def test_homepage_is_indexable_for_production():
    html = (ROOT / "index.html").read_text(encoding="utf-8", errors="ignore")

    assert '<link rel="canonical" href="https://duesight.nl">' in html
    assert '<meta property="og:url" content="https://duesight.nl">' in html
    assert '<meta name="robots" content="noindex' not in html.lower()


def test_homepage_hides_preview_chrome_and_restores_brand_video():
    html = (ROOT / "index.html").read_text(encoding="utf-8", errors="ignore")

    assert 'window.DUESIGHT_BUILD = "20260522-pipeline-curated";' in html
    assert 'class="brand" href="index.html"' in html
    assert "sample-report-matrix" in html
    assert "Pipeline-curated samples" in html


def test_unreviewed_surfaces_are_disallowed_for_crawlers():
    robots = (ROOT / "robots.txt").read_text(encoding="utf-8", errors="ignore")

    assert "Disallow: /backups/" in robots
    assert "Disallow: /backtesting/" in robots
    assert "Disallow: /company/" in robots
    assert "Disallow: /designs/" in robots
    assert "Disallow: /docs/" in robots
    assert "Disallow: /reports/" in robots
    assert "Disallow: /sample-report-*/" in robots
    assert "Disallow: /website_src/" in robots


def test_homepage_does_not_ship_known_broken_legacy_scripts():
    html = (ROOT / "index.html").read_text(encoding="utf-8", errors="ignore")

    assert '<script src="/index.html"' not in html
    assert "saved_resource" not in html
    assert "window.DUESIGHT_API_//l0" not in html
    assert "\n            nchors = ['#privacy'" not in html
    assert "duesight_improved.html" not in html
    assert "localServiceOrigin(5050)" in html


def test_homepage_source_is_not_a_browser_save_artifact():
    html = (ROOT / "index.html").read_text(encoding="utf-8", errors="ignore")

    assert "saved from url" not in html.lower()
    assert "data-lt-installed" not in html
    assert "suppresshydrationwarning" not in html.lower()
    assert '<html lang="nl" data-theme="light">' in html


def test_homepage_has_one_h1_and_no_dead_primary_section_links():
    html = (ROOT / "index.html").read_text(encoding="utf-8", errors="ignore")
    lower_html = html.lower()

    assert lower_html.count("<h1") == 1
    assert "pre-due diligence" in lower_html
    assert "buyer review" in lower_html

    for section_id in ["workflow", "evidence", "samples", "rapporten", "security", "pricing"]:
        assert f'id="{section_id}"' in html
    assert 'section#final-cta[style*="gradient"]' not in html
    assert 'href="#autopilot-demo"' not in html


def test_newly_visible_forensic_section_uses_demo_safe_claim_language():
    html = (ROOT / "index.html").read_text(encoding="utf-8", errors="ignore")

    assert "Precisie: <strong>99.7%</strong>" not in html
    assert "0 false positives" not in html
    assert "<strong>142 datapunten</strong>" not in html
    assert "<strong>KvK, CBS, Apollo</strong> en 8+ bronnen" not in html
    assert "Illustratief, uitsluitend op basis van publieke bronnen" in html
    assert "geen externe certificering" in html
    assert "geen perfecte-scoreclaim" in html


def test_homepage_does_not_load_b2b_tracker_without_consent():
    html = (ROOT / "index.html").read_text(encoding="utf-8", errors="ignore")
    lower_html = html.lower()

    assert "sc.lfeeder.com" not in lower_html
    assert "lftracker" not in lower_html
    assert "ldfdr" not in lower_html
    assert "dealfront tracker" not in lower_html
    assert "'unsafe-eval'" not in lower_html


def test_homepage_excludes_known_marketing_tabus():
    # Briefs BRIEF_HOMEPAGE_TABU_CLEANUP_20260608 and BRIEF_1b_ROOT_TABU_CLEANUP_20260608.
    surfaces = _public_homepage_surfaces()
    combined = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore").lower()
        for path in surfaces
    )
    html_combined = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore").lower()
        for path in surfaces
        if path.suffix.lower() == ".html"
    )

    assert "64+ institutionele bronnen" not in combined
    assert "64+ institutionele databronnen" not in combined
    assert "multi-engine consensus" not in combined
    assert "shodan" not in html_combined
    assert "ollama" not in html_combined
    assert "finbert" not in html_combined
    assert "qwen" not in html_combined
    assert "claude" not in html_combined
    assert "gemini" not in html_combined
    assert "ai confidence score" not in html_combined
    assert "6-engine" not in html_combined


def test_public_price_surfaces_match_checkout_products():
    surfaces = [
        ROOT / "index.html",
        ROOT / "_pages" / "index.html",
        ROOT / "roi-calculator.html",
        ROOT / "_pages" / "roi-calculator.html",
        ROOT / "intelligence-hub-template.html",
        ROOT / "_pages" / "intelligence-hub-template.html",
        ROOT / "scan_client.js",
        ROOT / "_pages" / "scan_client.js",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in _existing(surfaces))
    roi = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in _existing([ROOT / "roi-calculator.html", ROOT / "_pages" / "roi-calculator.html"])
    )
    index = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in _existing([ROOT / "index.html", ROOT / "_pages" / "index.html"])
    )

    for stale in [
        "\\u20ac49",
        "\\u20ac299",
        "&euro;299",
        "€299",
        "€599",
        "€2.999",
        '"price": "1499"',
        "&euro;1.499",
    ]:
        assert stale not in combined

    assert "\\u20ac79 per scan" in roi
    assert "\\u20ac399 per rapport" in roi
    assert '"price": "79"' in index
    assert '"price": "399"' in index
    assert "Op aanvraag" in index


def test_public_copy_allows_optional_uploads_and_retention_policy():
    surfaces = [
        ROOT / "index.html",
        ROOT / "_pages" / "index.html",
        ROOT / "trust.html",
        ROOT / "_pages" / "trust.html",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in _existing(surfaces))

    for absolute in [
        "Er is geen dataretentie",
        "er is geen dataretentie",
        "uitsluitend met publiek beschikbare brondata",
        "De enige input die wij ontvangen is een bedrijfsnaam of KvK-nummer",
        "Wij uploaden, ontvangen of verwerken geen documenten",
    ]:
        assert absolute not in combined

    assert "privacy- en retentiebeleid" in combined
    assert "optionele klantuploads" in combined


def test_legacy_root_index_variants_redirect_to_canonical_homepage():
    legacy_paths = list(ROOT.glob("index*.html"))
    legacy_paths.append(ROOT / "duesight_improved.html")
    for path in legacy_paths:
        if path.name == "index.html" or "backup" in path.name.lower() or "master" in path.name.lower():
            continue
        if not path.exists():
            continue
        html = path.read_text(encoding="utf-8", errors="ignore").lower()
        assert 'window.location.replace("index.html")' in html
        assert 'content="0; url=index.html"' in html
