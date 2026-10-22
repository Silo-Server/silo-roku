#!/usr/bin/env bash
# Stream the dev app's BrightScript console (print output, crashes) from port 8085.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f .env ]; then set -a; . ./.env; set +a; fi
: "${ROKU_HOST:?set ROKU_HOST in .env}"
if [ -n "${ROKU_DEPLOY_VIA:-}" ]; then
    exec $ROKU_DEPLOY_VIA "nc $ROKU_HOST 8085"
fi
exec nc "$ROKU_HOST" 8085
