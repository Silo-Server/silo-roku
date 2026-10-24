#!/usr/bin/env bash
# Build the Rooibos test packages and run them headless under brs-node, in
# shards (scripts/test-headless.py). Pass --junit to also write
# reports/junit.xml; TEST_JOBS sets how many shards run at once.
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 -I scripts/test-headless.py "$@"
