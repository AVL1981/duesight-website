from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_insurance_page_records_hiscox_status_without_evidence_marker() -> None:
    html = (ROOT / "insurance" / "index.html").read_text(encoding="utf-8", errors="ignore")

    assert 'name="robots" content="noindex,nofollow"' in html
    assert "Verzekeringsbewijs" in html
    assert "Afgesloten (Hiscox)" in html
    assert "Publieke dekkingssamenvatting wordt pas gepubliceerd na controle" in html
    assert "duesight-insurance-evidence" not in html
    assert "data-insurance-evidence" not in html


def test_trademark_page_records_pending_status_without_registered_marker() -> None:
    html = (ROOT / "trademarks" / "index.html").read_text(encoding="utf-8", errors="ignore")

    assert 'name="robots" content="noindex,nofollow"' in html
    assert "Merkregistratie & i-DEPOT" in html
    assert "Registratie is nog pending" in html
    assert "payment references are retained internally" in html
    assert "Payment reference:" not in html
    assert "duesight-boip-evidence" not in html
    assert "data-boip-evidence" not in html
