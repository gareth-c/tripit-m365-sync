#!/bin/sh
set -e
chown syncer:syncer /data/ics /data/caddy
exec su-exec syncer "$@"
