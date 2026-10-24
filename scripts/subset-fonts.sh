#!/usr/bin/env bash
# Rebuild fonts/ from the official Inter release (plan section 3): the static
# Regular, Medium, SemiBold, and Bold TTFs subset to Latin, Latin Extended,
# Greek, Cyrillic, and Vietnamese; the timecode variant Inter-SemiBold-Tabular
# (scripts/tabular-font.py); fonts/OFL.txt; and fonts/SOURCE.
#
#   scripts/subset-fonts.sh [Inter-<version>.zip]
#
# Without an argument the release zip is downloaded into a fresh temporary
# directory. Either way it is untrusted until it matches the pinned sha256, and
# only the four TTFs and LICENSE.txt are extracted from it. fontTools comes from
# PyPI as a hash-pinned wheel in a throwaway virtualenv. The subset is
# deterministic, so rerunning with the same pins reproduces the committed files.
set -euo pipefail
cd "$(dirname "$0")/.."

# rsms/inter publishes no digest for the asset; this is the sha256 of the zip
# downloaded on 2026-10-22.
INTER_VERSION=4.1
INTER_URL=https://github.com/rsms/inter/releases/download/v$INTER_VERSION/Inter-$INTER_VERSION.zip
INTER_SHA256=9883fdd4a49d4fb66bd8177ba6625ef9a64aa45899767dde3d36aa425756b11e
FONTTOOLS_VERSION=4.67.0
FONTTOOLS_SHA256=4304f03ed7f4ba000a8dcc941ad854bfa52e2f3b6112b8f099b6f431cf98e701
WEIGHTS=(Regular Medium SemiBold Bold)
# Timecodes use the tab label's weight.
TABULAR_WEIGHT=SemiBold

# Unicode blocks kept: Basic Latin and Latin-1; Latin Extended-A and -B; IPA,
# spacing modifiers, and combining marks (Vietnamese and decomposed text); Greek
# and Coptic; Cyrillic and its supplement; Latin Extended Additional
# (Vietnamese); general punctuation (including the hair space theme.tracked
# uses); currency; letterlike symbols; basic arrows; minus; Latin Extended-C
# and -D; BOM and the replacement character.
UNICODES=U+0000-036F,U+0370-03FF,U+0400-052F,U+1E00-1EFF,U+2000-206F,U+20A0-20CF,U+2100-214F,U+2190-2193,U+2212,U+2C60-2C7F,U+A720-A7FF,U+FEFF,U+FFFD
# The license name records (IDs 13 and 14) stay with the copyright, as the OFL
# asks. The .notdef box is kept so a missing glyph is visible rather than
# blank. Hinting is dropped: Roku scales the FHD layout and the TTFs carry none
# worth the bytes. Layout features are pyftsubset's defaults; Label cannot turn
# on tnum, so timecodes use the variant below.
COMMON_OPTIONS=(--name-IDs+=13,14 --notdef-outline --no-hinting)
SUBSET_OPTIONS=(--unicodes="$UNICODES" "${COMMON_OPTIONS[@]}")
# The timecode variant keeps only what elapsed time, time left, and end time
# need: space, hyphen, period, the slash between position and runtime
# ("0:23 / 22:00"), digits, colon, minus, the letters of AM/PM and am/pm
# (Roku's asTimeStringLoc writes "11:25 pm"), and the no-break and narrow
# no-break spaces localized times may put before them. Its digits are already
# tabular, so it drops the layout tables and nothing can kern or swap them.
TABULAR_UNICODES=U+0020,U+002D-003A,U+0041,U+004D,U+0050,U+0061,U+006D,U+0070,U+00A0,U+202F,U+2212
TABULAR_OPTIONS=(--unicodes="$TABULAR_UNICODES" --drop-tables+=GDEF,GPOS,GSUB "${COMMON_OPTIONS[@]}")

sha256() {
    if command -v sha256sum > /dev/null; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -d' ' -f1
}

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
mkdir "$work/download" "$work/extract"

zip=${1:-}
if [ -z "$zip" ]; then
    zip=$work/download/Inter-$INTER_VERSION.zip
    curl -fsSL --proto '=https' --retry 3 --connect-timeout 15 --max-time 300 -o "$zip" "$INTER_URL"
fi
actual=$(sha256 "$zip")
if [ "$actual" != "$INTER_SHA256" ]; then
    echo "$zip has sha256 $actual, not the pinned Inter $INTER_VERSION ($INTER_SHA256)." >&2
    echo "To move to a new release, review it, then bump INTER_VERSION and INTER_SHA256 here." >&2
    exit 1
fi

members=(LICENSE.txt)
for weight in "${WEIGHTS[@]}"; do members+=("extras/ttf/Inter-$weight.ttf"); done
unzip -q -j -d "$work/extract" "$zip" "${members[@]}"

python3 -m venv "$work/venv"
printf 'fonttools==%s --hash=sha256:%s\n' "$FONTTOOLS_VERSION" "$FONTTOOLS_SHA256" > "$work/requirements.txt"
"$work/venv/bin/pip" install --quiet --disable-pip-version-check --no-deps --only-binary :all: \
    --require-hashes -r "$work/requirements.txt"

mkdir -p fonts
command="pyftsubset Inter-<weight>.ttf --output-file=fonts/Inter-<weight>.ttf ${SUBSET_OPTIONS[*]}"
tabular=Inter-$TABULAR_WEIGHT-Tabular.ttf
tabular_command="scripts/tabular-font.py Inter-$TABULAR_WEIGHT.ttf $tabular && pyftsubset $tabular --output-file=fonts/$tabular ${TABULAR_OPTIONS[*]}"
outputs=()
describe() {
    outputs+=("  $1  sha256 $(sha256 "fonts/$1")  $(wc -c < "fonts/$1" | tr -d ' ') bytes")
}
for weight in "${WEIGHTS[@]}"; do
    "$work/venv/bin/python" -I -m fontTools.subset "$work/extract/Inter-$weight.ttf" \
        --output-file="fonts/Inter-$weight.ttf" "${SUBSET_OPTIONS[@]}"
    describe "Inter-$weight.ttf"
done
"$work/venv/bin/python" -I scripts/tabular-font.py "$work/extract/Inter-$TABULAR_WEIGHT.ttf" "$work/$tabular"
"$work/venv/bin/python" -I -m fontTools.subset "$work/$tabular" --output-file="fonts/$tabular" "${TABULAR_OPTIONS[@]}"
describe "$tabular"
cp "$work/extract/LICENSE.txt" fonts/OFL.txt

cat > fonts/SOURCE << EOF
font: Inter $INTER_VERSION (static TTFs from extras/ttf/)
license: SIL Open Font License 1.1, no Reserved Font Name (fonts/OFL.txt is the release's LICENSE.txt)
source: $INTER_URL
source sha256: $INTER_SHA256
subset with: fontTools $FONTTOOLS_VERSION (PyPI wheel sha256 $FONTTOOLS_SHA256)
command: $command
generated by: scripts/subset-fonts.sh
update: bump INTER_VERSION and INTER_SHA256 (or FONTTOOLS_*) in scripts/subset-fonts.sh after reviewing the release, rerun it, and commit fonts/ together
weights: ${WEIGHTS[*]}; Black falls back to Bold (spec section 5.2)
timecode variant: $tabular, family "Inter Tabular" (PostScript InterTabular), is Inter $TABULAR_WEIGHT with its tabular figures as the default digits, subset to timecode characters
timecode command: $tabular_command
timecode license: a Modified Version under the same OFL; it keeps the copyright and license name records and notes the change in its version string, and the new family name keeps it from passing for Inter (the OFL here reserves no font name)
files:
$(printf '%s\n' "${outputs[@]}")
EOF
cat fonts/SOURCE
