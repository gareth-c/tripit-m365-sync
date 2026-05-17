# tripit-m365-sync

A self-hosted Docker service that bridges TripIt's iCal feed to Microsoft 365 calendar subscriptions.

## The Problem

TripIt's iCal feed has a long-standing compatibility issue with Microsoft 365. TripIt acknowledges they don't officially support M365 calendar syncing and describes it as a vendor issue; The result: M365 calendar subscriptions to TripIt either fail silently or stop updating.

The root cause is that TripIt's feed uses redirect chains and HTTP response patterns that M365's calendar subscription engine doesn't handle reliably — particularly in the new Outlook client, Outlook on the web, and iOS.


## How It Works

```
[M365 Calendar] ──── HTTPS poll ────► [Caddy (Let's Encrypt TLS)]
                                              │  serves cached .ics
                                       [ics_cache volume]
                                              ▲  atomic write every 30 min
                                       [Python syncer]
                                              │  HTTPS GET
                                       [TripIt iCal feed]
```

This service fetches your TripIt feed every 30 minutes and caches it locally. Caddy re-serves it over HTTPS with an automatically managed Let's Encrypt certificate. M365 subscribes to your domain's URL instead of TripIt directly — a clean, standards-compliant HTTPS `.ics` file with no redirects.

On first launch, the syncer generates a random token and serves the feed at a URL that has **no relation** to your TripIt private token:

```
https://your-domain.com:8443/feed/ical/private/<RANDOM_TOKEN>/tripit.ics
```

The full URL is printed to the container log on every startup (see [Getting your URL](#getting-your-url)).

## Prerequisites

- A server with **Docker** and **Docker Compose** installed
- A **domain name** (or subdomain) with an **A record** pointing to the server's public IP
- Ports **80** and **443** open in your firewall / cloud security group
- Your **TripIt private iCal URL** (TripIt > Settings > Calendars & Sync > iCalendar)

## Setup

**1. Clone or copy this repo onto your server.**

**2. Edit `docker-compose.yml`** — set your values in the `environment:` blocks:

| Variable | Where | Description |
|---|---|---|
| `DOMAIN` | caddy + syncer | Your domain or subdomain |
| `HTTPS_PORT` | caddy + syncer | HTTPS port (default: `8443`) |
| `TRIPIT_ICS_URL` | syncer | Your TripIt private iCal URL |
| `SYNC_INTERVAL_SECONDS` | syncer | Fetch interval in seconds (default: `1800`) |

```yaml
# In the caddy service:
- DOMAIN=your-domain.com
- HTTPS_PORT=8443

# In the syncer service:
- TRIPIT_ICS_URL=https://www.tripit.com/feed/ical/private/YOUR_TOKEN/tripit.ics
- DOMAIN=your-domain.com
- HTTPS_PORT=8443
```

**3. Start the services:**

```bash
docker-compose up -d
```

Caddy will automatically obtain a Let's Encrypt certificate on first start (requires DNS to already be pointing at the server). This takes about 60 seconds.

## Getting Your URL

The syncer prints your subscription URL to the container log on every startup:

```bash
docker-compose logs syncer
```

Look for output like this:

```
============================================================
TripIt-Sync-M365 starting
  Interval: 1800s (30 min)

  Subscribe to this URL in Microsoft 365:
  https://your-domain.com:8443/feed/ical/private/abc123.../tripit.ics
============================================================
```

The random token is generated once and saved to the `ics_cache` volume — it stays the same across restarts.

## Adding to Microsoft 365

1. Copy the URL from `docker-compose logs syncer`
2. Open [Outlook on the web](https://outlook.office.com) or the M365 Calendar app
3. Go to **Calendar** > **Add calendar** > **Subscribe from web**
4. Paste the URL and give it a name (e.g. *TripIt*), then click **Import**

M365 will poll the feed periodically (typically every 24 hours). Because the feed is now served as a plain HTTPS `.ics` file with no redirects, it syncs reliably.

## Troubleshooting

**Check syncer logs** (should show a sync every 30 minutes):
```bash
docker-compose logs -f syncer
```

**Check Caddy logs** (certificate issuance, access logs):
```bash
docker-compose logs -f caddy
```

**Certificate not issuing?** Ensure:
- The domain's A record points to this server's public IP (`dig your-domain.com`)
- Port 80 is open (Let's Encrypt HTTP-01 challenge uses port 80)
- No other service is bound to port 80 or 443

**Feed returns 404?** The syncer may not have run yet. Check `docker-compose logs syncer` — it fetches immediately on startup, so a 404 shortly after launch usually means the TripIt URL is wrong.

## Pre-built Image

The syncer image is published to GitHub Container Registry on every push to `main` and on version tags:

```
ghcr.io/gareth-c/tripit-m365-sync/syncer:main
```

Supported platforms: `linux/amd64`, `linux/arm64`.

## Updating

```bash
docker-compose pull
docker-compose up -d
```

## Changing the Port or Sync Interval

All configuration is in the `environment:` blocks in `docker-compose.yml`. Change any value and restart:

```bash
docker-compose up -d
```

Note: M365 controls how often it polls your feed — typically every 24 hours regardless of how often your service syncs. The 30-minute sync interval ensures your cached copy is fresh when M365 does poll.
