#!/usr/bin/env bash
# Fail when the production package exceeds the 3.5 MB CI budget (implementation
# plan section 3). Checks out/silo-roku.zip unless another zip is given.
set -euo pipefail
cd "$(dirname "$0")/.."
zip=${1:-out/silo-roku.zip}
budget=3670016
[ -f "$zip" ] || { echo "missing $zip; run npm run build" >&2; exit 1; }

size=$(($(wc -c < "$zip")))
headroom=$((budget - size))
if [ "$headroom" -lt 0 ]; then
    echo "$zip is $size bytes, $((-headroom)) bytes over the $budget-byte budget" >&2
    exit 1
fi
echo "$zip is $size bytes; $headroom bytes of headroom under the $budget-byte budget"
