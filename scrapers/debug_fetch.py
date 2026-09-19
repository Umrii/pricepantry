"""Diagnostic: navigate a Tesco search page and report what came back.

Run: docker compose run --rm scraper python debug_fetch.py
Helps distinguish a bot-block / challenge from a selector mismatch.
"""
from __future__ import annotations

import re

from playwright.sync_api import sync_playwright

from tesco.scraper import USER_AGENT, _STEALTH_JS

URL = "https://www.tesco.com/groceries/en-GB/search?query=milk&page=1"

SELECTORS = [
    "li.product-list--list-item",
    '[data-testid="product-tile"]',
    "div.product-list",
    'a[href*="/products/"]',
]


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, args=["--disable-blink-features=AutomationControlled"]
        )
        ctx = browser.new_context(
            user_agent=USER_AGENT,
            locale="en-GB",
            timezone_id="Europe/London",
            viewport={"width": 1366, "height": 900},
            extra_http_headers={"Accept-Language": "en-GB,en;q=0.9"},
        )
        ctx.add_init_script(_STEALTH_JS)
        page = ctx.new_page()

        # Warm up on the homepage so Akamai sets a (hopefully valid) _abck cookie.
        from tesco.scraper import TescoScraper
        TescoScraper(headless=True)._warmup(page)

        resp = page.goto(URL, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(4000)

        html = page.content()
        print(f"HTTP status : {resp.status if resp else 'n/a'}")
        print(f"Final URL   : {page.url}")
        print(f"Title       : {page.title()!r}")
        print(f"HTML length : {len(html)}")

        lowered = html.lower()
        for marker in ["access denied", "captcha", "are you a robot",
                       "unusual traffic", "px-captcha", "just a moment",
                       "enable javascript", "blocked"]:
            if marker in lowered:
                print(f"  !! found block marker: {marker!r}")

        for sel in SELECTORS:
            print(f"selector {sel!r}: {len(page.query_selector_all(sel))} matches")

        # Count product links.
        hrefs = re.findall(r'/products/(\d+)', html)
        print(f"'/products/<id>' hrefs in HTML: {len(hrefs)} (unique {len(set(hrefs))})")

        # Dump the first 800 chars of the body text for eyeballing.
        text = page.inner_text("body")[:800]
        print("---- body text preview ----")
        print(text)
        print("---- end ----")

        ctx.close()
        browser.close()


if __name__ == "__main__":
    main()
