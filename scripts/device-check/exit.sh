# Leaving the dev app between device-check sessions, sourced by
# scripts/device-check.sh and by test_device_check.py. Needs the caller's
# ecp, foreground, and die, and EXIT_TIMEOUT and EXIT_POLL in seconds.

# Roku OS 15.3 answers 202 (accepted) where earlier releases answer 200; 404
# means the dev app was not running. An accepted exit has finished once the
# dev app has left the foreground, which is polled for up to EXIT_TIMEOUT s;
# the caller's ownership checks then decide whether the run goes on.
exit_dev() {
    local code deadline
    code=$(ecp POST exit-app/dev)
    case $code in
    404) return 0 ;;
    200 | 202) ;;
    *) die "ECP exit-app/dev answered HTTP $code (needs Roku OS 13+, developer mode, and Control by mobile apps)" ;;
    esac
    deadline=$((SECONDS + EXIT_TIMEOUT))
    while [ "$(foreground | cut -d' ' -f1)" = dev ]; do
        [ "$SECONDS" -lt "$deadline" ] || die "the dev app was still in the foreground ${EXIT_TIMEOUT} s after ECP exit-app/dev answered HTTP $code"
        sleep "$EXIT_POLL"
    done
}
