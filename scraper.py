"""
scraper.py – two-step scraper: open the base URL, then the target path,
             show summary info, and save the HTML.

Flow
----
1. Open TARGET_URL          – establishes a session and picks up any cookies
                              set by the landing page.
2. Open TARGET_URL/TARGET_PATH – follows through to the real target using the
                              session established in step 1.
3. Print a concise summary  – URL, status, title, description, size.
4. Save full HTML            – written to OUTPUT_FILE (default: scrapper.html).

Run:
    python scraper.py
"""

from __future__ import annotations

import sys
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import OUTPUT_FILE, PROXY_URL, REQUEST_TIMEOUT, TARGET_PATH, TARGET_URL


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
    normalized_proxy_url = normalize_proxy_url(PROXY_URL) if PROXY_URL else ""
    proxies = {"http": normalized_proxy_url, "https": normalized_proxy_url} if normalized_proxy_url else None

    session = requests.Session()
    if proxies:
        session.proxies.update(proxies)

    # ── Step 1: open the base / landing URL ──────────────────────────────────
    print(f"[Step 1] Opening base URL: {TARGET_URL}")
    base_response = _get(session, TARGET_URL)
    print(f"         Status: {base_response.status_code}  |  Cookies collected: {len(session.cookies)}")

    # ── Step 2: open the target path ─────────────────────────────────────────
    target = urljoin(TARGET_URL, TARGET_PATH)
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
    description = description_tag.get("content", "").strip() if description_tag and description_tag.get("content") else "(no description)"

    print()
    print(f"URL        : {response.url}")
    print(f"Status     : {response.status_code}")
    print(f"Title      : {title}")
    print(f"Description: {description}")
    print(f"Size       : {len(html):,} characters")
    print(f"Saved to   : {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
