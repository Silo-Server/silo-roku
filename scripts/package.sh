#!/usr/bin/env bash
# Sign a package on a Roku in Developer Mode: package.sh <app.zip> <out.pkg>.
# Roku signs only on a device, so this rekeys the device with the signing key
# (when ROKU_SIGN_KEY names a package signed with it), sideloads the zip with
# scripts/sideload.sh, runs the device's packager, and downloads the .pkg.
# Reads ROKU_HOST, ROKU_PASSWORD, ROKU_SIGN_PASSWORD, and optional
# ROKU_SIGN_KEY, ROKU_DEV_ID, and ROKU_DEPLOY_VIA from the environment or .env.
# Without ROKU_SIGN_KEY the device's current key signs (first package after
# genkey). With ROKU_DEV_ID the device's keyed developer ID must match it.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f .env ]; then set -a; . ./.env; set +a; fi
: "${ROKU_HOST:?set ROKU_HOST}"
: "${ROKU_PASSWORD:?set ROKU_PASSWORD}"
: "${ROKU_SIGN_PASSWORD:?set ROKU_SIGN_PASSWORD (the genkey password)}"
[ $# = 2 ] || { echo "usage: scripts/package.sh <app.zip> <out.pkg>" >&2; exit 2; }
zip=$1 out=$2
[ -f "$zip" ] || { echo "missing $zip" >&2; exit 1; }
if [ -n "${ROKU_SIGN_KEY:-}" ] && [ ! -s "$ROKU_SIGN_KEY" ]; then
    echo "ROKU_SIGN_KEY names a missing or empty file" >&2; exit 1
fi
case ${ROKU_DEV_ID:-} in *[!0-9a-fA-F]*) echo "ROKU_DEV_ID is not hex" >&2; exit 1 ;; esac
title=$(unzip -p "$zip" manifest | sed -n 's/^title=//p' | tr -d '\r')
major=$(unzip -p "$zip" manifest | sed -n 's/^major_version=//p' | tr -d '\r')
minor=$(unzip -p "$zip" manifest | sed -n 's/^minor_version=//p' | tr -d '\r')
case $title$major$minor in *[!A-Za-z0-9.\ ]*) echo "unexpected manifest title or version" >&2; exit 1 ;; esac

# Each step runs on this machine or through ROKU_DEPLOY_VIA. The passwords come
# first on stdin, one per line, so they never appear in a command line or log.
run() {
    local script
    printf -v script 'ROKU_HOST=%q\nDEV_ID=%q\nAPP_NAME=%q\n%s' \
        "$ROKU_HOST" "${ROKU_DEV_ID:-}" "$title/$major.$minor" "$1"
    if [ -n "${ROKU_DEPLOY_VIA:-}" ]; then $ROKU_DEPLOY_VIA "$script"; else bash -c "$script"; fi
}

common=$(cat <<'COMMON'
set -eu
umask 077
IFS= read -r pass
IFS= read -r sign
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
printf 'user = "rokudev:%s"\n' "$(printf %s "$pass" | sed 's/[\\"]/\\&/g')" > "$tmp/curlrc"
printf %s "$sign" > "$tmp/sign"
unset pass sign
post() {
    curl -sS --digest --connect-timeout 10 --max-time 120 -K "$tmp/curlrc" \
        -o "$tmp/response" -w '%{http_code}' "$@"
}
check_dev_id() {
    [ -n "$DEV_ID" ] || return 0
    actual=$(curl -sS --max-time 10 "http://$ROKU_HOST:8060/query/device-info" |
        sed -n 's:.*<keyed-developer-id>\(.*\)</keyed-developer-id>.*:\1:p')
    if [ "$actual" != "$DEV_ID" ]; then
        echo "the device is keyed with developer ID '$actual', not ROKU_DEV_ID" >&2; exit 1
    fi
}
COMMON
)

rekey=$(cat <<'REKEY'
cat > "$tmp/key.pkg"
code=$(post -F mysubmit=Rekey -F "passwd=<$tmp/sign" -F "archive=@$tmp/key.pkg" \
    "http://$ROKU_HOST/plugin_inspect")
[ "$code" = 200 ] || { echo "rekey failed: HTTP $code" >&2; exit 1; }
result=$(sed -n 's:.*<font color="red">\([^<]*\)</font>.*:\1:p' "$tmp/response" | head -n 1)
[ "$result" = "Success." ] || { echo "rekey failed: ${result:-unrecognized response}" >&2; exit 1; }
check_dev_id
echo "rekeyed $ROKU_HOST" >&2
REKEY
)

package=$(cat <<'PACKAGE'
check_dev_id
code=$(post -F mysubmit=Package -F "app_name=$APP_NAME" -F "passwd=<$tmp/sign" \
    -F "pkg_time=$(date +%s)000" "http://$ROKU_HOST/plugin_package")
[ "$code" = 200 ] || { echo "packaging failed: HTTP $code" >&2; exit 1; }
failed=$(sed -n 's:.*<font[^>]*>Failed\: \(.*\):\1:p' "$tmp/response" | head -n 1)
[ -z "$failed" ] || { echo "packaging failed: $failed" >&2; exit 1; }
path=$(sed -n 's:.*"pkgPath" *\: *"\([^"]*\)".*:\1:p' "$tmp/response" | head -n 1)
[ -n "$path" ] || path=$(sed -n 's:.*<a href="\(pkgs/[^".]*\.pkg\)">.*:\1:p' "$tmp/response" | head -n 1)
printf %s "$path" | grep -qE '^pkgs/+[^/]+\.pkg$' ||
    { echo "packaging failed: no package link in the response" >&2; exit 1; }
code=$(curl -sS --digest --connect-timeout 10 --max-time 120 -K "$tmp/curlrc" \
    -o "$tmp/out.pkg" -w '%{http_code}' "http://$ROKU_HOST/$path")
[ "$code" = 200 ] && [ -s "$tmp/out.pkg" ] || { echo "download failed: HTTP $code" >&2; exit 1; }
cat "$tmp/out.pkg"
PACKAGE
)

secrets() { printf '%s\n%s\n' "$ROKU_PASSWORD" "$ROKU_SIGN_PASSWORD"; }

if [ -n "${ROKU_SIGN_KEY:-}" ]; then
    { secrets; cat "$ROKU_SIGN_KEY"; } | run "$common
$rekey"
fi
scripts/sideload.sh "$zip"
mkdir -p "$(dirname "$out")"
secrets | run "$common
$package" > "$out.partial"
if [ "$(head -c 16 "$out.partial")" != "Roku Channel Pak" ]; then
    rm -f "$out.partial"; echo "packaging failed: the download is not a Roku package" >&2; exit 1
fi
mv "$out.partial" "$out"
echo "signed $out ($(wc -c < "$out" | tr -d ' ') bytes) for $title $major.$minor"
