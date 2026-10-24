#!/usr/bin/env bash
# Device lane (implementation plan sections 1, 7, 8, and 9.2): cold launches
# timed by the port 8085 beacon report, ECP performance snapshots, and the
# deep-link matrix. Writes raw files and summary.md, rows for
# docs/hardware-evidence.md, to --out. Reads ROKU_HOST, ROKU_DEPLOY_VIA,
# ROKU_IDLE_INPUT, and ROKU_IDLE_CHECK from .env; see the README's Device check.
#
#   device-check.sh [--launches N] [--await-reboot | --no-reboot] [--perf]
#                   [--deeplinks] [--ids FILE] [--out DIR]
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -f .env ]; then set -a; . ./.env; set +a; fi
: "${ROKU_HOST:?set ROKU_HOST in .env}"
idle_input=${ROKU_IDLE_INPUT:-tvinput.hdmi1}

usage() { sed -n '8,9s/^# *//p' "$0" >&2; exit 2; }

launches=10 reboot=none perf=0 deeplinks=0 ids=.env.deeplinks out=""
while [ $# -gt 0 ]; do
    case $1 in
    --launches) [ $# -ge 2 ] && [[ $2 =~ ^[0-9]+$ ]] || usage; launches=$((10#$2)); shift 2 ;;
    --await-reboot) reboot=awaited; shift ;;
    --no-reboot) reboot=none; shift ;;
    --perf) perf=1; shift ;;
    --deeplinks) deeplinks=1; shift ;;
    --ids) [ $# -ge 2 ] || usage; ids=$2; shift 2 ;;
    --out) [ $# -ge 2 ] || usage; out=$2; shift 2 ;;
    *) usage ;;
    esac
done
out=${out:-.local/evidence/silo-roku/device-check-$(date +%Y%m%d-%H%M%S)}
[ ! -e "$out" ] || [ -z "$(ls -A "$out")" ] || { echo "device-check: $out is not empty" >&2; exit 1; }

EXIT_TIMEOUT=15      # after exit-app, for the dev app to leave the foreground
EXIT_POLL=0.5
BACKLOG_WAIT=2       # the console replays recent output to a new connection
LAUNCH_TIMEOUT=30    # for AppLaunchComplete (certification allows 15 s)
HOLD=3               # after AppLaunchComplete, for the app's launch logs
REPORT_WAIT=3        # after exit-app, for Roku's beacon report
SNAPSHOT_WAIT=5      # on Home before the --perf snapshots
DEEPLINK_WAIT=10     # after a deep link, for the routing lines
REBOOT_TIMEOUT=600
REBOOT_SETTLE=30
LAUNCHED='\[beacon\.signal\] \|AppLaunchComplete -+> Duration\('
READY="$LAUNCHED|\\[beacon\\.signal\\] \\|AppDialogInitiate"
# The debug console serves one client: a second connection is refused or
# gets nothing.
CONSOLE_BUSY="It serves one connection at a time: close any other console (npm run console, telnet, an IDE debugger) and run again."
# A content ID that exists nowhere, for the "invalid or inaccessible" row.
INVALID_ID=00000000-0000-4000-8000-000000000000

py() { python3 -I -B scripts/device-check/device_check.py "$@"; }
note() { echo "device-check: $*" >&2; }
die() { note "$*"; exit 1; }
# exit_dev: leave the dev app, waiting until it has left the foreground.
. scripts/device-check/exit.sh

tmp=$(mktemp -d)
cap_pid="" started=""
# A run that stops early still summarizes what it saved.
cleanup() {
    [ -z "$cap_pid" ] || capture_stop
    rm -rf "$tmp"
    if [ -n "$started" ] && [ ! -f "$out/summary.md" ]; then
        summarize > /dev/null && note "summarized the runs that finished in $out/summary.md"
    fi
}
summarize() { DEVICE_CHECK_SCRUB=${scrub:-} py summarize "$out" > "$out/summary.md" && cat "$out/summary.md"; }
trap cleanup EXIT

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

# ecp METHOD PATH [FILE]: send one ECP request and print its HTTP status (000
# when the device did not answer). FILE receives the body.
ecp() {
    local path reply body=""
    printf -v path '%q' "$2"
    reply=$(remote "tmp=\$(mktemp)
code=\$(curl -sS -m 15 -X $1 -o \"\$tmp\" -w '%{http_code}' \"http://\${ROKU_HOST}:8060/\"$path 2>/dev/null) || code=000
echo \"\$code\"
cat \"\$tmp\"
rm -f \"\$tmp\"" < /dev/null 8>&-) || reply=000
    [[ $reply == *$'\n'* ]] && body=${reply#*$'\n'}
    [ -z "${3:-}" ] || printf '%s\n' "$body" > "$3"
    printf '%s\n' "${reply%%$'\n'*}"
}

# step SESSION STEP VALUE: one line of steps.tsv, which summarize reads.
step() { printf '%s\t%s\t%s\n' "$1" "$2" "$3" >> "$out/steps.tsv"; }

urlencode() { python3 -I -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$1"; }

# Streams the console to stdout until stdin closes, for at most 15 minutes.
# Python 3 on the relay host, as for sideloading; fd 3 is the control pipe.
CAPTURE=$(cat <<'CAPTURE'
exec 3<&0
python3 - "$ROKU_HOST" <<'PY'
import os, select, socket, sys, time
sock = socket.create_connection((sys.argv[1], 8085), timeout=10)
end = time.monotonic() + 900
out = sys.stdout.buffer
while time.monotonic() < end:
    ready = select.select([sock, 3], [], [], 1)[0]
    if 3 in ready and not os.read(3, 4096):
        break
    if sock in ready:
        data = sock.recv(65536)
        if not data:
            break
        out.write(data)
        out.flush()
PY
CAPTURE
)

capture_start() {
    rm -f "$tmp/capture.ctl"
    mkfifo "$tmp/capture.ctl"
    remote "$CAPTURE" < "$tmp/capture.ctl" > "$1" 2> "$tmp/capture.err" &
    cap_pid=$!
    exec 8> "$tmp/capture.ctl"
    sleep "$BACKLOG_WAIT"
    kill -0 "$cap_pid" 2> /dev/null || die "could not read the console on port 8085 ($(console_error)). $CONSOLE_BUSY"
}

console_error() { tail -n 1 "$tmp/capture.err" 2> /dev/null || true; }

capture_stop() {
    local i
    exec 8>&-
    for i in 1 2 3 4 5 6 7 8 9 10; do
        kill -0 "$cap_pid" 2> /dev/null || break
        sleep 0.5
    done
    pkill -P "$cap_pid" 2> /dev/null || true
    kill "$cap_pid" 2> /dev/null || true
    wait "$cap_pid" 2> /dev/null || true
    cap_pid=""
}

# wait_for FILE OFFSET PATTERN: true once PATTERN appears after OFFSET, false
# after the launch timeout or when the capture ends.
wait_for() {
    local deadline=$((SECONDS + LAUNCH_TIMEOUT))
    while [ "$SECONDS" -lt "$deadline" ]; do
        grep -qE "$3" < <(tail -c +"$(($2 + 1))" "$1") && return 0
        kill -0 "$cap_pid" 2> /dev/null || return 1
        sleep 0.5
    done
    return 1
}

# foreground [--preflight]: print the verdict for the TV's current state
# (home, dev, input ID, or refuse REASON). Pre-flight also reads power mode,
# developer mode, and the media player.
foreground() {
    local device=- player=-
    ecp GET query/active-app "$tmp/active-app.xml" > /dev/null
    if [ "${1:-}" = --preflight ]; then
        device=$tmp/device-info.xml player=$tmp/media-player.xml
        [ "$(ecp GET query/device-info "$device")" = 200 ] || die "the Roku did not answer ECP query/device-info"
        ecp GET query/media-player "$player" > /dev/null
    fi
    py foreground "$tmp/active-app.xml" "$device" "$player" "$idle_input"
}

# Proceed only from Roku Home or the dev app (assumption A-10). Pre-flight may
# leave the one idle-checked input with Home; later checks never leave anything.
preflight() {
    local verdict state
    verdict=$(foreground --preflight)
    case $verdict in
    home*) idle_by="the TV showed Roku Home" ;;
    dev*) idle_by="the TV showed the dev app" ;;
    input*)
        [ -n "${ROKU_IDLE_CHECK:-}" ] || die "the TV is on ${verdict#input }; set ROKU_IDLE_CHECK in .env to check its device is idle"
        remote "$ROKU_IDLE_CHECK" < /dev/null > "$tmp/idle.txt" 2> /dev/null || die "the idle check failed; not leaving ${verdict#input }"
        state=$(py idle "$tmp/idle.txt") || die "the device on ${verdict#input } reports \"$state\", not Idle; not leaving it"
        [ "$(ecp POST keypress/Home)" = 200 ] || die "ECP keypress/Home failed (Control by mobile apps must be Permissive)"
        sleep 3
        verdict=$(foreground --preflight)
        [ "${verdict%% *}" = home ] || die "Home did not bring up Roku Home: $verdict"
        idle_by="the TV showed ${idle_input}; its device reported Idle, so Home was pressed"
        ;;
    *) die "${verdict#refuse }" ;;
    esac
}

still_idle() {
    local verdict
    verdict=$(foreground)
    case $verdict in
    home* | dev*) ;;
    *) die "stopping: the TV left Roku Home during the run (${verdict#* })" ;;
    esac
}

# session NAME WAIT ECP_PATH [COMMAND...]: from Home, launch the dev app with
# ECP_PATH while capturing the console, wait for the WAIT pattern, run
# COMMAND, exit the app, and keep the console from the launch on as NAME.log.
# COMMAND can read cap_file and cap_offset.
session() {
    local name=$1 wait=$2 path=$3
    shift 3
    exit_dev
    still_idle
    cap_file=$tmp/console.log
    capture_start "$cap_file"
    cap_offset=$(($(wc -c < "$cap_file")))
    step "$name" launch "$(ecp POST "$path")"
    if ! wait_for "$cap_file" "$cap_offset" "$wait"; then
        [ -s "$cap_file" ] || die "the console on port 8085 sent nothing. $CONSOLE_BUSY"
        note "$name: no launch beacon within ${LAUNCH_TIMEOUT} s"
    fi
    sleep "$HOLD"
    [ $# -eq 0 ] || "$@"
    exit_dev
    sleep "$REPORT_WAIT"
    capture_stop
    tail -c +$((cap_offset + 1)) "$cap_file" > "$out/$name.log"
}

read_fwbeacons() { ecp GET query/fwbeacons "$out/$1-fwbeacons.xml" > /dev/null; }

snapshots() {
    local name path
    sleep "$SNAPSHOT_WAIT"
    while read -r name path; do
        step perf "$name" "$(ecp GET "$path" "$out/$name.xml")"
    done << 'PATHS'
chanperf query/chanperf
r2d2-bitmaps query/r2d2-bitmaps
sgnodes-count query/sgnodes/all?count_only=true
sgnodes-sizes query/sgnodes/all?count_only=true&sizes=true
graphics-frame-rate query/graphics-frame-rate
PATHS
}

# after_deeplink NAME: record where the app is once the link has settled.
after_deeplink() {
    sleep "$DEEPLINK_WAIT"
    step "$1" after "$(foreground | cut -d' ' -f1)"
}

send_input() {
    step "$1" input-offset "$(($(wc -c < "$cap_file") - cap_offset))"
    step "$1" input "$(ecp POST "input?$2")"
    after_deeplink "$1"
}

await_reboot() {
    local before now down=0 deadline=$((SECONDS + REBOOT_TIMEOUT))
    before=$(py uptime "$tmp/device-info.xml")
    note "ECP cannot restart the Roku: restart it now (Settings > System > Power > System restart)."
    note "waiting up to $((REBOOT_TIMEOUT / 60)) minutes for it to come back"
    while :; do
        [ "$SECONDS" -lt "$deadline" ] || die "the Roku did not restart within $((REBOOT_TIMEOUT / 60)) minutes"
        sleep 5
        if [ "$(ecp GET query/device-info "$tmp/device-info.xml")" != 200 ]; then
            down=1
            continue
        fi
        now=$(py uptime "$tmp/device-info.xml")
        if [ -n "$before" ] && [ -n "$now" ]; then
            [ "$now" -lt "$before" ] && break
        elif [ "$down" = 1 ]; then
            break
        fi
    done
    note "the Roku is back; waiting ${REBOOT_SETTLE} s"
    sleep "$REBOOT_SETTLE"
}

# deeplink_id TYPE: the content ID from DEEPLINK_<TYPE>, or nothing.
deeplink_id() {
    local var
    var=DEEPLINK_$(printf %s "$1" | tr '[:lower:]' '[:upper:]')
    printf %s "${!var:-}"
}

deeplink_ids() {
    local type id
    # The coordinator's gitignored file of DEEPLINK_<TYPE>=<content ID> lines.
    if [ -f "$ids" ]; then . "$ids"; fi
    for type in movie episode series season; do
        id=$(deeplink_id "$type")
        [ -z "$id" ] || scrub+="$id"$'\n'
    done
    [ -n "$scrub" ] || die "no deep-link IDs: set DEEPLINK_MOVIE, DEEPLINK_EPISODE, DEEPLINK_SERIES, and DEEPLINK_SEASON in $ids"
}

deeplink_matrix() {
    local type id query
    for type in movie episode series season invalid; do
        if [ "$type" = invalid ]; then
            id=$INVALID_ID
        else
            id=$(deeplink_id "$type")
        fi
        if [ -z "$id" ]; then
            step "deeplink-$type" skipped "no ID"
            continue
        fi
        # The made-up ID is tried as a movie.
        query="contentId=$(urlencode "$id")&mediaType=${type/invalid/movie}"
        note "deep link: $type via launch"
        session "deeplink-$type-launch" "$READY" "launch/dev?$query" after_deeplink "deeplink-$type-launch"
        note "deep link: $type via input"
        session "deeplink-$type-input" "$READY" launch/dev send_input "deeplink-$type-input" "$query"
    done
}

scrub=""
[ "$deeplinks" = 0 ] || deeplink_ids

preflight
[ "$(ecp GET query/apps "$tmp/apps.xml")" = 200 ] || die "the Roku did not answer ECP query/apps"
py facts "$tmp/device-info.xml" "$tmp/apps.xml" > /dev/null || die "no dev app is installed; sideload one first"
if [ "$reboot" = awaited ]; then
    await_reboot
    preflight
    ecp GET query/apps "$tmp/apps.xml" > /dev/null
fi

umask 077
mkdir -p "$out"
: > "$out/steps.tsv"
py facts "$tmp/device-info.xml" "$tmp/apps.xml" > "$out/device.json" || true
cat > "$out/meta.txt" << META
date=$(date +%F)
launches=$launches
reboot=$reboot
perf=$perf
deeplinks=$deeplinks
foreground=$idle_by
timeout=$LAUNCH_TIMEOUT
exit_timeout=$EXIT_TIMEOUT
snapshot_wait=$((HOLD + SNAPSHOT_WAIT))
META
started=1
note "writing to $out"

if [ "$launches" -gt 0 ]; then
    track=$(ecp POST fwbeacons/track/dev)
    step launches fwbeacons-track "$track"
    for i in $(seq 1 "$launches"); do
        run=launch-$(printf %02d "$i")
        note "cold launch $i of $launches"
        if [ "$track" = 200 ]; then
            session "$run" "$LAUNCHED" launch/dev read_fwbeacons "$run"
        else
            session "$run" "$LAUNCHED" launch/dev
        fi
    done
    [ "$track" != 200 ] || ecp POST fwbeacons/untrack > /dev/null
fi
if [ "$perf" = 1 ]; then
    note "snapshots"
    session perf "$LAUNCHED" launch/dev snapshots
fi
if [ "$deeplinks" = 1 ]; then
    deeplink_matrix
fi

summarize
note "raw files and summary.md are in $out; the TV shows $(foreground | cut -d' ' -f1)"
