"""Health check — exits 0 if the cache was written within the last 2 hours."""

import os
import sys
import time

CACHE_DIR = "/data/ics"
MAX_AGE_SECONDS = 7200


def main() -> None:
    """Check the cache directory mtime and exit with an appropriate code."""
    try:
        mtime = os.stat(CACHE_DIR).st_mtime
    except FileNotFoundError:
        print(f"[HEALTH] Cache directory not found: {CACHE_DIR}", flush=True)
        sys.exit(1)

    age = time.time() - mtime
    if age > MAX_AGE_SECONDS:
        print(
            f"[HEALTH] Cache is stale "
            f"({int(age)}s old, limit {MAX_AGE_SECONDS}s)",
            flush=True,
        )
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
