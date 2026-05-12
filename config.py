"""
config.py – configuration for the single-page scraper.
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
