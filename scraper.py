"""
scraper.py – two-step scraper: open the base URL, then the target path,
             show summary info, and save the HTML.

Flow
----
1. Ask user to choose Desktop or Mobile browser simulation.
2. Open TARGET_URL          – establishes a session and picks up any cookies
                              set by the landing page, using realistic browser
                              headers for the chosen mode.
3. Human-like random delay  – breaks timing-based bot detection.
4. Open TARGET_URL/TARGET_PATH – follows through to the real target, carrying
                              session cookies and a Referer header.
5. Print a concise summary  – URL, status, title, description, size.
6. Save full HTML            – written to OUTPUT_FILE (default: scrapper.html).

Run:
    python scraper.py
"""

from __future__ import annotations

import random
import sys
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import (
    BROWSER_MODE,
    DELAY_MAX,
    DELAY_MIN,
    OUTPUT_FILE,
    PROXY_URL,
    REQUEST_TIMEOUT,
    TARGET_PATH,
    TARGET_URL,
)

# ── Browser profiles ──────────────────────────────────────────────────────────
# Each profile carries the User-Agent and optional Client Hint headers.
# Multiple profiles per mode so a random one is chosen on each run.

_DESKTOP_PROFILES: list[dict[str, str]] = [
    {
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-platform": '"Windows"',
    },
    {
        "user_agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-platform": '"macOS"',
    },
    {
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
            "Gecko/20100101 Firefox/125.0"
        ),
        "sec-ch-ua": "",
        "sec-ch-ua-platform": "",
    },
]

_MOBILE_PROFILES: list[dict[str, str]] = [
    {
        "user_agent": (
            "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.67 Mobile Safari/537.36"
        ),
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-platform": '"Android"',
    },
    {
        "user_agent": (
            "Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
        ),
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-platform": '"Android"',
    },
    {
        "user_agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1"
        ),
        "sec-ch-ua": "",
        "sec-ch-ua-platform": "",
    },
]


def ask_browser_mode() -> str:
    """Prompt the user to choose mobile or desktop browser simulation.

    Returns 'desktop' or 'mobile'. If the BROWSER_MODE environment variable
    is already set to a valid value, the prompt is skipped.
    """
    env_mode = BROWSER_MODE.strip().lower()
    if env_mode in ("desktop", "mobile"):
        print(f"[Config] Browser mode: {env_mode} (from BROWSER_MODE env var)")
        return env_mode

    print()
    print("┌─────────────────────────────────────────┐")
    print("│      Browser Simulation Mode            │")
    print("├─────────────────────────────────────────┤")
    print("│  [1] Desktop  (Windows / macOS / Linux) │")
    print("│  [2] Mobile   (Android / iOS)           │")
    print("└─────────────────────────────────────────┘")
    while True:
        choice = input("Select mode [1/2]: ").strip()
        if choice == "1":
            return "desktop"
        if choice == "2":
            return "mobile"
        print("  Please enter 1 or 2.")


def build_session_headers(mode: str) -> dict[str, str]:
    """Return realistic browser headers for *mode* ('desktop' or 'mobile').

    Anti-bot tweaks applied:
    - Randomised profile (UA + client hints) chosen from the pool.
    - sec-fetch-* headers that match a genuine top-level navigation.
    - sec-ch-ua-mobile flag set correctly per mode.
    - Upgrade-Insecure-Requests / DNT present as a real browser would send.
    """
    profiles = _MOBILE_PROFILES if mode == "mobile" else _DESKTOP_PROFILES
    profile = random.choice(profiles)
    is_mobile = mode == "mobile"

    headers: dict[str, str] = {
        "User-Agent": profile["user_agent"],  # type: ignore[assignment]
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "sec-ch-ua-mobile": "?1" if is_mobile else "?0",
    }

    if profile["sec-ch-ua"]:
        headers["sec-ch-ua"] = profile["sec-ch-ua"]
    if profile["sec-ch-ua-platform"]:
        headers["sec-ch-ua-platform"] = profile["sec-ch-ua-platform"]

    return headers


def normalize_proxy_url(proxy_url: str) -> str:
    """Return the proxy URL with scheme socks5://.

    Any existing http:// scheme is converted to socks5://. Bare addresses
    (no scheme) and all other schemes are left as-is, except that bare
    addresses receive a socks5:// prefix.
    """
    if "://" in proxy_url:
        scheme, rest = proxy_url.split("://", 1)
        if scheme.lower() == "http" and rest:
            return f"socks5://{rest}"
        return proxy_url
    return f"socks5://{proxy_url}"


def _get(session: requests.Session, url: str) -> requests.Response:
    """Perform a GET request and raise on HTTP errors, with friendly messages."""
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response
    except requests.exceptions.ProxyError as exc:
        print(f"[ERROR] Proxy error – could not reach the proxy server: {exc}", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.ConnectionError as exc:
        print(f"[ERROR] Connection error – failed to establish a connection: {exc}", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"[ERROR] Request timed out after {REQUEST_TIMEOUT}s.", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.HTTPError as exc:
        print(f"[ERROR] HTTP error: {exc}", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.RequestException as exc:
        print(f"[ERROR] Unexpected request error: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    # ── Browser mode selection ────────────────────────────────────────────────
    mode = ask_browser_mode()
    headers = build_session_headers(mode)
    print(f"\n[Config] Mode: {mode}  |  UA: {headers['User-Agent'][:60]}...")

    normalized_proxy_url = normalize_proxy_url(PROXY_URL) if PROXY_URL else ""
    proxies = {"http": normalized_proxy_url, "https": normalized_proxy_url} if normalized_proxy_url else None

    session = requests.Session()
    session.headers.update(headers)
    if proxies:
        session.proxies.update(proxies)

    # ── Step 1: open the base / landing URL ──────────────────────────────────
    print(f"\n[Step 1] Opening base URL: {TARGET_URL}")
    base_response = _get(session, TARGET_URL)
    print(f"         Status: {base_response.status_code}  |  Cookies collected: {len(session.cookies)}")

    # ── Anti-ban delay ────────────────────────────────────────────────────────
    delay = random.uniform(DELAY_MIN, DELAY_MAX)
    print(f"[Delay]  Waiting {delay:.1f}s before next request...")
    time.sleep(delay)

    # ── Step 2: open the target path ─────────────────────────────────────────
    target = urljoin(TARGET_URL, TARGET_PATH)
    # Update headers to reflect an internal navigation from the base URL
    session.headers.update({
        "Referer": TARGET_URL,
        "sec-fetch-site": "same-origin",
    })
    print(f"[Step 2] Opening target path: {target}")
    response = _get(session, target)
    print(f"         Status: {response.status_code}")

    html = response.text

    # ── Step 3: save the full HTML ────────────────────────────────────────────
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        file.write(html)

    # ── Step 4: print a concise summary ──────────────────────────────────────
    soup = BeautifulSoup(html, "html.parser")
    title = str(soup.title.string).strip() if soup.title and soup.title.string is not None else "(no title)"
    description_tag = soup.find("meta", attrs={"name": "description"})
    content = description_tag.get("content", "").strip() if description_tag else ""
    description = content or "(no description)"

    print()
    print(f"URL        : {response.url}")
    print(f"Status     : {response.status_code}")
    print(f"Title      : {title}")
    print(f"Description: {description}")
    print(f"Size       : {len(html):,} characters")
    print(f"Saved to   : {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
