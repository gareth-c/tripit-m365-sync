"""Fetch a TripIt iCal feed periodically and cache it for local re-serving."""

import os
import shutil
import tempfile
import time
from urllib.parse import urlparse

import requests

TRIPIT_ICS_URL = os.environ["TRIPIT_ICS_URL"]
SYNC_INTERVAL = int(os.environ.get("SYNC_INTERVAL_SECONDS", 1800))
OUTPUT_BASE = "/data/ics"


def url_to_local_path(url: str) -> str:
    """Derive a local path from URL by stripping scheme and host."""
    parsed = urlparse(url)
    relative = parsed.path.lstrip("/")
    return os.path.join(OUTPUT_BASE, relative)


def fetch_and_cache(url: str, dest: str) -> None:
    """Fetch the iCal feed from url and atomically write it to dest."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    with tempfile.NamedTemporaryFile(
        dir=os.path.dirname(dest), delete=False, suffix=".tmp"
    ) as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name
    shutil.move(tmp_path, dest)
    print(f"[OK] Synced {len(response.content)} bytes -> {dest}", flush=True)


def main() -> None:
    """Run the sync loop indefinitely."""
    dest = url_to_local_path(TRIPIT_ICS_URL)
    print("TripIt-Sync-M365 starting", flush=True)
    print(f"  Source:   {TRIPIT_ICS_URL}", flush=True)
    print(f"  Dest:     {dest}", flush=True)
    print(
        f"  Interval: {SYNC_INTERVAL}s ({SYNC_INTERVAL // 60} min)",
        flush=True,
    )

    while True:
        try:
            fetch_and_cache(TRIPIT_ICS_URL, dest)
        except (OSError, requests.RequestException) as exc:
            print(
                f"[WARN] Fetch failed: {exc} — keeping last cached version",
                flush=True,
            )
        time.sleep(SYNC_INTERVAL)


if __name__ == "__main__":
    main()
