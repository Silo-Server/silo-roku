#!/usr/bin/env bash
# Upload a package (default out/silo-roku.zip) to a Roku in Developer Mode,
# replacing the dev app: sideload.sh [package.zip], a path from the repo root.
# Reads ROKU_HOST, ROKU_PASSWORD, and optional ROKU_DEPLOY_VIA from .env.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f .env ]; then set -a; . ./.env; set +a; fi
: "${ROKU_HOST:?set ROKU_HOST in .env}"
: "${ROKU_PASSWORD:?set ROKU_PASSWORD in .env}"
zip=${1:-out/silo-roku.zip}
[ -f "$zip" ] || { echo "missing $zip; build it first (npm run build)" >&2; exit 1; }

# The uploader reads the password from the first stdin line and the zip from the
# rest, so the password never appears in a command line or log.
upload=$(cat <<'UPLOAD'
set -eu
umask 077
IFS= read -r pass
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cat > "$tmp/app.zip"
printf 'user = "rokudev:%s"\n' "$(printf %s "$pass" | sed 's/[\\"]/\\&/g')" > "$tmp/curlrc"
unset pass
http_code=$(curl -sS --digest --connect-timeout 10 --max-time 90 -K "$tmp/curlrc" \
    -F mysubmit=Install -F "archive=@$tmp/app.zip" -o "$tmp/response" \
    -w '%{http_code}' "http://$ROKU_HOST/plugin_install")
if [ "$http_code" != 200 ]; then echo "install failed: HTTP $http_code" >&2; exit 1; fi
python3 - "$tmp/response" "$tmp/app.zip" "$ROKU_HOST" <<'VERIFY'
import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

response, archive, host = sys.argv[1:]
html = open(response).read()

def fail(message):
    print("sideload failed: " + message, file=sys.stderr)
    sys.exit(1)

if re.search(r"swup_failed\s*=\s*true", html):
    fail("the developer installer requires a software update check")
match = re.search(r"JSON\.parse\('((?:\\.|[^'])*)'\)", html)
if not match:
    fail("unrecognized installer response; cannot verify upload")
# Decode the JavaScript string containing the installer's JSON payload.
payload = re.sub(r"\\([\\'])", r"\1", match.group(1))
try:
    messages = json.loads(payload).get("messages") or []
except (ValueError, TypeError):
    fail("invalid installer status payload")
for message in messages:
    print(message.get("type", "unknown") + ": " + message.get("text", "").strip())
if not messages:
    fail("installer returned no upload status")
if any(message.get("type") == "error" for message in messages):
    fail("the developer installer rejected the package")

with zipfile.ZipFile(archive) as package:
    manifest = dict(line.split("=", 1) for line in package.read("manifest").decode().splitlines()
                    if "=" in line and not line.startswith("#"))
version = ".".join(manifest[key].strip() for key in ("major_version", "minor_version", "build_version"))
base = "http://" + host + ":8060"

def query(path):
    with urllib.request.urlopen(base + path, timeout=5) as result:
        return ET.fromstring(result.read())

def installed():
    return any(app.get("id") == "dev" and app.get("version") == version
               and app.text == manifest["title"].strip() for app in query("/query/apps"))

# HTTP 200 and "Application Received" only prove upload, not installation.
try:
    for attempt in range(10):
        if installed():
            break
        time.sleep(1)
    else:
        fail("expected dev app is absent from /query/apps (including after an install timeout)")
    active = query("/query/active-app").find("app")
    if active is None or active.get("id") != "dev":
        request = urllib.request.Request(base + "/launch/dev", data=b"", method="POST")
        with urllib.request.urlopen(request, timeout=10) as result:
            if result.status != 200:
                fail("ECP could not launch the dev app")
    for attempt in range(10):
        active = query("/query/active-app").find("app")
        if active is not None and active.get("id") == "dev":
            # A crashed app can briefly appear active; require it to stay active.
            time.sleep(2)
            active = query("/query/active-app").find("app")
            if active is not None and active.get("id") == "dev":
                print("Verified installed and active: dev / " + manifest["title"].strip() + " / " + version)
                sys.exit(0)
        time.sleep(1)
    fail("dev app did not remain active; inspect npm run console")
except (OSError, ET.ParseError) as error:
    fail("ECP verification failed: " + str(error))
VERIFY
UPLOAD
)
# Pass only the host in the remote command; credentials and package use stdin.
printf -v host_arg '%q' "$ROKU_HOST"
upload="ROKU_HOST=$host_arg
$upload"

if [ -n "${ROKU_DEPLOY_VIA:-}" ]; then
    { printf '%s\n' "$ROKU_PASSWORD"; cat "$zip"; } | $ROKU_DEPLOY_VIA "$upload"
else
    { printf '%s\n' "$ROKU_PASSWORD"; cat "$zip"; } | bash -c "$upload"
fi
