from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _products() -> dict[str, dict[str, str]]:
    tree = ast.parse((ROOT / "payment_server.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "PRODUCTS":
            return ast.literal_eval(node.value)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "PRODUCTS":
                    return ast.literal_eval(node.value)
    raise AssertionError("PRODUCTS not found in payment_server.py")


def test_payment_products_cover_only_active_checkout_prices() -> None:
    products = _products()

    assert products["compact"]["amount"] == "79.00"
    assert products["predd"]["amount"] == "399.00"
    assert products["ma"]["amount"] == "399.00"
    assert products["monitoring"]["amount"] == "19.00"
    assert set(products) == {"compact", "predd", "ma", "monitoring"}


def test_sales_tool_volume_packs_are_offerte_not_stale_checkout_prices() -> None:
    html = (ROOT / "sales-tool.html").read_text(encoding="utf-8", errors="ignore")

    assert "€349" not in html
    assert "€649" not in html
    assert "Compact · 5+ credits" in html
    assert "Pre-DD · 3+ credits" in html
    assert "Op aanvraag" in html
    assert "Op aanvraag 5+ credits Compact" in html
    assert "Op aanvraag 3x Pre-DD" in html


def test_notaris_api_pricing_is_offerte_until_sku_exists() -> None:
    html = (ROOT / "notaris-api-docs.html").read_text(encoding="utf-8", errors="ignore")

    assert "€4,99" not in html
    assert "€4.99" not in html
    assert "per API call" not in html
    assert "Prijs:</strong> Op aanvraag" in html
    assert "Pricing op aanvraag" in html


def test_partner_listing_fee_is_offerte_until_sku_exists() -> None:
    html = (ROOT / "partners.html").read_text(encoding="utf-8", errors="ignore")

    assert "€200/maand" not in html
    assert "€200/mnd" not in html
    assert "Listing fee" not in html
    assert "Listing op aanvraag" in html
