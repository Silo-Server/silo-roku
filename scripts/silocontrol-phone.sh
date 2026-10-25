#!/usr/bin/env bash
# Run scripts/silocontrol-phone.mjs against the Roku in .env, on this machine
# or, with ROKU_DEPLOY_VIA, on the host that can reach the Roku (the script
# goes over stdin, so that host needs only Node). Arguments pass through.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f .env ]; then set -a; . ./.env; set +a; fi
: "${ROKU_HOST:?set ROKU_HOST in .env}"
args=(--host "$ROKU_HOST" "$@")
if [ -n "${ROKU_DEPLOY_VIA:-}" ]; then
    printf -v quoted ' %q' "${args[@]}"
    $ROKU_DEPLOY_VIA "node --input-type=module -$quoted" < scripts/silocontrol-phone.mjs
else
    node scripts/silocontrol-phone.mjs "${args[@]}"
fi
