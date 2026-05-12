# FCX – Playwright Stealth Scraper

A **headless Playwright** scraper with real-browser fingerprint simulation,
targeting [quotes.toscrape.com](https://quotes.toscrape.com) — a site specifically
built for scraping practice.

## Stealth techniques applied

| Technique | How |
|-----------|-----|
| **`playwright-stealth`** | Patches `navigator.webdriver`, plugins list, language prefs, WebGL renderer strings, and more via JS injection at page-load time |
| **Randomised User-Agent** | `fake-useragent` rotates through real Chrome / Firefox / Edge UA strings |
| **Randomised viewport** | 5 common screen resolutions are rotated per context |
| **Locale & timezone** | Fixed to `en-US` / `America/New_York` to match UA strings |
| **Human-like scrolling** | Random wheel-scroll events before extraction |
| **Random inter-request delays** | Sleep `1–3.5 s` between pages to break timing fingerprints |
| **Chromium launch flags** | `--disable-blink-features=AutomationControlled` removes the most common bot signal |
| **Fresh browser context per page** | Prevents cross-page cookie/session leakage |

## Project structure

```
fcx/
├── config.py          # Tunable settings (URL, pages, delays, viewports)
├── stealth_utils.py   # Browser context factory + stealth helpers
├── scraper.py         # Main async scraper entry point
├── requirements.txt   # Python dependencies
└── README.md
```

## Requirements

- Python 3.10+
- Chromium (installed automatically by Playwright)

## Setup

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Install Playwright's bundled Chromium
playwright install chromium

# 3. Run the scraper
python scraper.py
```

Output is written to **`quotes.json`** (configurable in `config.py`).

## Configuration (`config.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `TARGET_URL` | `https://quotes.toscrape.com` | Root URL to scrape |
| `MAX_PAGES` | `5` | Stop after N pages (`None` = all pages) |
| `OUTPUT_FILE` | `quotes.json` | Output file path |
| `DELAY_MIN / MAX` | `1.0 / 3.5` s | Inter-page sleep range |
| `VIEWPORTS` | 5 resolutions | Pool to rotate through |

## Sample output (`quotes.json`)

```json
[
  {
    "text": "\u201cThe world as we have created it is a process of our thinking.\u201d",
    "author": "Albert Einstein",
    "tags": ["change", "deep-thoughts", "thinking", "world"]
  },
  ...
]
```
