from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = ROOT / "docs"
if not (DOCS_ROOT / "CLAIMS_SUBSTANTIATION_MATRIX.md").exists():
    DOCS_ROOT = ROOT.parent / "duesight-agent" / "docs"
if not (DOCS_ROOT / "CLAIMS_SUBSTANTIATION_MATRIX.md").exists():
    DOCS_ROOT = ROOT.parent / "docs_patch"


def read_homepage() -> str:
    return (ROOT / "index.html").read_text(encoding="utf-8", errors="ignore")


def test_homepage_does_not_use_unsubstantiated_certification_language():
    html = read_homepage()
    lower_html = html.lower()

    blocked_phrases = [
        "strict zero-retention",
        "eu ai act conform",
        "nis2-conform",
        "nis2-compliant",
        "gdpr-conform",
        "avg-conform",
        "eu ai act ready",
        "eu ai act conform",
        "certificationstatus",
        "certificationactive",
        '"@type": "certification"',
        "99.97%",
        "synced</span>",
    ]

    for phrase in blocked_phrases:
        assert phrase not in lower_html


def test_homepage_uses_allowed_claim_status_language():
    html = read_homepage()

    assert '"@type": "SoftwareApplication"' in html
    assert '"@type": "FAQPage"' in html
    assert "AVG-documentatie" in html
    assert "AI Act-transparantie" in html
    assert 'href="privacy/"' in html
    assert 'href="assurance/"' in html
    assert 'href="dpa/"' in html
    assert "SOC 2-roadmap" not in html
    assert "ISO 27001-aligned" not in html


def test_claims_matrix_is_registered_as_active_source_of_truth():
    matrix = DOCS_ROOT / "CLAIMS_SUBSTANTIATION_MATRIX.md"
    index = DOCS_ROOT / "DOC_INDEX.md"

    matrix_text = matrix.read_text(encoding="utf-8", errors="ignore")
    index_text = index.read_text(encoding="utf-8", errors="ignore")

    assert "DueSight Claims Substantiation Matrix" in matrix_text
    assert "Hard Public Wording Rules" in matrix_text
    for status in [
        "CERTIFIED",
        "SELF_ASSESSED",
        "ALIGNED",
        "ROADMAP",
        "DEMO_SYNTHETIC",
        "REMOVE_UNTIL_EVIDENCE",
    ]:
        assert status in matrix_text
    for claim_id in [f"C-{number:03d}" for number in range(1, 13)]:
        assert claim_id in matrix_text

    assert "CLAIMS_SUBSTANTIATION_MATRIX.md" in index_text
