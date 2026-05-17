"""Fetch a TripIt iCal feed periodically and cache it for local re-serving."""

import os
import secrets
import shutil
import tempfile
import time

import requests

TRIPIT_ICS_URL = os.environ["TRIPIT_ICS_URL"]
DOMAIN = os.environ["DOMAIN"]
HTTPS_PORT = os.environ.get("HTTPS_PORT", "8443")
SYNC_INTERVAL_RAW = int(os.environ.get("SYNC_INTERVAL_SECONDS", 1800))
if SYNC_INTERVAL_RAW < 60:
    raise ValueError(
        f"SYNC_INTERVAL_SECONDS must be >= 60, got {SYNC_INTERVAL_RAW}"
    )
SYNC_INTERVAL = SYNC_INTERVAL_RAW
OUTPUT_BASE = os.path.realpath("/data/ics")
TOKEN_FILE = os.path.join(OUTPUT_BASE, ".token")
MAX_BYTES = 10 * 1024 * 1024  # 10 MB — generous for an iCal file


def load_or_create_token() -> str:
    """Return the persistent random URL token, creating it on first run."""
    os.makedirs(OUTPUT_BASE, exist_ok=True)
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, encoding="utf-8") as fh:
            return fh.read().strip()
    token = secrets.token_urlsafe(32)
    with open(TOKEN_FILE, "w", encoding="utf-8") as fh:
        fh.write(token)
    return token


def build_dest(token: str) -> str:
    """Return the local path where the cached .ics file is written."""
    return os.path.join(
        OUTPUT_BASE, "feed", "ical", "private", token, "tripit.ics"
    )


def build_url(token: str) -> str:
    """Return the public HTTPS URL subscribers should use."""
    port = f":{HTTPS_PORT}" if HTTPS_PORT not in ("443", "80") else ""
    return f"https://{DOMAIN}{port}/feed/ical/private/{token}/tripit.ics"


def fetch_and_cache(url: str, dest: str) -> None:
    """Stream the iCal feed from url and atomically write it to dest."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp_path = None
    try:
        with requests.get(url, timeout=30, stream=True) as response:
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(
                dir=os.path.dirname(dest), delete=False, suffix=".tmp"
            ) as tmp:
                tmp_path = tmp.name
                size = 0
                for chunk in response.iter_content(65536):
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise ValueError(
                            f"Response exceeded {MAX_BYTES} bytes"
                        )
                    tmp.write(chunk)
        shutil.move(tmp_path, dest)
        tmp_path = None
        print(f"[OK] Synced {size} bytes -> {dest}", flush=True)
    except Exception:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def main() -> None:
    """Run the sync loop indefinitely."""
    token = load_or_create_token()
    dest = build_dest(token)
    feed_url = build_url(token)

    print("=" * 60, flush=True)
    print("TripIt-Sync-M365 starting", flush=True)
    print(f"  Interval: {SYNC_INTERVAL}s ({SYNC_INTERVAL // 60} min)",
          flush=True)
    print("", flush=True)
    print("  Subscribe to this URL in Microsoft 365:", flush=True)
    print(f"  {feed_url}", flush=True)
    print("=" * 60, flush=True)

    while True:
        try:
            fetch_and_cache(TRIPIT_ICS_URL, dest)
        except (OSError, ValueError, requests.RequestException) as exc:
            print(
                f"[WARN] Fetch failed: {exc} — keeping last cached version",
                flush=True,
            )
        time.sleep(SYNC_INTERVAL)


if __name__ == "__main__":
    main()
