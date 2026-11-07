#!/usr/bin/env bash
# Build the Japanese and Simplified Chinese UI fonts (decisions D10 and D20 of
# the translation program; docs/spec.md "Languages"): one weight of Noto Sans
# JP and Noto Sans SC, subset to the characters the catalog shows in that
# language (i18n-charsets/<folder>.txt, written by scripts/sync-translations)
# and the language's own name for the App language picker, which it must draw,
# plus what the source has of the ranges in EXTRA. SceneGraph has no font fallback, so in
# those languages these fonts replace Inter everywhere (theme.fontUri). A language
# ships only once it has strings, and only a shipped one gets a charset; without one
# its font is removed (and the license, when no font is left), since nothing could
# apply that language.
#
#   scripts/subset-cjk-fonts.sh            rebuild fonts/NotoSans{JP,SC}-Medium.ttf
#   scripts/subset-cjk-fonts.sh --check    fail when a charset or font changed
#                                          since the last rebuild, or a font is
#                                          left without its charset (no network)
#
# Rerun after every sync that adds, changes or removes i18n-charsets/ja.txt or zh_Hans.txt, and
# commit fonts/ with it. The sources are Google Fonts' TrueType builds (not the
# CFF .otf of notofonts/noto-cjk, which Roku has not been shown to draw),
# downloaded at a pinned google/fonts commit into a fresh temporary directory
# and untrusted until they match the pinned sha256s. fontTools comes from PyPI
# as the hash-pinned wheel scripts/subset-fonts.sh uses, in a throwaway
# virtualenv. The output is deterministic for the same pins and charsets.
set -euo pipefail
cd "$(dirname "$0")/.."

GOOGLE_FONTS_COMMIT=38411257417e616c5d4daa1b9e91a3dbcebe1c2e
BASE_URL=https://raw.githubusercontent.com/google/fonts/$GOOGLE_FONTS_COMMIT/ofl
JP_SOURCE=notosansjp/NotoSansJP%5Bwght%5D.ttf
JP_SHA256=c2f3b4d463500a2ddcd3849cded1fceeb9fd6d1c32e6cbecd568453ba50fc68f
SC_SOURCE=notosanssc/NotoSansSC%5Bwght%5D.ttf
SC_SHA256=a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da
LICENSE_SOURCE=notosansjp/OFL.txt
LICENSE_SHA256=1c05c68c34f9708415aada51f17e1b0092d2cea709bf4a94cd38114f9e73d7d9
FONTTOOLS_VERSION=4.67.0
FONTTOOLS_SHA256=4304f03ed7f4ba000a8dcc941ad854bfa52e2f3b6112b8f099b6f431cf98e701
# One weight per language: Medium, between Inter's Regular body text and its
# SemiBold titles. Every theme.textStyle weight draws in it.
WEIGHT=500
WEIGHT_NAME=Medium
# folder, font file stem, source path, source sha256, the language's own name
LANGUAGES=(
    "ja NotoSansJP $JP_SOURCE $JP_SHA256 日本語"
    "zh_Hans NotoSansSC $SC_SOURCE $SC_SHA256 简体中文"
)
# What server metadata may hold beyond the catalog's characters, as far as
# the source has it: Latin-1 and Latin Extended-A (most European names),
# general punctuation, currency signs, letterlike symbols (™), arrows, the
# minus sign, and the replacement character. Greek, Cyrillic, and
# Vietnamese, which Inter draws, are left out for size (docs/spec.md 5.9).
EXTRA=$(printf '%b' "$(printf '\\U%08x' $(seq 32 126) $(seq 160 383) $(seq 8192 8303) $(seq 8352 8399) $(seq 8448 8527) $(seq 8592 8595) 8722 65533)")
RECORD=fonts/SOURCE-cjk

sha256() {
    if command -v sha256sum > /dev/null; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -d' ' -f1
}

if [ "${1:-}" = "--check" ]; then
    [ -f "$RECORD" ] || { echo "missing $RECORD; run scripts/subset-cjk-fonts.sh" >&2; exit 1; }
    status=0
    for entry in "${LANGUAGES[@]}"; do
        read -r folder stem _ <<< "$entry"
        if [ ! -f "i18n-charsets/$folder.txt" ]; then
            if [ -f "fonts/$stem-$WEIGHT_NAME.ttf" ]; then
                echo "fonts/$stem-$WEIGHT_NAME.ttf ships but $folder does not (no i18n-charsets/$folder.txt); run scripts/subset-cjk-fonts.sh and commit fonts/" >&2
                status=1
            fi
            continue
        fi
        for file in "i18n-charsets/$folder.txt" "fonts/$stem-$WEIGHT_NAME.ttf"; do
            want=$(sed -n "s|^  $file  sha256 \([0-9a-f]*\).*|\1|p" "$RECORD")
            if [ ! -f "$file" ] || [ "$(sha256 "$file")" != "$want" ]; then
                echo "$file changed since the CJK fonts were built; run scripts/subset-cjk-fonts.sh and commit fonts/" >&2
                status=1
            fi
        done
    done
    [ "$status" = 0 ] && echo "CJK fonts match i18n-charsets/"
    exit "$status"
fi

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
mkdir "$work/download"

fetch() {
    local path=$1 want=$2 out=$work/download/$(basename "$1")
    curl -fsSL --proto '=https' --retry 3 --connect-timeout 15 --max-time 600 -o "$out" "$BASE_URL/$path"
    local got
    got=$(sha256 "$out")
    if [ "$got" != "$want" ]; then
        echo "$path has sha256 $got, not the pinned $want." >&2
        echo "To move to a new google/fonts commit, review the fonts, then bump the pins here." >&2
        exit 1
    fi
    printf '%s' "$out"
}

outputs=()
building=()
for entry in "${LANGUAGES[@]}"; do
    read -r folder stem _ <<< "$entry"
    if [ -f "i18n-charsets/$folder.txt" ]; then
        building+=("$entry")
    else
        rm -f "fonts/$stem-$WEIGHT_NAME.ttf"
        outputs+=("  i18n-charsets/$folder.txt  absent: $folder does not ship, so fonts/$stem-$WEIGHT_NAME.ttf is not built")
    fi
done

if [ "${#building[@]}" = 0 ]; then
    rm -f fonts/OFL-Noto.txt
else
    python3 -m venv "$work/venv"
    printf 'fonttools==%s --hash=sha256:%s\n' "$FONTTOOLS_VERSION" "$FONTTOOLS_SHA256" > "$work/requirements.txt"
    "$work/venv/bin/pip" install --quiet --disable-pip-version-check --no-deps --only-binary :all: \
        --require-hashes -r "$work/requirements.txt"
    license=$(fetch "$LICENSE_SOURCE" "$LICENSE_SHA256")
    cp "$license" fonts/OFL-Noto.txt
fi
for entry in ${building[@]+"${building[@]}"}; do
    read -r folder stem path want name <<< "$entry"
    source=$(fetch "$path" "$want")
    charset=i18n-charsets/$folder.txt
    printf '%s%s' "$(cat "$charset")" "$name" > "$work/$folder.required"
    printf '%s' "$EXTRA" > "$work/$folder.extra"
    out=fonts/$stem-$WEIGHT_NAME.ttf
    "$work/venv/bin/python" -I scripts/cjk-font.py "$source" "$WEIGHT" "$work/$folder.required" "$work/$folder.extra" "$out"
    outputs+=("  $charset  sha256 $(sha256 "$charset")")
    outputs+=("  $out  sha256 $(sha256 "$out")  $(wc -c < "$out" | tr -d ' ') bytes")
done

cat > "$RECORD" << EOF
fonts: Noto Sans JP and Noto Sans SC (Google Fonts' variable TrueType builds), one weight each ($WEIGHT_NAME, wght $WEIGHT)
license: SIL Open Font License 1.1, Reserved Font Name "Source" (fonts/OFL-Noto.txt is google/fonts' ofl/notosansjp/OFL.txt; notosanssc's is the same text)
source: $BASE_URL/$JP_SOURCE and $BASE_URL/$SC_SOURCE
source sha256: JP $JP_SHA256, SC $SC_SHA256
instanced and subset with: fontTools $FONTTOOLS_VERSION (PyPI wheel sha256 $FONTTOOLS_SHA256), scripts/cjk-font.py
characters: i18n-charsets/<folder>.txt and the language's own name (required), and what the source has of U+0020-007E, U+00A0-017F, U+2000-206F, U+20A0-20CF, U+2100-214F, U+2190-2193, U+2212 and U+FFFD; U+200A is not in the sources (theme.tracked skips CJK)
modified version: instanced to one weight and subset; the family keeps its Noto name, which the license does not reserve
generated by: scripts/subset-cjk-fonts.sh (check: scripts/subset-cjk-fonts.sh --check)
files:
$(printf '%s\n' "${outputs[@]}")
EOF
cat "$RECORD"
