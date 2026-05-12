"""
scraper.py – fetch one page and print the raw HTML.

Run:
    python scraper.py
"""

from __future__ import annotations

import requests

from config import TARGET_URL, REQUEST_TIMEOUT


def main() -> None:
    response = requests.get(TARGET_URL, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    print(response.text)


if __name__ == "__main__":
    main()
