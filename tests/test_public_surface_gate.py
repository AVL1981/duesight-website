import subprocess
from pathlib import Path

from tools import public_surface_gate


def test_public_surface_gate_blocks_claim_audit_regressions(tmp_path):
    page = tmp_path / "index.html"
    page.write_text(
        """
        <span>GDPR Compliant</span>
        <span class="badge-clear">CLEAR</span>
        <p>AI Confidence Score: 98</p>
        <p>volledige eigendomsketens</p>
        <p>Google Gemini API and Claude Opus review</p>
        <p>Multi-Provider AI Consensus across 5 independent AI engines</p>
        <p>Shodan InternetDB exposure scan</p>
        <p>Benford's Law Forensics</p>
        <p>AVG-conform and EU AI Act ready</p>
        <footer>DueSight B.V. · KvK: 94847392 · BTW: NL866219241B01</footer>
        """,
        encoding="utf-8",
    )

    findings = public_surface_gate.scan_public_surface(tmp_path, strict=True)

    assert any("GDPR/AVG compliance-status token" in finding for finding in findings)
    assert any("EU AI Act compliance-status token" in finding for finding in findings)
    assert any("provider/model disclosure token" in finding for finding in findings)
    assert any("multi-provider consensus claim token" in finding for finding in findings)
    assert any("engine-count claim token" in finding for finding in findings)
    assert any("Shodan/InternetDB featureclaim token" in finding for finding in findings)
    assert any("Benford product-claim token" in finding for finding in findings)
    assert any("clean verdict badge text" in finding for finding in findings)
    assert any("AI confidence score token" in finding for finding in findings)
    assert any("full ownership chain token" in finding for finding in findings)
    assert any("DueSight old legal entity token" in finding for finding in findings)
    assert any("DueSight old KvK token" in finding for finding in findings)
    assert any("DueSight old VAT token" in finding for finding in findings)


def test_public_surface_gate_allows_only_curated_sample_report_files(tmp_path):
    sample = tmp_path / "sample-report-nlist"
    sample.mkdir()
    (sample / "index-premium.html").write_text("<h1>Sample</h1>", encoding="utf-8")
    (sample / "pipeline-evidence.json").write_text("{}", encoding="utf-8")

    findings = public_surface_gate.scan_public_surface(tmp_path, strict=True)

    assert any("non-curated sample-report file present" in finding for finding in findings)
    assert not any("index-premium.html" in finding for finding in findings)


def test_public_artifact_build_curates_linked_sample_reports(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "public"
    sample = source / "sample-report-nlist"
    sample.mkdir(parents=True)
    (source / "index.html").write_text(
        '<a href="/sample-report-nlist/index-premium.html">sample</a>',
        encoding="utf-8",
    )
    for name in ["flipbook.html", "hub.html", "index.html", "index-premium.html", "styles.css"]:
        (sample / name).write_text("ok", encoding="utf-8")
    (sample / "pipeline-evidence.json").write_text("{}", encoding="utf-8")
    (sample / "company-intel-prompt-evaluation.json").write_text("{}", encoding="utf-8")

    public_surface_gate.build_public_artifact(source, target)

    assert (target / "index.html").exists()
    assert (target / "sample-report-nlist" / "index-premium.html").exists()
    assert (target / "sample-report-nlist" / "flipbook.html").exists()
    assert not (target / "sample-report-nlist" / "pipeline-evidence.json").exists()
    assert not (target / "sample-report-nlist" / "company-intel-prompt-evaluation.json").exists()
    assert public_surface_gate.scan_public_surface(target, strict=True) == []


def test_public_artifact_build_uses_only_git_tracked_files(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "public"
    source.mkdir()
    subprocess.run(["git", "-C", str(source), "init"], check=True, capture_output=True)

    (source / "index.html").write_text("<h1>Tracked</h1>", encoding="utf-8")
    (source / "orbit-duesight.html").write_text("<h1>Untracked experiment</h1>", encoding="utf-8")
    subprocess.run(["git", "-C", str(source), "add", "index.html"], check=True, capture_output=True)

    public_surface_gate.build_public_artifact(source, target)

    assert (target / "index.html").exists()
    assert not (target / "orbit-duesight.html").exists()


def test_public_artifact_build_from_tracked_source_is_clean(tmp_path):
    source = Path(public_surface_gate.__file__).resolve().parents[1]
    target = tmp_path / "public"

    public_surface_gate.build_public_artifact(source, target)

    assert public_surface_gate.scan_public_surface(target, strict=True) == []


def test_public_surface_gate_blocks_residual_claim_gaps(tmp_path):
    """Triage-driven gap-hardening: the old gate passed while these specific
    patterns leaked into customer-visible HTML. They must all block now."""
    page = tmp_path / "index.html"
    page.write_text(
        """
        <div class="stat-item"><div class="stat-num">64+</div><div class="stat-label">Databronnen</div></div>
        <div class="stat-item"><div class="stat-num">64+</div><div class="stat-label">Data Sources</div></div>
        <p>64+ publieke bronnen</p>
        <p>64+ datapunten</p>
        <p>This report uses 64+ public data sources for cross-validation.</p>
        <p>Multi-Provider AI Consensus across multiple engines</p>
        <p>Multi-Provider Consensus with adversarial review</p>
        <p>DueSight uses bare Multi-Provider architecture</p>
        <p>The AI Consensus dashboard aggregates signals</p>
        <p>multi-engine cross-check validates bevindingen</p>
        <p>DueSight automatiseert due diligence met 38 AI-agenten</p>
        <p>13-Engine cascade review</p>
        <p>5-engine consensus</p>
        """,
        encoding="utf-8",
    )

    findings = public_surface_gate.scan_public_surface(tmp_path, strict=False)
    joined = "\n".join(findings)

    assert "split-tag window token" in joined
    assert "datapunten token" in joined
    assert "publieke bronnen token" in joined
    assert "public data sources token" in joined
    assert "Multi-Provider Consensus token" in joined
    assert "bare Multi-Provider token" in joined
    assert "bare AI Consensus token" in joined
    assert "multi-engine cross-check token" in joined
    assert "AI agenten fixed-count token" in joined
    assert "engine-count claim token" in joined


def test_public_surface_gate_allows_safe_replacement_language(tmp_path):
    """Safe replacement language must NOT be flagged by the hardened gate."""
    page = tmp_path / "index.html"
    page.write_text(
        """
        <p>meerdere databronnen</p>
        <p>bronherleidbare publieke bronnen</p>
        <p>multi-source evidence review</p>
        <p>proprietary multi-model intelligence engine</p>
        <p>passive infrastructure exposure analysis</p>
        <p>documented security controls</p>
        <p>47 databases</p>
        <p>meerdere analyselagen</p>
        """,
        encoding="utf-8",
    )

    findings = public_surface_gate.scan_public_surface(tmp_path, strict=False)

    assert findings == [], f"safe replacement language must not be flagged, got: {findings}"


def test_public_surface_gate_split_tag_window_catches_html_breaks():
    """Direct unit test: the split-tag window regex must match the canonical
    `<div>64+</div><div>Databronnen</div>` form, and not over-match common
    safe strings like '47 databases' or 'multi-source evidence review'."""
    split = "<div class=\"stat-item\"><div class=\"stat-num\">64+</div><div class=\"stat-label\">Databronnen</div></div>"
    safe_1 = "We integrate 47 databases for cross-validation"
    safe_2 = "multi-source evidence review across the public web"
    safe_3 = "meerdere publieke bronnen, geen 64+ claim"

    pattern = public_surface_gate.FORBIDDEN_PATTERNS["legacy 64+ sources split-tag window token"]
    assert pattern.search(split) is not None
    assert pattern.search(safe_1) is None
    assert pattern.search(safe_2) is None
    assert pattern.search(safe_3) is None


def test_public_surface_gate_split_tag_window_catches_reverse_order():
    """Reverse-order split-tag: e.g. `<td>Databronnen</td>...<strong>64+</strong>`
    where the noun appears before the number (common in comparison tables)."""
    reverse = '<tr><td class="feature-name">Databronnen</td><td class="highlight"><strong>64+</strong></td><td>15-20</td></tr>'
    safe = "The Databronnen field is left empty for the audit. 65 other entries follow."

    pattern = public_surface_gate.FORBIDDEN_PATTERNS["legacy 64+ sources split-tag window token (reverse)"]
    assert pattern.search(reverse) is not None
    assert pattern.search(safe) is None


# --- Blindspot hardening tests (2026-06-09) ---


def test_public_surface_gate_blocks_new_provider_leaks(tmp_path):
    """Newly added provider names (MiniCPM, HuggingFace, LiteLLM) must be caught."""
    page = tmp_path / "index.html"
    page.write_text(
        """
        <p>Powered by MiniCPM for document analysis</p>
        <p>HuggingFace model hub integration</p>
        <p>Routed via LiteLLM proxy</p>
        <p>Hugging Face transformers pipeline</p>
        """,
        encoding="utf-8",
    )

    findings = public_surface_gate.scan_public_surface(tmp_path, strict=False)
    joined = "\n".join(findings)

    assert "provider/model disclosure token" in joined
    # Must catch at least 4 distinct matches (MiniCPM, HuggingFace, LiteLLM, Hugging Face)
    provider_hits = [f for f in findings if "provider/model disclosure token" in f]
    assert len(provider_hits) >= 4, f"Expected 4+ provider hits, got {len(provider_hits)}: {provider_hits}"


def test_public_surface_gate_blocks_ai_engines_disclosure(tmp_path):
    """AI-engines / AI engine / AI-engines must be caught as disclosure."""
    page = tmp_path / "index.html"
    page.write_text(
        """
        <p>meerdere AI-engines werken parallel</p>
        <p>multiple AI engines analyze independently</p>
        <p>onafhankelijke AI-engine analyseert</p>
        """,
        encoding="utf-8",
    )

    findings = public_surface_gate.scan_public_surface(tmp_path, strict=False)
    joined = "\n".join(findings)

    assert "AI-engines disclosure token" in joined


def test_public_surface_gate_blocks_source_count_bronnen(tmp_path):
    """Fixed source-count claims like '27 bronnen', '24 bronnen' must be caught."""
    page = tmp_path / "index.html"
    page.write_text(
        """
        <p>146 bronclaims uit 27 bronnen met timestamp</p>
        <p>132 bronclaims uit 24 bronnen, met 6 signalen</p>
        <p>geanalyseerd uit 15 bronnen</p>
        """,
        encoding="utf-8",
    )

    findings = public_surface_gate.scan_public_surface(tmp_path, strict=False)
    joined = "\n".join(findings)

    assert "source-count bronnen token" in joined
    bronnen_hits = [f for f in findings if "source-count bronnen token" in f]
    assert len(bronnen_hits) >= 3, f"Expected 3+ bronnen hits, got {len(bronnen_hits)}"


def test_public_surface_gate_blocks_fixed_count_databases(tmp_path):
    """Fixed database counts like '8 databases' must be caught, but '47 databases' allowed."""
    page = tmp_path / "index.html"
    page.write_text(
        """
        <p>Sanctiescreening (8 databases)</p>
        <p>we integrate 15 databases</p>
        <p>64 databases automatically</p>
        """,
        encoding="utf-8",
    )

    findings = public_surface_gate.scan_public_surface(tmp_path, strict=False)
    joined = "\n".join(findings)

    assert "fixed-count databases token" in joined
    db_hits = [f for f in findings if "fixed-count databases token" in f]
    assert len(db_hits) >= 3, f"Expected 3+ databases hits, got {len(db_hits)}"


def test_public_surface_gate_allows_47_databases(tmp_path):
    """'47 databases' must NOT be caught by the databases token."""
    page = tmp_path / "index.html"
    page.write_text(
        """
        <p>We integrate 47 databases for cross-validation</p>
        <p>47 databases wereldwijd</p>
        """,
        encoding="utf-8",
    )

    findings = public_surface_gate.scan_public_surface(tmp_path, strict=False)
    db_hits = [f for f in findings if "fixed-count databases token" in f]

    assert db_hits == [], f"'47 databases' must not be flagged, got: {db_hits}"


def test_public_surface_gate_blocks_gate_count_claims(tmp_path):
    """Fixed gate-count claims like '10-Gate' must be caught."""
    page = tmp_path / "index.html"
    page.write_text(
        """
        <p>10-Gate epistemisch systeem</p>
        <p>5-Gate validatie</p>
        <p>12 Gate review protocol</p>
        """,
        encoding="utf-8",
    )

    findings = public_surface_gate.scan_public_surface(tmp_path, strict=False)
    joined = "\n".join(findings)

    assert "gate-count claim token" in joined
    gate_hits = [f for f in findings if "gate-count claim token" in f]
    assert len(gate_hits) >= 3, f"Expected 3+ gate-count hits, got {len(gate_hits)}"


def test_public_surface_gate_blocks_consensus_stack(tmp_path):
    """'consensus-stack' must be caught."""
    page = tmp_path / "index.html"
    page.write_text(
        """
        <p>DueSight's consensus-stack bestaat uit meerdere lagen</p>
        <p>Our consensus stack ensures reliability</p>
        """,
        encoding="utf-8",
    )

    findings = public_surface_gate.scan_public_surface(tmp_path, strict=False)
    joined = "\n".join(findings)

    assert "consensus-stack claim token" in joined


def test_public_surface_gate_blocks_dual_model_ai(tmp_path):
    """'dual-model AI' must be caught."""
    page = tmp_path / "index.html"
    page.write_text(
        """
        <p>8 databases + dual-model AI</p>
        <p>dual model AI enhanced screening</p>
        """,
        encoding="utf-8",
    )

    findings = public_surface_gate.scan_public_surface(tmp_path, strict=False)
    joined = "\n".join(findings)

    assert "dual-model AI claim token" in joined


def test_public_surface_gate_hardened_safe_replacements_all(tmp_path):
    """All safe replacement language must pass the fully hardened gate."""
    page = tmp_path / "index.html"
    page.write_text(
        """
        <p>proprietary multi-model intelligence engine</p>
        <p>multi-source evidence review</p>
        <p>forensische data-analyse</p>
        <p>passive infrastructure exposure analysis</p>
        <p>documented security controls</p>
        <p>47 databases</p>
        <p>meerdere analyselagen</p>
        <p>meerdere sanctielijsten</p>
        <p>uitgebreide sanctiedekking</p>
        <p>Geautomatiseerde sanctiescreening</p>
        <p>public-source based pre-diligence</p>
        <p>bronherleidbare publieke bronnen</p>
        <p>meerdere databronnen</p>
        <p>meerdere bronnen</p>
        """,
        encoding="utf-8",
    )

    findings = public_surface_gate.scan_public_surface(tmp_path, strict=False)

    assert findings == [], f"safe replacement language must not be flagged, got: {findings}"


def test_public_surface_gate_allows_benford_shodan_only_in_url_contexts(tmp_path):
    """Legacy SEO slugs may remain in href/canonical/sitemap URL contexts."""
    page = tmp_path / "index.html"
    page.write_text(
        """
        <a href="../benfords-law/">forensische data-analyse</a>
        <a href="../blog/benfords-law-fraude-detectie/">Forensische Fraude Detectie</a>
        <link rel="canonical" href="https://example.test/glossary/shodan/">
        <script type="application/ld+json">
        {"item": "https://example.test/glossary/benfords-law/", "url": "https://example.test/glossary/shodan/"}
        </script>
        """,
        encoding="utf-8",
    )
    sitemap = tmp_path / "sitemap.xml"
    sitemap.write_text(
        "<urlset><url><loc>https://example.test/blog/benfords-law-fraude-detectie/</loc></url></urlset>",
        encoding="utf-8",
    )

    findings = public_surface_gate.scan_public_surface(tmp_path, strict=False)

    assert findings == [], f"URL-only slugs must not be flagged, got: {findings}"


def test_public_surface_gate_still_blocks_benford_shodan_visible_text(tmp_path):
    """The URL-context bypass must not allow public copy feature claims."""
    page = tmp_path / "index.html"
    page.write_text(
        """
        <a href="/safe/">Benford analysis</a>
        <p>Shodan scan included</p>
        """,
        encoding="utf-8",
    )

    findings = public_surface_gate.scan_public_surface(tmp_path, strict=False)
    joined = "\n".join(findings)

    assert "Benford product-claim token" in joined
    assert "Shodan/InternetDB featureclaim token" in joined


def test_public_surface_gate_blocks_url_terms_in_non_url_meta_content(tmp_path):
    """Meta descriptions are public copy, but og:url style content values are URL context."""
    page = tmp_path / "index.html"
    page.write_text(
        """
        <meta name="description" content="Shodan scan included">
        <meta property="og:url" content="https://example.test/glossary/shodan/">
        """,
        encoding="utf-8",
    )

    findings = public_surface_gate.scan_public_surface(tmp_path, strict=False)
    joined = "\n".join(findings)

    assert "Shodan/InternetDB featureclaim token" in joined
