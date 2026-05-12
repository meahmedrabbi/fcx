"""
stealth_utils.py – browser launch helpers and fingerprint-evasion patches.

Techniques applied
------------------
1. playwright-stealth  – patches navigator, webdriver flag, plugins, languages,
                         WebGL renderer strings, and more via JS overrides.
2. Randomised viewport  – each page gets a different screen resolution.
3. Randomised User-Agent – rotated from a curated real-browser list via
                          fake-useragent (falls back to a static pool).
4. Timezone / locale    – set to a common US locale to match UA strings.
5. Human-like mouse     – random scroll & micro-movements before extracting data.
6. Random delays        – sleep between actions to break timing fingerprints.
"""

from __future__ import annotations

import asyncio
import random
from playwright.async_api import Browser, BrowserContext, Page
from playwright_stealth import stealth_async

try:
    from fake_useragent import UserAgent
    _ua = UserAgent(browsers=["chrome", "firefox", "edge"])
    def _get_ua() -> str:
        return _ua.random
except Exception:
    _FALLBACK_UAS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
        "Gecko/20100101 Firefox/125.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    ]
    def _get_ua() -> str:
        return random.choice(_FALLBACK_UAS)


from config import VIEWPORTS, DELAY_MIN, DELAY_MAX


async def new_stealth_context(browser: Browser) -> BrowserContext:    """Create a new browser context with stealth settings."""
    viewport = random.choice(VIEWPORTS)
    user_agent = _get_ua()

    context = await browser.new_context(
        viewport=viewport,
        user_agent=user_agent,
        locale="en-US",
        timezone_id="America/New_York",
        # Emulate a common colour depth / device scale
        color_scheme="light",
        device_scale_factor=random.choice([1, 1.25, 1.5, 2]),
        # Accept typical browser headers
        extra_http_headers={
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
            "DNT": "1",
        },
    )
    return context


async def new_stealth_page(context: BrowserContext) -> Page:
    """Open a new page and apply playwright-stealth patches."""
    page = await context.new_page()
    await stealth_async(page)
    return page


async def human_delay(min_s: float = DELAY_MIN, max_s: float = DELAY_MAX) -> None:
    """Sleep for a random duration to mimic human think-time."""
    await asyncio.sleep(random.uniform(min_s, max_s))


async def human_scroll(page: Page, steps: int = 3) -> None:
    """Scroll the page gradually, simulating a human reading."""
    for _ in range(steps):
        delta = random.randint(200, 600)
        await page.mouse.wheel(0, delta)
        await asyncio.sleep(random.uniform(0.3, 0.9))
