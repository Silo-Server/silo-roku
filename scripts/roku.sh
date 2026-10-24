#!/usr/bin/env bash
# Drive the Roku over ECP (port 8060) and the developer installer.
# Reads ROKU_HOST, ROKU_PASSWORD, and optional ROKU_DEPLOY_VIA from .env.
#
#   roku.sh key Home Down Select   press remote keys in order
#   roku.sh text "query"           type text into the focused field
#   roku.sh launch [app-id] [k=v]  launch an app (default: dev) with optional params
#   roku.sh active                 print the foreground app
#   roku.sh query <path>           print an ECP query, e.g. device-info or apps
#   roku.sh screenshot <file.jpg>  save a screenshot of the dev app
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f .env ]; then set -a; . ./.env; set +a; fi
: "${ROKU_HOST:?set ROKU_HOST in .env}"

usage() { sed -n '5,10s/^# *//p' "$0" >&2; exit 2; }

# Run a shell script on the host that can reach the Roku. Stdin passes through.
remote() {
    local host_arg
    printf -v host_arg '%q' "$ROKU_HOST"
    local script="ROKU_HOST=$host_arg
$1"
    if [ -n "${ROKU_DEPLOY_VIA:-}" ]; then
        $ROKU_DEPLOY_VIA "$script"
    else
        bash -c "$script"
    fi
}

ecp_post() {
    local paths=() path
    for path in "$@"; do printf -v path '%q' "$path"; paths+=("$path"); done
    remote "set -eu
for p in ${paths[*]}; do
    code=\$(curl -sS -m 10 -o /dev/null -w '%{http_code}' -X POST \"http://\${ROKU_HOST}:8060/\$p\")
    case \"\$code\" in 2??) ;; *) { echo \"ECP \$p failed: HTTP \$code\" >&2; exit 1; }; esac
    sleep 0.3
done"
}

urlencode() { python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$1"; }

cmd=${1:-}
[ $# -gt 0 ] && shift
case "$cmd" in
key)
    [ $# -gt 0 ] || usage
    paths=()
    for key in "$@"; do paths+=("keypress/$(urlencode "$key")"); done
    ecp_post "${paths[@]}"
    ;;
text)
    [ $# -eq 1 ] || usage
    paths=()
    while IFS= read -r -n1 char; do
        [ -n "$char" ] || char=" "
        paths+=("keypress/Lit_$(urlencode "$char")")
    done < <(printf %s "$1")
    ecp_post "${paths[@]}"
    ;;
launch)
    app=${1:-dev}
    [ $# -gt 0 ] && shift
    query=""
    for param in "$@"; do
        query+="${query:+&}$(urlencode "${param%%=*}")=$(urlencode "${param#*=}")"
    done
    ecp_post "launch/$(urlencode "$app")${query:+?$query}"
    ;;
active)
    remote 'curl -sS -m 10 "http://${ROKU_HOST}:8060/query/active-app"' | sed -n 's/.*<app id="\([^"]*\)"[^>]*>\([^<]*\)<\/app>.*/\1 \2/p'
    ;;
query)
    [ $# -eq 1 ] || usage
    printf -v path '%q' "$1"
    remote "curl -sS -m 10 \"http://\${ROKU_HOST}:8060/query/\"$path"
    ;;
screenshot)
    [ $# -eq 1 ] || usage
    : "${ROKU_PASSWORD:?set ROKU_PASSWORD in .env}"
    # The installer only captures the sideloaded dev app. The password travels
    # over stdin and lives only in a private temporary curl config.
    tmp_out=$(mktemp)
    trap 'rm -f "$tmp_out"' EXIT
    printf '%s\n' "$ROKU_PASSWORD" | remote 'set -eu
umask 077
IFS= read -r pass
tmp=$(mktemp -d)
trap "rm -rf \"$tmp\"" EXIT
printf "user = \"rokudev:%s\"\n" "$(printf %s "$pass" | sed "s/[\\\\\"]/\\\\&/g")" > "$tmp/curlrc"
unset pass
curl -sS --digest -m 20 -K "$tmp/curlrc" -F mysubmit=Screenshot -F archive= -F passwd= \
    -o "$tmp/page" "http://$ROKU_HOST/plugin_inspect"
image=$(grep -oE "pkgs/dev\.(jpg|png)\?time=[0-9]+" "$tmp/page" | head -n 1)
[ -n "$image" ] || { echo "screenshot failed: is the dev app installed?" >&2; exit 1; }
curl -sS --digest -m 20 -K "$tmp/curlrc" -f "http://$ROKU_HOST/$image"' > "$tmp_out"
    mv "$tmp_out" "$1"
    trap - EXIT
    echo "$1"
    ;;
*)
    usage
    ;;
esac
