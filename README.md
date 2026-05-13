# FCX – Playwright Stealth Scraper

A **headless Playwright** scraper with real-browser fingerprint simulation,
targeting [quotes.toscrape.com](https://quotes.toscrape.com) — a site specifically
built for scraping practice.

## Stealth techniques applied

| # | Technique | How |
|---|-----------|-----|
| 1 | **`playwright-stealth`** | Patches `navigator.webdriver`, plugins list, language prefs, WebGL renderer strings, and more via JS injection at page-load time |
| 2 | **Randomised User-Agent** | `fake-useragent` rotates through real Chrome / Firefox / Edge UA strings; falls back to a built-in pool if the library is unavailable |
| 3 | **Desktop / Mobile browser profile pool** | On each run a random profile is selected from a desktop (Windows Chrome, macOS Chrome, Firefox) or mobile (Pixel 8 Android, Galaxy Android, iPhone iOS) pool – UA string and client-hint headers are kept consistent within the chosen profile |
| 4 | **Randomised viewport** | 7 common screen resolutions (including mobile) are rotated per context |
| 5 | **Device scale factor (DPR) randomisation** | `deviceScaleFactor` is randomly picked from `[1, 1.25, 1.5, 2]` to vary the device-pixel-ratio fingerprint |
| 6 | **Locale & timezone** | Fixed to `en-US` / `America/New_York` to match UA strings |
| 7 | **Realistic `Accept` / `Accept-Language` / `Accept-Encoding` headers** | Sent with every request exactly as a real browser would, including `image/avif` and `image/webp` preference signals |
| 8 | **`sec-fetch-*` headers** | `sec-fetch-dest: document`, `sec-fetch-mode: navigate`, `sec-fetch-site`, and `sec-fetch-user: ?1` mirror a genuine top-level browser navigation |
| 9 | **Client Hint headers (`sec-ch-ua`)** | `sec-ch-ua`, `sec-ch-ua-platform`, and `sec-ch-ua-mobile` are set consistently with the chosen browser profile |
| 10 | **`DNT` & `Upgrade-Insecure-Requests`** | Present in every request, as a real browser would include them |
| 11 | **Two-step session warm-up** | The landing / root URL is fetched first so the session accumulates real cookies before the target path is requested |
| 12 | **`Referer` + `sec-fetch-site: same-origin`** | After the warm-up step, the `Referer` header is set to the base URL and `sec-fetch-site` is updated to `same-origin`, mimicking genuine in-site navigation |
| 13 | **Dynamic query-string preservation** | The landing page HTML is scanned for links matching `TARGET_PATH`; any `?key=value` query parameters found are carried over to the target request |
| 14 | **Human-like scrolling** | Random wheel-scroll events (200–600 px, 0.3–0.9 s apart) before extraction (Playwright mode) |
| 15 | **Random inter-request delays** | Sleep `1.5–4.0 s` between requests to break timing fingerprints |
| 16 | **Exponential back-off retries** | Transient errors (connection, proxy, timeout) are retried up to `RETRY_COUNT` times with a `RETRY_BACKOFF × 2ⁿ` wait, avoiding hammering the target after a blip |
| 17 | **SOCKS5 proxy routing** | Optional `PROXY_URL` is normalised to `socks5://` and applied to all requests, masking the scraper's real IP |
| 18 | **Chromium launch flags** | `--disable-blink-features=AutomationControlled` removes the most common bot signal (Playwright mode) |
| 19 | **Fresh browser context per page** | Prevents cross-page cookie/session leakage (Playwright mode) |

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
