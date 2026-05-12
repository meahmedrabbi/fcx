"""
scraper.py – fetch a configured path, print the response URL and HTML, and save it.

Run:
    python scraper.py
"""

from __future__ import annotations

from urllib.parse import urljoin

import requests

from config import OUTPUT_FILE, PROXY_URL, REQUEST_TIMEOUT, TARGET_PATH, TARGET_URL


def normalize_proxy_url(proxy_url: str) -> str:
    if "://" in proxy_url:
        return proxy_url
    return f"http://{proxy_url}"


def main() -> None:
    target = urljoin(TARGET_URL, TARGET_PATH)
    normalized_proxy_url = normalize_proxy_url(PROXY_URL) if PROXY_URL else ""
    proxies = {"http": normalized_proxy_url, "https": normalized_proxy_url} if normalized_proxy_url else None

    response = requests.get(target, timeout=REQUEST_TIMEOUT, proxies=proxies)
    response.raise_for_status()

    print(response.url)
    html = response.text
    print(html)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        file.write(html)


if __name__ == "__main__":
    main()
