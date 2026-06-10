from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_contact_page_exposes_manual_intake_and_routing_channels() -> None:
    html = (ROOT / "contact.html").read_text(encoding="utf-8", errors="ignore")

    assert "Handmatige intake" in html
    assert "mailto:info@duesight.nl" in html
    assert "mailto:legal@duesight.nl" in html
    assert "mailto:privacy@duesight.nl" in html
    assert "mailto:security@duesight.nl" in html
    assert "Deel geen gevoelige dataroomdocumenten in de eerste mail" in html
    assert "Online checkout en live payment blijven afhankelijk van de launch gates" in html
    assert "Vibe The Code (KvK 99920301)" in html


def test_homepage_keeps_contact_paths_for_navigation_and_manual_fallback() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8", errors="ignore")

    assert '<a class="nav-link" href="contact.html">Contact</a>' in html
    assert '<a class="nav-cta" href="contact.html">' in html
    assert "Intake aanvragen" in html
    assert 'href="contact.html"><span class="material-symbols-outlined">mail</span>Plan intake</a>' in html
    assert 'href="contact.html"><span class="material-symbols-outlined">mail</span>Vraag gesprek aan</a>' in html
    assert "Checkout nog niet beschikbaar. Neem contact op voor handmatige intake." in html


def test_pricing_redirect_preserves_homepage_pricing_entrypoint() -> None:
    html = (ROOT / "pricing.html").read_text(encoding="utf-8", errors="ignore")

    assert 'content="0; url=index.html#pricing"' in html
    assert 'href="index.html#pricing"' in html


def test_partner_and_sales_surfaces_have_mail_fallbacks() -> None:
    partners = (ROOT / "partners.html").read_text(encoding="utf-8", errors="ignore")
    sales = (ROOT / "sales-tool.html").read_text(encoding="utf-8", errors="ignore")

    assert "mailto:partners@duesight.nl" in partners
    assert "Listing op aanvraag" in partners
    assert "mailto:info@duesight.nl" in sales
    assert "Betaallinks worden binnenkort geactiveerd" in sales
