"""
scraper.py – fetch a configured path, save the HTML, and print summary info.

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


def main() -> None:
    target = urljoin(TARGET_URL, TARGET_PATH)
    normalized_proxy_url = normalize_proxy_url(PROXY_URL) if PROXY_URL else ""
    proxies = {"http": normalized_proxy_url, "https": normalized_proxy_url} if normalized_proxy_url else None

    try:
        response = requests.get(target, timeout=REQUEST_TIMEOUT, proxies=proxies)
        response.raise_for_status()
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

    html = response.text

    # Save the full HTML to the output file (not printed to console)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        file.write(html)

    # Print a concise summary to the console
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string is not None else "(no title)"
    description_tag = soup.find("meta", attrs={"name": "description"})
    description = description_tag["content"].strip() if description_tag and description_tag.get("content") else "(no description)"

    print(f"URL        : {response.url}")
    print(f"Status     : {response.status_code}")
    print(f"Title      : {title}")
    print(f"Description: {description}")
    print(f"Size       : {len(html):,} characters")
    print(f"Saved to   : {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
