"""Fetch a TripIt iCal feed periodically and cache it for local re-serving."""

import os
import shutil
import tempfile
import time
from urllib.parse import urlparse

import requests

TRIPIT_ICS_URL = os.environ["TRIPIT_ICS_URL"]
SYNC_INTERVAL_RAW = int(os.environ.get("SYNC_INTERVAL_SECONDS", 1800))
if SYNC_INTERVAL_RAW < 60:
    raise ValueError(
        f"SYNC_INTERVAL_SECONDS must be >= 60, got {SYNC_INTERVAL_RAW}"
    )
SYNC_INTERVAL = SYNC_INTERVAL_RAW
OUTPUT_BASE = os.path.realpath("/data/ics")
MAX_BYTES = 10 * 1024 * 1024  # 10 MB — generous for an iCal file


def redact_url(url: str) -> str:
    """Replace the private token segment in a TripIt URL with ***."""
    parsed = urlparse(url)
    parts = parsed.path.split("/")
    redacted = [
        "***" if i > 0 and parts[i - 1] == "private" else part
        for i, part in enumerate(parts)
    ]
    return parsed._replace(path="/".join(redacted)).geturl()


def url_to_local_path(url: str) -> str:
    """Derive a safe local path from the URL, confined to OUTPUT_BASE."""
    parsed = urlparse(url)
    relative = parsed.path.lstrip("/")
    dest = os.path.realpath(os.path.join(OUTPUT_BASE, relative))
    if not dest.startswith(OUTPUT_BASE + os.sep):
        raise ValueError(f"URL path escapes OUTPUT_BASE: {url!r}")
    return dest


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
    dest = url_to_local_path(TRIPIT_ICS_URL)
    print("TripIt-Sync-M365 starting", flush=True)
    print(f"  Source:   {redact_url(TRIPIT_ICS_URL)}", flush=True)
    print(f"  Dest:     {dest}", flush=True)
    print(
        f"  Interval: {SYNC_INTERVAL}s ({SYNC_INTERVAL // 60} min)",
        flush=True,
    )

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
