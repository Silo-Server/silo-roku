#!/usr/bin/env bash
# Set build_version in the packaged manifest to the CI run number, leaving the
# committed manifest alone. bsc deletes its staging directory after zipping, so
# this rewrites the manifest entry inside the zip. Without GITHUB_RUN_NUMBER
# (local builds) the package keeps the committed value.
set -euo pipefail
cd "$(dirname "$0")/.."
zip=${1:-out/silo-roku.zip}
run=${GITHUB_RUN_NUMBER:-}

if [ -z "$run" ]; then
    echo "GITHUB_RUN_NUMBER unset; $zip keeps the committed build_version"
    exit 0
fi
case $run in *[!0-9]*) echo "GITHUB_RUN_NUMBER is not a number: $run" >&2; exit 1 ;; esac
[ -f "$zip" ] || { echo "missing $zip; run npm run build" >&2; exit 1; }
zip_path=$(cd "$(dirname "$zip")" && pwd)/$(basename "$zip")

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
unzip -q "$zip" manifest -d "$tmp"
grep -q '^build_version=' "$tmp/manifest" || { echo "$zip manifest has no build_version" >&2; exit 1; }
sed "s/^build_version=.*/build_version=$run/" "$tmp/manifest" > "$tmp/manifest.new"
mv "$tmp/manifest.new" "$tmp/manifest"
(cd "$tmp" && zip -q -X "$zip_path" manifest)
echo "stamped build_version=$run into $zip"
