#!/usr/bin/env bash
# Run Roku Static Analysis (sca-cmd) on the built package and write
# reports/sca.xml. Fails on any error and on any warning in the Monitoring
# (memory monitor) category.
#
#   scripts/sca.sh [PACKAGE]        analyze a zip or staged directory (default out/silo-roku.zip)
#   scripts/sca.sh --print-pin      print the pinned sha256 (the CI cache key)
#   scripts/sca.sh --check-upstream fail if the live download no longer matches the pin
#
# Roku replaces the unversioned download in place, so the zip is pinned by
# sha256 and cached outside the repository in SCA_CMD_CACHE_DIR/<sha256>
# (default ${XDG_CACHE_HOME:-~/.cache}/silo-roku/sca-cmd). A mismatch fails
# with instructions to bump the pin; an unverified tool never runs. SCA_CMD_URL
# overrides the download location (for a mirror); the pin still applies.
set -euo pipefail
cd "$(dirname "$0")/.."

# The jar's Implementation-Version; Roku's changelog dates it 2026-10-13.
SCA_CMD_VERSION=14.16.0
SCA_CMD_SHA256=272ef9847bf69daacac64094596f2ede7a9c1a8e9d7418c73c18ab148b772f31
url=${SCA_CMD_URL:-https://devtools.web.roku.com/static-channel-analysis/sca-cmd.zip}
changelog=https://devtools.web.roku.com/static-channel-analysis/CHANGELOG.md

sha256() {
    if command -v sha256sum > /dev/null; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -d' ' -f1
}

download() {
    curl -fsSL --proto '=https' --retry 3 --connect-timeout 15 --max-time 120 -o "$1" "$url"
}

# Version string from the jar manifest inside a downloaded zip, reduced to
# characters a version can contain so untrusted bytes never reach the log.
jar_version() {
    unzip -p "$1" sca-cmd/lib/sca-cmd.jar > "$work/version.jar" 2> /dev/null &&
        unzip -p "$work/version.jar" META-INF/MANIFEST.MF 2> /dev/null | sed -n 's/^Implementation-Version:[[:space:]]*//p' | tr -cd '0-9A-Za-z.+-'
}

# Download sca-cmd.zip to $1 and stop with bump instructions unless it matches the pin.
fetch_pinned() {
    local actual version
    download "$1"
    actual=$(sha256 "$1")
    [ "$actual" != "$SCA_CMD_SHA256" ] || return 0
    version=$(jar_version "$1" || true)
    echo "The downloaded sca-cmd.zip does not match the pinned $SCA_CMD_VERSION ($SCA_CMD_SHA256)." >&2
    echo "Roku replaces the unversioned download in place, so the pin needs a deliberate bump." >&2
    echo "Downloaded sha256: $actual (Implementation-Version: ${version:-unknown})" >&2
    echo "Review $changelog, then bump SCA_CMD_VERSION and SCA_CMD_SHA256 in scripts/sca.sh." >&2
    exit 1
}

if [ "${1:-}" = --print-pin ]; then
    echo "$SCA_CMD_SHA256"
    exit 0
fi

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

if [ "${1:-}" = --check-upstream ]; then
    fetch_pinned "$work/sca-cmd.zip"
    echo "upstream sca-cmd matches the pinned $SCA_CMD_VERSION ($SCA_CMD_SHA256)"
    exit 0
fi

package=${1:-out/silo-roku.zip}
[ -e "$package" ] || { echo "missing $package; run npm run build" >&2; exit 1; }
package=$(cd "$(dirname "$package")" && pwd)/$(basename "$package")
command -v java > /dev/null || { echo "sca-cmd needs Java (21 in CI) on PATH" >&2; exit 1; }

# The cached zip is re-verified on every run; only a verified download is stored.
cache=${SCA_CMD_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/silo-roku/sca-cmd}/$SCA_CMD_SHA256
zip=$cache/sca-cmd.zip
if [ ! -f "$zip" ] || [ "$(sha256 "$zip")" != "$SCA_CMD_SHA256" ]; then
    echo "downloading sca-cmd $SCA_CMD_VERSION into $cache"
    fetch_pinned "$work/sca-cmd.zip"
    mkdir -p "$cache"
    mv "$work/sca-cmd.zip" "$zip"
fi

# Unpack the verified jar afresh for each run and run it from the scratch
# directory, so nothing else cached or in the repository is loaded as tool code.
unzip -q "$zip" sca-cmd/lib/sca-cmd.jar -d "$work"
mkdir -p reports
report=$PWD/reports/sca.xml
rm -f "$report"

status=0
(cd "$work" && java -jar sca-cmd/lib/sca-cmd.jar "$package" \
    --severity info --exit error --format console,junit --output "$report") || status=$?
[ -f "$report" ] || { echo "sca-cmd exited $status without writing $report" >&2; exit 1; }

# The JUnit report marks each finding's severity in testcase/@status and its
# category in the enclosing testsuite/@name.
python3 -I - "$report" "$status" << 'PY'
import sys
import xml.etree.ElementTree as ET

report, status = sys.argv[1], int(sys.argv[2])
errors = monitoring = 0
for suite in ET.parse(report).getroot().iter("testsuite"):
    for case in suite.iter("testcase"):
        severity = (case.get("status") or "").lower()
        if severity == "error":
            errors += 1
        elif severity == "warning" and (suite.get("name") or "").lower() == "monitoring":
            monitoring += 1
print(f"sca-cmd: {errors} errors, {monitoring} monitoring warnings", flush=True)
if errors or monitoring or status:
    print(f"Static Analysis failed (sca-cmd exit {status}); see the log above or {report}", file=sys.stderr)
    sys.exit(1)
PY
