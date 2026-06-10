from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_SCAN_CLIENT = ROOT / "Institutional Investment Intelligence _ DueSight_files" / "scan_client.js.downloaden"


def test_homepage_exposes_production_api_bridge():
    html = (ROOT / "index.html").read_text(encoding="utf-8", errors="ignore")

    assert 'id="ds-production-api-bridge"' in html
    assert 'data-preview-endpoint="/api/teaser-scan?company_name="' in html
    assert 'data-payment-endpoint="/api/payment/create"' in html
    assert "/api/teaser-scan?company_name=" in html
    assert "/api/payment/create" in html
    assert "terms_accepted: true" in html
    assert "window.showIntentModal" in html
    assert "window.selectIntent" in html
    assert "localDefault(5050)" in html
    assert "localDefault(5051)" in html
    assert "window.location.hostname" in html
    assert "DueSight teaser preview unavailable; continuing to checkout." in html
    assert "apiBase = window.DUESIGHT_API_BASE || window.DUESIGHT_API_URL || serviceOrigin(5050)" not in html
    assert "paymentBase = window.DUESIGHT_PAYMENT_BASE || serviceOrigin(5051)" not in html


def test_homepage_customer_checkout_flow_supports_upload_and_return_status():
    html = (ROOT / "index.html").read_text(encoding="utf-8", errors="ignore")

    assert 'id="intentCompanyInput"' in html
    assert 'id="intentEmailInput"' in html
    assert 'id="intentKvkInput"' in html
    assert 'id="intentUploadFile"' in html
    assert 'id="intentTermsAccepted"' in html
    assert "uploadOrderFile(payload.order_id, customerEmail, uploadFile)" in html
    assert "'/api/payment/orders/' + encodeURIComponent(orderId) + '/uploads'" in html
    assert "orderStoragePrefix = 'duesight:payment-order:'" in html
    assert "params.get('payment') === 'success'" in html
    assert "E-mail voor status en upload" in html
    assert "'/api/payment/status/' + encodeURIComponent(orderId) + '?customer_email='" in html
    assert "window.prompt('E-mailadres voor rapportlevering')" not in html
    assert "window.confirm('Ik ga akkoord met de DueSight voorwaarden en privacyverklaring.')" not in html


def test_active_scan_client_uses_canonical_payment_flow():
    js = ACTIVE_SCAN_CLIENT.read_text(encoding="utf-8", errors="ignore")

    assert "window.DUESIGHT_API_BASE" in js
    assert "localDefault(5050)" in js
    assert "localDefault(5051)" in js
    assert "/api/teaser-scan?company_name=" in js
    assert "/api/payment/create" in js
    assert "/api/checkout?tier=" not in js
    assert "API_BASE = window.DUESIGHT_API_BASE || window.DUESIGHT_API_URL || serviceOrigin(5050)" not in js
    assert "PAYMENT_BASE = window.DUESIGHT_PAYMENT_BASE || serviceOrigin(5051)" not in js
    assert "'http://localhost:8000'" not in js
    assert "'http://localhost:5051'" not in js


def test_root_scan_client_sanitizes_dynamic_checkout_and_subsidy_content():
    js = (ROOT / "scan_client.js").read_text(encoding="utf-8", errors="ignore")

    assert "function escapeHTML" in js
    assert "const safeDomain = escapeHTML" in js
    assert "container.replaceChildren();" in js
    assert "btn.textContent = `Mislukt:" in js
    assert "terms_accepted: termsAccepted" in js
