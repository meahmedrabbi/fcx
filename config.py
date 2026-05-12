"""
config.py – central configuration for the stealth scraper.
"""

TARGET_URL = "https://quotes.toscrape.com"

# How many pages to scrape (None = follow all "Next" links)
MAX_PAGES = 5

# Output
OUTPUT_FILE = "quotes.json"

# Request delays (seconds) – random range to mimic human pacing
DELAY_MIN = 1.0
DELAY_MAX = 3.5

# Viewport sizes to rotate through
VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 800},
    {"width": 1536, "height": 864},
]
