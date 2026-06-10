from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_insurance_page_records_external_evidence_required_without_marker() -> None:
    html = (ROOT / "insurance" / "index.html").read_text(encoding="utf-8", errors="ignore")

    assert 'name="robots" content="noindex,nofollow"' in html
    assert "Verzekeringsbewijs" in html
    assert "in controle" in html
    assert "Extern bewijs vereist" in html
    assert "Afgesloten (Hiscox)" not in html
    assert "verzekerd voor beroeps- en bedrijfsaansprakelijkheid" not in html
    assert "duesight-insurance-evidence" not in html
    assert "data-insurance-evidence" not in html


def test_trademark_page_records_external_evidence_required_without_marker() -> None:
    html = (ROOT / "trademarks" / "index.html").read_text(encoding="utf-8", errors="ignore")

    assert 'name="robots" content="noindex,nofollow"' in html
    assert "Merk- en depotbewijs" in html
    assert "in controle" in html
    assert "Extern bewijs vereist" in html
    assert "Benelux-merkaanvraag gepubliceerd" not in html
    assert "i-DEPOT submitted" not in html
    assert "Payment reference:" not in html
    assert "duesight-boip-evidence" not in html
    assert "data-boip-evidence" not in html
