#!/usr/bin/env bash
# Grep the built package for code the client must never ship and for required
# manifest keys (implementation plan section 8). Checks out/silo-roku.zip unless
# another zip or a staged directory is given.
set -euo pipefail
cd "$(dirname "$0")/.."
target=${1:-out/silo-roku.zip}

if [ -d "$target" ]; then
    root=$target
elif [ -f "$target" ]; then
    root=$(mktemp -d)
    trap 'rm -rf "$root"' EXIT
    unzip -q "$target" -d "$root"
else
    echo "missing $target; run npm run build" >&2
    exit 1
fi

failed=0
report() {
    echo "hygiene: $1" >&2
    printf '%s\n' "$2" >&2
    failed=1
}

# Case-insensitive ERE search of the package; prints ./path:line:text matches.
search() {
    local status=0
    (cd "$root" && grep -rIinE "$@" .) || status=$?
    [ "$status" -le 1 ] || { echo "hygiene: grep failed" >&2; exit 2; }
}

ban() {
    local hits
    hits=$(search "$2")
    [ -z "$hits" ] || report "$1" "$hits"
}

ban "v1 API, which retires at Silo 1.0" '/api/v1([^0-9]|$)'
ban "InitClientCertificates, deprecated by Roku" 'InitClientCertificates'
ban "observeFieldScoped; use observeFieldScopedEx with a port" 'observeFieldScoped[[:space:]]*\('
ban "observeFieldScopedEx with a callback name; pass a port" 'observeFieldScopedEx[[:space:]]*\([^,)]*,[[:space:]]*"'

# A print statement starts a line or follows ":", "then", or "else"; "?" is its
# shorthand. Full-line comments are skipped. Only the logger may print.
print_allowed=(
    '^\./source/util/log\.brs:'
)
hits=$(search --include='*.brs' --include='*.xml' '(^|:|[[:space:]](then|else))[[:space:]]*(print|\?)([^[:alnum:]_]|$)')
hits=$(printf '%s\n' "$hits" |
    grep -viE "^[^:]+:[0-9]+:[[:space:]]*('|rem([[:space:]]|$))" |
    grep -vE -f <(printf '%s\n' "${print_allowed[@]}") || true)
[ -z "$hits" ] || report "bare print outside the logger (source/util/log)" "$hits"

# Manifest attribute names are case-sensitive on Roku, so these match exactly.
if [ -f "$root/manifest" ]; then
    missing=()
    for key in rsg_version=1.3 supports_input_launch=1 requires_mkv=1 ui_resolutions=fhd; do
        grep -qxF "$key" "$root/manifest" || missing+=("  $key")
    done
    grep -qE '^bs_const=.' "$root/manifest" || missing+=("  bs_const=<flags>")
    [ "${#missing[@]}" = 0 ] || report "manifest lacks required keys" "$(printf '%s\n' "${missing[@]}")"
else
    report "package has no manifest" "  $target"
fi

[ "$failed" = 0 ] || exit 1
echo "hygiene: $target passed"
