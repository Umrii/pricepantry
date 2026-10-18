"""Tesco Groceries scraper (Playwright + BeautifulSoup).

Tesco protects its site with bot detection, so this scraper:
  * uses a realistic browser fingerprint (UA, locale, viewport, headers),
  * masks the obvious ``navigator.webdriver`` automation signal,
  * waits for the product grid and adds human-like jitter between requests,
  * parses defensively with several selector fallbacks + a price regex.

Selectors on Tesco change often; if a run returns zero products, the parsing
here is the first place to adjust. The rest of the pipeline (dedup, persistence)
is store-agnostic and lives in ``base.py`` / ``db.py``.
"""
from __future__ import annotations

import os
import random
import re
import time
from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

from base import AbstractScraper
from db import ScrapedProduct

SEARCH_URL = "https://www.tesco.com/groceries/en-GB/search?query={query}&page={page}"
PRODUCT_HREF_RE = re.compile(r"/products/(\d+)")
PRICE_RE = re.compile(r"£\s?(\d+(?:\.\d{1,2})?)")
UNIT_PRICE_RE = re.compile(r"£\s?\d+(?:\.\d{1,2})?\s*/\s*\w+")
# A tile node whose text is *only* a price, e.g. "£2.75". The real sell price
# usually sits in its own element, while promo/unit figures are embedded in
# longer text ("Any 2 for £4.00", "£1.38/litre").
LONE_PRICE_RE = re.compile(r"^£\s?\d+(?:\.\d{1,2})?$")
# A £ amount is a unit price when it is immediately FOLLOWED by "/unit" or "per".
_UNIT_AFTER_RE = re.compile(r"\s*(?:/|per\b)", re.IGNORECASE)
# Promotional / multi-buy wording that, when it PRECEDES a £ amount, marks that
# amount as not the product's own sell price (e.g. "Any 2 for £4", "Was £3",
# "Save £1", "3 for £5", Clubcard offers, "Spend £40 for free delivery").
_PROMO_CTX_RE = re.compile(
    r"(?:any\s*\d+|\d+\s*for\b|\bfor\s*£|\bsave\b|\bwas\b|clubcard|\boffer|"
    r"multi-?buy|mix\b|meal\s*deal|when\s+you\b|\bspend\b)",
    re.IGNORECASE,
)
# Container class names that denote a promotional price block.
_PROMO_CLASS_RE = re.compile(r"offer|promo|promotion|clubcard|multi-?buy", re.IGNORECASE)


def extract_price(text: str) -> Decimal | None:
    """Return a product's own sell price from a blob of tile/price text.

    Tesco tiles concatenate several monetary values — the sell price, a unit
    price ("£1.38/litre") and sometimes promotional / multi-buy amounts
    ("Any 2 for £4.00"). Taking the first "£" blindly (the original bug) could
    return a promo or unit figure instead of the real price.

    Scan amounts left to right and return the first that is neither a unit
    price (judged by the text right after it) nor introduced by a promotional
    phrase (judged by the text since the previous amount, so promo context does
    not bleed onto the following value). Used as the fallback when a dedicated
    price element cannot be isolated (see ``TescoScraper._extract_price``).
    """
    if not text:
        return None
    prev_end = 0
    for m in PRICE_RE.finditer(text):
        start, end = m.span()
        context = text[prev_end:start]
        prev_end = end
        if _UNIT_AFTER_RE.match(text[end:end + 8]):
            continue  # unit price, e.g. "£1.38/litre"
        if _PROMO_CTX_RE.search(context):
            continue  # promotional / multi-buy amount
        try:
            return Decimal(m.group(1))
        except InvalidOperation:
            continue
    return None

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# Search terms act as "categories" for Phase 1.
DEFAULT_CATEGORIES = [
    "milk",
    "bread",
    "eggs",
    "chicken",
    "cheese",
    "bananas",
    "coffee",
    "rice",
]

# A hint map: search term -> tidy category label stored on the product.
CATEGORY_LABELS = {
    "milk": "Milk",
    "bread": "Bread",
    "eggs": "Eggs",
    "chicken": "Poultry",
    "cheese": "Cheese",
    "bananas": "Fresh Fruit",
    "coffee": "Coffee",
    "rice": "Rice & Grains",
}

_STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['en-GB', 'en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
window.chrome = { runtime: {} };
"""


class TescoScraper(AbstractScraper):
    slug = "tesco"
    store_name = "Tesco"
    website_url = "https://www.tesco.com/groceries/"

    def __init__(self, max_pages: int = 2, headless: bool = True,
                 categories: list[str] | None = None) -> None:
        self.max_pages = max_pages
        self.headless = headless
        self.categories = categories or DEFAULT_CATEGORIES
        self._page = None  # set inside run()

    # ---- AbstractScraper interface ------------------------------------- #
    def scrape_categories(self) -> list[str]:
        return self.categories

    def scrape_price(self, raw: dict) -> Decimal | None:
        # AbstractScraper interface: parse a price from raw text, skipping unit
        # and promotional amounts.
        return extract_price(raw.get("price_text", ""))

    def scrape_products(self, category: str) -> list[ScrapedProduct]:
        assert self._page is not None, "scrape_products must run inside run()"
        products: list[ScrapedProduct] = []
        label = CATEGORY_LABELS.get(category, category.title())

        for page_num in range(1, self.max_pages + 1):
            url = SEARCH_URL.format(query=category, page=page_num)
            html = self._fetch(url)
            if not html:
                break
            page_products = self._parse(html, label)
            if not page_products:
                # No results (blocked, or reached the end) — stop paging.
                break
            products.extend(page_products)
            time.sleep(random.uniform(1.5, 3.5))  # be polite

        print(f"[tesco] '{category}': {len(products)} products")
        return products

    # ---- internals ----------------------------------------------------- #
    def _fetch(self, url: str) -> str | None:
        page = self._page
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except PWTimeout:
            print(f"[tesco] timeout loading {url}")
            return None

        # Best-effort cookie accept (privacy-preserving: only 'accept all' if present
        # is required to view the grid; we do not set marketing preferences).
        for selector in ('button#onetrust-accept-btn-handler',
                         'button[aria-label*="Accept"]'):
            try:
                btn = page.query_selector(selector)
                if btn:
                    btn.click(timeout=2000)
                    time.sleep(1)
                    break
            except Exception:
                pass

        # Wait for the product grid to appear.
        for selector in ('li.product-list--list-item',
                         '[data-testid="product-tile"]',
                         'div.product-list',
                         'a[href*="/products/"]'):
            try:
                page.wait_for_selector(selector, timeout=8000)
                break
            except PWTimeout:
                continue

        return page.content()

    def _parse(self, html: str, category_label: str) -> list[ScrapedProduct]:
        soup = BeautifulSoup(html, "html.parser")

        tiles = (
            soup.select("li.product-list--list-item")
            or soup.select('[data-testid="product-tile"]')
        )
        if not tiles:
            # Fallback: group by anchor to a product page.
            tiles = [a.find_parent("li") or a for a in soup.select('a[href*="/products/"]')]

        results: list[ScrapedProduct] = []
        seen: set[str] = set()
        for tile in tiles:
            link = tile.select_one('a[href*="/products/"]')
            if not link or not link.get("href"):
                continue
            href = link["href"]
            m = PRODUCT_HREF_RE.search(href)
            if not m:
                continue
            external_id = m.group(1)
            if external_id in seen:
                continue
            seen.add(external_id)

            url = href if href.startswith("http") else f"https://www.tesco.com{href}"
            name = self._extract_name(tile, link)
            if not name:
                continue

            tile_text = tile.get_text(" ", strip=True)
            price = self._extract_price(tile)
            unit_match = UNIT_PRICE_RE.search(tile_text)
            img = tile.select_one("img")
            image_url = img.get("src") or img.get("data-src") if img else None

            results.append(
                ScrapedProduct(
                    name=name,
                    url=url,
                    price=price,
                    brand=self._guess_brand(name),
                    weight=self._extract_weight(name),
                    category=category_label,
                    image_url=image_url,
                    external_id=external_id,
                    unit_price=unit_match.group(0) if unit_match else None,
                )
            )
        return results

    def _extract_price(self, tile) -> Decimal | None:
        """Extract the product's own sell price from a search-result tile.

        Prefer a dedicated element that contains *only* a price (a node whose
        text is exactly "£2.75") and is not inside a promotional block; this
        sidesteps multi-buy / Clubcard / unit figures elsewhere in the tile
        (the root cause of the £4.00-vs-£2.75 discrepancy). Fall back to a
        promo/unit-aware scan of the whole tile text when no such node exists.
        """
        for el in tile.find_all(True):
            text = el.get_text(" ", strip=True)
            if not LONE_PRICE_RE.match(text):
                continue
            if self._in_promo_context(el, tile):
                continue
            amount = extract_price(text)
            if amount is not None:
                return amount
        return extract_price(tile.get_text(" ", strip=True))

    @staticmethod
    def _in_promo_context(el, tile) -> bool:
        """True if ``el`` sits inside a promotional / multi-buy price block.

        Judged by (a) a promo-ish class on any ancestor up to the tile, and
        (b) a promo phrase in the price's *immediate sub-container* — but never
        the tile root itself, whose text always includes the promo banner.
        """
        node = el
        for _ in range(5):
            if node is None or not hasattr(node, "get"):
                break
            classes = " ".join(node.get("class", []) or [])
            if classes and _PROMO_CLASS_RE.search(classes):
                return True
            if node is tile:
                break
            node = node.parent
        parent = el.parent
        if parent is not None and parent is not tile and hasattr(parent, "get_text"):
            if _PROMO_CTX_RE.search(parent.get_text(" ", strip=True)):
                return True
        return False

    @staticmethod
    def _extract_name(tile, link) -> str | None:
        for sel in ('a[href*="/products/"] span', 'h3', 'h2',
                    '[data-testid="product-tile--title"]'):
            el = tile.select_one(sel)
            if el and el.get_text(strip=True):
                return el.get_text(strip=True)
        text = link.get_text(strip=True)
        return text or None

    @staticmethod
    def _extract_weight(name: str) -> str | None:
        m = re.search(r"(\d+(?:\.\d+)?\s?(?:kg|g|ml|l|litre|cl|pack|x\s?\d+))",
                      name, re.IGNORECASE)
        return m.group(1) if m else None

    @staticmethod
    def _guess_brand(name: str) -> str | None:
        # Naive: first token(s). Tesco own-brand starts with "Tesco".
        if name.lower().startswith("tesco"):
            return "Tesco"
        return name.split(" ")[0] if name else None

    def _warmup(self, page) -> None:
        """Prime Akamai's ``_abck`` sensor cookie on the homepage.

        Akamai serves 403 on protected paths until its JS challenge has run and
        POSTed valid sensor data. Loading the homepage first (with a little
        human-like movement) lets that happen, and the resulting cookies carry
        over to the search requests in the same context.
        """
        try:
            page.goto("https://www.tesco.com/", wait_until="domcontentloaded",
                      timeout=45000)
        except PWTimeout:
            print("[tesco] warmup: homepage load timed out")
            return

        # Accept cookies if the banner is shown.
        for selector in ('button#onetrust-accept-btn-handler',
                         'button[aria-label*="Accept"]'):
            try:
                btn = page.query_selector(selector)
                if btn:
                    btn.click(timeout=2000)
                    break
            except Exception:
                pass

        # Akamai's ``_abck`` starts as "~-1~" (unvalidated) and only flips to a
        # validated token once its sensor script has POSTed enough behavioural
        # data. Keep interacting (mouse + scroll) and poll the cookie until it
        # validates or we give up.
        def abck_value() -> str | None:
            c = next((c for c in page.context.cookies() if c["name"] == "_abck"), None)
            return c["value"] if c else None

        validated = False
        deadline = 22  # seconds of best-effort warm-up
        for i in range(deadline):
            page.mouse.move(random.randint(80, 1250), random.randint(80, 820))
            if i % 3 == 0:
                try:
                    page.mouse.wheel(0, random.randint(300, 900))
                except Exception:
                    pass
            page.wait_for_timeout(random.randint(700, 1100))
            val = abck_value()
            if val and "~-1~" not in val:
                validated = True
                break

        # Visit the groceries landing page in-session to further legitimise the
        # Akamai session before requesting the protected search endpoint.
        try:
            page.goto("https://www.tesco.com/groceries/en-GB/",
                      wait_until="domcontentloaded", timeout=45000)
            page.mouse.move(random.randint(200, 1000), random.randint(200, 700))
            page.wait_for_timeout(random.randint(2000, 3500))
            val = abck_value()
            validated = validated or bool(val and "~-1~" not in val)
        except PWTimeout:
            pass

        if abck_value() is None:
            print("[tesco] warmup: no _abck cookie set")
        else:
            print(f"[tesco] warmup: _abck "
                  f"{'VALIDATED' if validated else 'still unvalidated'}")

    def run(self) -> list[ScrapedProduct]:
        # Optionally drive the user's real Chrome (channel) via a persistent
        # profile — a genuine Chrome fingerprint can validate Akamai's sensor
        # where bundled Chromium fails. Configure with PW_CHANNEL=chrome and
        # (optionally) PW_USER_DATA_DIR=/path/to/profile.
        channel = os.environ.get("PW_CHANNEL") or None
        user_data_dir = os.environ.get("PW_USER_DATA_DIR")
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
        ]
        with sync_playwright() as p:
            if user_data_dir:
                context = p.chromium.launch_persistent_context(
                    user_data_dir,
                    channel=channel,
                    headless=self.headless,
                    args=launch_args,
                    user_agent=USER_AGENT,
                    locale="en-GB",
                    timezone_id="Europe/London",
                    viewport={"width": 1366, "height": 900},
                    extra_http_headers={"Accept-Language": "en-GB,en;q=0.9"},
                )
                browser = None
            else:
                browser = p.chromium.launch(
                    channel=channel, headless=self.headless, args=launch_args
                )
                context = browser.new_context(
                    user_agent=USER_AGENT,
                    locale="en-GB",
                    timezone_id="Europe/London",
                    viewport={"width": 1366, "height": 900},
                    extra_http_headers={"Accept-Language": "en-GB,en;q=0.9"},
                )
            context.add_init_script(_STEALTH_JS)
            self._page = context.pages[0] if context.pages else context.new_page()
            try:
                self._warmup(self._page)
                return super().run()
            finally:
                context.close()
                if browser is not None:
                    browser.close()
                self._page = None
