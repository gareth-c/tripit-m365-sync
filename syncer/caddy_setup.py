"""Manage the Caddy config file and reload Caddy when the config changes."""

import os

import requests

DOMAIN = os.environ["DOMAIN"]
HTTPS_PORT = os.environ.get("HTTPS_PORT", "8443")
CADDY_CONF_DIR = "/data/caddy"
CADDY_CONF_FILE = os.path.join(CADDY_CONF_DIR, "Caddyfile")
CADDY_ADMIN_URL = "http://caddy:2019/load"


def _build_caddyfile() -> str:
    """Build the Caddyfile content from environment variables."""
    return (
        "{\n"
        "    admin 0.0.0.0:2019\n"
        "}\n"
        "\n"
        f"{DOMAIN}:{HTTPS_PORT} {{\n"
        "    root * /srv/ics\n"
        "\n"
        "    @ical path /feed/ical/private/*/tripit.ics\n"
        "    @health path /feed/ical/private/*/health\n"
        "\n"
        "    route {\n"
        "        handle @ical {\n"
        "            file_server\n"
        "        }\n"
        "        handle @health {\n"
        "            header Content-Type application/json\n"
        "            file_server\n"
        "        }\n"
        "        respond 404\n"
        "    }\n"
        "}\n"
    )


def ensure_caddyfile() -> None:
    """Write Caddyfile if missing or outdated; reload Caddy if running."""
    os.makedirs(CADDY_CONF_DIR, exist_ok=True)
    expected = _build_caddyfile()

    existing = ""
    if os.path.exists(CADDY_CONF_FILE):
        with open(CADDY_CONF_FILE, encoding="utf-8") as fh:
            existing = fh.read()

    if expected == existing:
        print("[CADDY] Config is up to date.", flush=True)
        return

    with open(CADDY_CONF_FILE, "w", encoding="utf-8") as fh:
        fh.write(expected)
    print(f"[CADDY] Wrote config -> {CADDY_CONF_FILE}", flush=True)

    # Reload running Caddy — safe to fail if Caddy isn't up yet
    try:
        response = requests.post(
            CADDY_ADMIN_URL,
            data=expected.encode(),
            headers={"Content-Type": "text/caddyfile"},
            timeout=5,
        )
        response.raise_for_status()
        print("[CADDY] Reloaded via admin API.", flush=True)
    except requests.RequestException as exc:
        print(
            f"[CADDY] Admin API not reachable ({exc})"
            " — Caddy will use the file on next start.",
            flush=True,
        )
