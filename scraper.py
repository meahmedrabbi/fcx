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
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config import (
    BROWSER_MODE,
    DELAY_MAX,
    DELAY_MIN,
    OUTPUT_FILE,
    PROXY_URL,
    REQUEST_TIMEOUT,
    RETRY_BACKOFF,
    RETRY_COUNT,
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
        "Accept-Encoding": "gzip, deflate",
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
    """Perform a GET request, retrying transient errors with exponential back-off.

    Transient errors (ConnectionError, ProxyError, Timeout) are retried up to
    RETRY_COUNT additional times.  Each attempt waits RETRY_BACKOFF * 2^(attempt-1)
    seconds before retrying.  Non-transient errors (HTTP, unexpected) exit immediately.
    """
    _TRANSIENT = (
        requests.exceptions.ProxyError,
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
    )

    last_exc: Exception | None = None
    for attempt in range(1, RETRY_COUNT + 2):  # 1 original + RETRY_COUNT retries
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response
        except _TRANSIENT as exc:
            last_exc = exc
            if attempt <= RETRY_COUNT:
                # attempt=1 → wait BACKOFF*1, attempt=2 → BACKOFF*2, attempt=3 → BACKOFF*4 …
                wait = RETRY_BACKOFF * (2 ** (attempt - 1))
                kind = "Proxy" if isinstance(exc, requests.exceptions.ProxyError) else (
                    "Timeout" if isinstance(exc, requests.exceptions.Timeout) else "Connection"
                )
                print(
                    f"[Retry {attempt}/{RETRY_COUNT}] {kind} error – retrying in {wait:.1f}s: {exc}",
                    file=sys.stderr,
                )
                time.sleep(wait)
            else:
                kind = "Proxy error" if isinstance(exc, requests.exceptions.ProxyError) else (
                    f"Request timed out after {REQUEST_TIMEOUT}s"
                    if isinstance(exc, requests.exceptions.Timeout)
                    else "Connection error – failed to establish a connection"
                )
                print(f"[ERROR] {kind}: {last_exc}", file=sys.stderr)
                sys.exit(1)
        except requests.exceptions.HTTPError as exc:
            print(f"[ERROR] HTTP error: {exc}", file=sys.stderr)
            sys.exit(1)
        except requests.exceptions.RequestException as exc:
            print(f"[ERROR] Unexpected request error: {exc}", file=sys.stderr)
            sys.exit(1)

    # Unreachable – loop always returns or exits – but satisfies type checkers.
    print(f"[ERROR] All {RETRY_COUNT + 1} attempts failed: {last_exc}", file=sys.stderr)
    sys.exit(1)


def extract_forms(html: str, page_url: str) -> list[dict]:
    """Return a list of form descriptors found in *html*.

    Each descriptor is a dict with:
      - ``action``   : resolved URL the form submits to
      - ``method``   : HTTP method (GET / POST, defaulting to GET)
      - ``fields``   : list of dicts, one per interactive control:
            name, type, value, placeholder, required, tag
      - ``submits``  : list of dicts, one per submit trigger:
            tag, type, name, value, text
    """
    soup = BeautifulSoup(html, "html.parser")
    forms: list[dict] = []

    for form in soup.find_all("form"):
        action_raw: str = form.get("action", "") or ""
        action = urljoin(page_url, action_raw) if action_raw else page_url
        method = (form.get("method", "GET") or "GET").upper()

        fields: list[dict] = []
        for tag in form.find_all(["input", "textarea", "select"]):
            tag_name: str = tag.name
            field_type = tag.get("type", "text" if tag_name == "input" else tag_name).lower()
            # Skip hidden submit/image/reset – we handle submits separately
            if field_type in ("submit", "image", "reset", "button"):
                continue
            fields.append({
                "tag": tag_name,
                "type": field_type,
                "name": tag.get("name", ""),
                "value": tag.get("value", ""),
                "placeholder": tag.get("placeholder", ""),
                "required": tag.has_attr("required"),
            })

        submits: list[dict] = []
        # <input type="submit|image">
        for tag in form.find_all("input", type=lambda t: t and t.lower() in ("submit", "image")):
            submits.append({
                "tag": "input",
                "type": tag.get("type", "submit").lower(),
                "name": tag.get("name", ""),
                "value": tag.get("value", ""),
                "text": "",
            })
        # <button> (type defaults to "submit" inside a form)
        for tag in form.find_all("button"):
            btn_type = (tag.get("type", "submit") or "submit").lower()
            submits.append({
                "tag": "button",
                "type": btn_type,
                "name": tag.get("name", ""),
                "value": tag.get("value", ""),
                "text": tag.get_text(strip=True),
            })

        forms.append({"action": action, "method": method, "fields": fields, "submits": submits})

    return forms


def find_target_url(landing_html: str, base_url: str, target_path: str) -> str:
    """Return the full URL for *target_path*, preserving any dynamic query params.

    Scans every ``<a href>`` in *landing_html* for one whose path component
    matches *target_path* (trailing-slash-insensitive).  If such a link is
    found its entire href – including any ``?key=value`` query string – is
    resolved against *base_url* and returned.

    Falls back to ``urljoin(base_url, target_path)`` (no query string) if no
    matching link is found, so the scraper behaves exactly as before when the
    landing page does not contain the link.
    """
    soup = BeautifulSoup(landing_html, "html.parser")
    normalised_target = target_path.rstrip("/")
    for tag in soup.find_all("a", href=True):
        href: str = tag["href"]
        parsed = urlparse(href)
        if parsed.path.rstrip("/") == normalised_target:
            return urljoin(base_url, href)
    return urljoin(base_url, target_path)


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
    base_html = base_response.content.decode("utf-8", errors="replace")
    print(f"         Status: {base_response.status_code}  |  Cookies collected: {len(session.cookies)}")

    # ── Anti-ban delay ────────────────────────────────────────────────────────
    delay = random.uniform(DELAY_MIN, DELAY_MAX)
    print(f"[Delay]  Waiting {delay:.1f}s before next request...")
    time.sleep(delay)

    # ── Step 2: open the target path (with any dynamic query params) ──────────
    # find_target_url scans the landing page for a link whose path matches
    # TARGET_PATH and carries over any ?key=value query parameters it finds.
    target = find_target_url(base_html, TARGET_URL, TARGET_PATH)
    # Update headers to reflect an internal navigation from the base URL
    session.headers.update({
        "Referer": TARGET_URL,
        "sec-fetch-site": "same-origin",
    })
    print(f"[Step 2] Opening target path: {target}")
    response = _get(session, target)
    print(f"         Status: {response.status_code}")

    html = response.content.decode("utf-8", errors="replace")

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

    # ── Step 5: print form / input summary ───────────────────────────────────
    forms = extract_forms(html, str(response.url))
    if not forms:
        print("\n[Forms]  No forms found on the page.")
    else:
        print(f"\n[Forms]  Found {len(forms)} form(s):")
        for i, form in enumerate(forms, 1):
            print(f"\n  ┌── Form {i} ─────────────────────────────")
            print(f"  │  Action : {form['action']}")
            print(f"  │  Method : {form['method']}")
            if form["fields"]:
                print(f"  │  Fields ({len(form['fields'])}):")
                for f in form["fields"]:
                    req = " [required]" if f["required"] else ""
                    ph  = f"  placeholder={f['placeholder']!r}" if f["placeholder"] else ""
                    val = f"  value={f['value']!r}" if f["value"] else ""
                    print(f"  │    <{f['tag']} type={f['type']!r} name={f['name']!r}{val}{ph}{req}>")
            else:
                print("  │  Fields : (none)")
            if form["submits"]:
                print(f"  │  Submit buttons ({len(form['submits'])}):")
                for s in form["submits"]:
                    label = s["text"] or s["value"] or s["name"] or "(unlabelled)"
                    print(f"  │    <{s['tag']} type={s['type']!r} name={s['name']!r}> → {label!r}")
            else:
                print("  │  Submit buttons: (none)")
            print("  └─────────────────────────────────────")


if __name__ == "__main__":
    main()
