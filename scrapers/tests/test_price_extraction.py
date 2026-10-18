"""Regression tests for Tesco price extraction — no network, no database.

Covers the confirmed real-world discrepancy where a multi-buy promotional
amount ("Any 2 for £4.00") was stored instead of the product's own sell price
(£2.75), plus promotional, unit, unrelated-currency and missing/invalid inputs.

These are deterministic: they parse static HTML / strings, never live Tesco.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from tesco.scraper import TescoScraper, extract_price


# --------------------------------------------------------------------------- #
# extract_price() — pure text-level behaviour
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "text, expected",
    [
        # Sell price stated first, multi-buy after.
        ("£2.75 £1.38/litre Any 2 for £4.00", Decimal("2.75")),
        # Multi-buy stated FIRST — must NOT be taken as the price (the bug).
        ("Any 2 for £4.00 £2.75", Decimal("2.75")),
        # Was/now promotion.
        ("Was £3.00 Now £2.00", Decimal("2.00")),
        # "N for £X" multi-buy before the real price.
        ("3 for £5.00 £1.90", Decimal("1.90")),
        # Save promotion.
        ("Save £1.00 £2.50", Decimal("2.50")),
    ],
)
def test_extract_price_skips_promotions(text, expected):
    assert extract_price(text) == expected


@pytest.mark.parametrize("text", ["£1.38/litre", "£0.25/each", "£4.00/kg"])
def test_extract_price_ignores_unit_only(text):
    # A unit price on its own is not the sell price.
    assert extract_price(text) is None


def test_extract_price_skips_unit_before_real_price():
    assert extract_price("£4.00/kg £3.60") == Decimal("3.60")


def test_extract_price_ignores_unrelated_currency():
    # A "spend £40 for free delivery" style threshold is not the price.
    assert extract_price("Spend £40 for free delivery £2.75") == Decimal("2.75")


@pytest.mark.parametrize(
    "text",
    ["", "   ", "Price unavailable", "Out of stock", "£", "no price here"],
)
def test_extract_price_missing_or_invalid(text):
    assert extract_price(text) is None


# --------------------------------------------------------------------------- #
# TescoScraper._parse() — HTML-level regression (element targeting)
# --------------------------------------------------------------------------- #
# The real Arla tile: a multi-buy banner, the product link, and a price block
# holding the sell price and the unit price.
ARLA_TILE_HTML = """
<ul>
  <li class="product-list--list-item">
    <div class="product-promotion offer">
      <span>Any 2 for £4.00 Clubcard Price</span>
    </div>
    <a href="/shop/en-GB/products/287971983">
      <span>Arla Big Milk Fresh Whole Milk 2L Vitamin Enriched for kids 1+</span>
    </a>
    <img src="https://digitalcontent.api.tesco.com/arla.jpg" />
    <div class="price">
      <p>£2.75</p>
      <p>£1.38/litre</p>
    </div>
  </li>
</ul>
"""


def _parse_one(html: str):
    scraper = TescoScraper()  # constructor does not launch a browser
    products = scraper._parse(html, "Milk")
    assert len(products) == 1
    return products[0]


def test_parse_arla_uses_sell_price_not_multibuy():
    p = _parse_one(ARLA_TILE_HTML)
    assert p.external_id == "287971983"
    assert p.price == Decimal("2.75")          # NOT the £4.00 multi-buy
    assert p.unit_price == "£1.38/litre"
    assert p.name.startswith("Arla Big Milk")


def test_parse_multibuy_lone_node_is_excluded():
    # Promo amount rendered as its own node inside an offer block must be
    # ignored in favour of the real price.
    html = """
    <ul><li class="product-list--list-item">
      <a href="/shop/en-GB/products/287971983"><span>Arla Big Milk 2L</span></a>
      <div class="offer"><span>£4.00</span><span>Any 2</span></div>
      <p class="value">£2.75</p>
    </li></ul>
    """
    assert _parse_one(html).price == Decimal("2.75")


def test_parse_normal_product_unaffected():
    html = """
    <ul><li class="product-list--list-item">
      <a href="/shop/en-GB/products/254656543"><span>Tesco Semi Skimmed Milk 2.272L</span></a>
      <p>£1.75</p><p>£0.77/litre</p>
    </li></ul>
    """
    p = _parse_one(html)
    assert p.price == Decimal("1.75")
    assert p.unit_price == "£0.77/litre"


def test_parse_missing_price_yields_none():
    html = """
    <ul><li class="product-list--list-item">
      <a href="/shop/en-GB/products/999999"><span>Mystery Item</span></a>
      <p>Price unavailable</p>
    </li></ul>
    """
    assert _parse_one(html).price is None
