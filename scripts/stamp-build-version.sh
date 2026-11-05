#!/usr/bin/env bash
# Stamp the version into the packaged manifest, leaving the committed manifest
# alone. bsc deletes its staging directory after zipping, so this rewrites the
# manifest entry inside the zip.
#
# Release builds set SILO_VERSION (X.Y.Z) and SILO_BUILD (the repository's
# build counter; see scripts/release-version.py): the package gets
# major_version=X, minor_version=Y, build_version=SILO_BUILD, and
# silo_version=X.Y.Z, which the app reports since Roku's manifest has no patch
# field. Otherwise build_version becomes the CI run number, and without
# GITHUB_RUN_NUMBER (local builds) the package keeps the committed values.
set -euo pipefail
cd "$(dirname "$0")/.."
zip=${1:-out/silo-roku.zip}
version=${SILO_VERSION:-}
build=${SILO_BUILD:-}

if [ -n "$version" ] || [ -n "$build" ]; then
    [[ $version =~ ^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]] ||
        { echo "SILO_VERSION is not X.Y.Z: $version" >&2; exit 1; }
    major=${BASH_REMATCH[1]} minor=${BASH_REMATCH[2]}
    [[ $build =~ ^[1-9][0-9]*$ ]] || { echo "SILO_BUILD is not a positive number: $build" >&2; exit 1; }
elif [ -n "${GITHUB_RUN_NUMBER:-}" ]; then
    build=$GITHUB_RUN_NUMBER
    case $build in *[!0-9]*) echo "GITHUB_RUN_NUMBER is not a number: $build" >&2; exit 1 ;; esac
else
    echo "GITHUB_RUN_NUMBER unset; $zip keeps the committed version"
    exit 0
fi
[ -f "$zip" ] || { echo "missing $zip; run npm run build" >&2; exit 1; }
zip_path=$(cd "$(dirname "$zip")" && pwd)/$(basename "$zip")

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
unzip -q "$zip" manifest -d "$tmp"
for key in major_version minor_version build_version; do
    grep -q "^$key=" "$tmp/manifest" || { echo "$zip manifest has no $key" >&2; exit 1; }
done
edits=(-e "s/^build_version=.*/build_version=$build/")
if [ -n "$version" ]; then
    edits+=(-e "s/^major_version=.*/major_version=$major/" -e "s/^minor_version=.*/minor_version=$minor/")
fi
grep -v '^silo_version=' "$tmp/manifest" | sed "${edits[@]}" > "$tmp/manifest.new"
[ -z "$version" ] || echo "silo_version=$version" >> "$tmp/manifest.new"
mv "$tmp/manifest.new" "$tmp/manifest"
(cd "$tmp" && zip -q -X "$zip_path" manifest)
echo "stamped ${version:+version $version }build_version=$build into $zip"
