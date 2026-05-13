"""
config.py – configuration for the scraper.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

TARGET_URL = os.environ.get("TARGET_URL", "https://example.com/")
TARGET_PATH = os.environ.get("TARGET_PATH", "/")
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "30"))
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "scrapper.html")
PROXY_URL = os.environ.get("PROXY_URL", "")

# Anti-ban: human-like delay range (seconds) between requests.
# Override with DELAY_MIN / DELAY_MAX environment variables.
DELAY_MIN = float(os.environ.get("DELAY_MIN", "1.5"))
DELAY_MAX = float(os.environ.get("DELAY_MAX", "4.0"))

# Browser simulation mode: "desktop" or "mobile".
# When set, the interactive prompt is skipped.
BROWSER_MODE = os.environ.get("BROWSER_MODE", "")

# Retry settings for transient connection / proxy / timeout errors.
# RETRY_COUNT  – how many additional attempts after the first failure (0 = no retry).
# RETRY_BACKOFF – base seconds for exponential back-off: attempt 1 sleeps BACKOFF*2^0,
#                 attempt 2 sleeps BACKOFF*2^1, etc.
RETRY_COUNT = int(os.environ.get("RETRY_COUNT", "4"))
RETRY_BACKOFF = float(os.environ.get("RETRY_BACKOFF", "2.0"))

# Viewports used by stealth_utils for Playwright-based contexts.
VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
    {"width": 1280, "height": 800},
    {"width": 390,  "height": 844},   # iPhone 14 Pro
    {"width": 412,  "height": 915},   # Android (Pixel 7)
    {"width": 360,  "height": 780},   # Android (Galaxy S21)
]
