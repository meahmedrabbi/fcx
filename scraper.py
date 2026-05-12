"""
scraper.py – main async scraper for https://quotes.toscrape.com

Run:
    python scraper.py

Output:
    quotes.json  (configurable via config.OUTPUT_FILE)
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from playwright.async_api import async_playwright, Page

from config import (
    TARGET_URL,
    MAX_PAGES,
    OUTPUT_FILE,
)
from stealth_utils import (
    new_stealth_context,
    new_stealth_page,
    human_delay,
    human_scroll,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

async def parse_quotes_from_page(page: Page) -> list[dict]:
    """Extract all quotes visible on the current page."""
    quotes = []
    quote_elements = await page.query_selector_all(".quote")
    for el in quote_elements:
        text_el = await el.query_selector(".text")
        author_el = await el.query_selector(".author")
        tag_els = await el.query_selector_all(".tag")

        text = (await text_el.inner_text()).strip() if text_el else ""
        author = (await author_el.inner_text()).strip() if author_el else ""
        tags = [
            (await t.inner_text()).strip() for t in tag_els
        ]
        quotes.append({"text": text, "author": author, "tags": tags})
    return quotes


async def get_next_page_url(page: Page) -> str | None:
    """Return the absolute URL of the next page, or None if last page."""
    next_btn = await page.query_selector("li.next > a")
    if not next_btn:
        return None
    href = await next_btn.get_attribute("href")
    if not href:
        return None
    # href is relative, e.g. /page/2/
    base = TARGET_URL.rstrip("/")
    return f"{base}{href}"


# ---------------------------------------------------------------------------
# Core scraping logic
# ---------------------------------------------------------------------------

async def scrape_page(browser, url: str) -> tuple[list[dict], str | None]:
    """
    Open a stealth context+page, navigate to *url*, scrape quotes,
    then return (quotes, next_url).
    """
    context = await new_stealth_context(browser)
    page = await new_stealth_page(context)

    try:
        log.info("Navigating → %s", url)
        response = await page.goto(url, wait_until="domcontentloaded", timeout=30_000)

        # Log the direct HTTP response
        if response:
            body = await response.body()
            log.info(
                "Response | url=%s status=%d %s headers=%s body_bytes=%d\n%s",
                response.url,
                response.status,
                response.status_text,
                dict(response.headers),
                len(body),
                body.decode("utf-8", errors="replace"),
            )
        else:
            log.warning("No response received for %s", url)

        # Let the page settle and simulate human reading behaviour
        await human_delay(1.0, 2.5)
        await human_scroll(page, steps=random.randint(2, 5))
        await human_delay(0.5, 1.5)

        quotes = await parse_quotes_from_page(page)
        next_url = await get_next_page_url(page)
        log.info("  ↳ scraped %d quotes | next=%s", len(quotes), next_url)
        return quotes, next_url

    finally:
        await context.close()


async def run_scraper() -> None:
    all_quotes: list[dict] = []
    current_url: str | None = TARGET_URL
    page_count = 0

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )

        try:
            while current_url:
                if MAX_PAGES and page_count >= MAX_PAGES:
                    log.info("Reached MAX_PAGES=%d, stopping.", MAX_PAGES)
                    break

                quotes, next_url = await scrape_page(browser, current_url)
                all_quotes.extend(quotes)
                page_count += 1
                current_url = next_url

                # Polite inter-page delay
                if current_url:
                    await human_delay()

        finally:
            await browser.close()

    # Persist results
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(all_quotes, fh, ensure_ascii=False, indent=2)

    log.info(
        "Done – scraped %d quotes across %d pages → %s",
        len(all_quotes),
        page_count,
        OUTPUT_FILE,
    )


if __name__ == "__main__":
    asyncio.run(run_scraper())
