#!/usr/bin/env python3
"""Instance one weight of a variable CJK font and subset it to a character list.

    python3 -I scripts/cjk-font.py SOURCE.ttf WEIGHT REQUIRED.txt EXTRA.txt OUT.ttf

Run by scripts/subset-cjk-fonts.sh with fontTools from its pinned wheel.
REQUIRED holds the characters the font must draw (the catalog's), EXTRA those
it keeps when the source has them. A required character the source lacks
fails the run, except U+200A (the hair space theme.tracked puts between
letters, which Noto Sans CJK does not have; tracking is off in the CJK
locales); control characters are left out. Prints the glyph count.
"""
import sys

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

OPTIONAL = {0x200A}


def characters(path):
    with open(path, encoding="utf-8") as f:
        return {ord(c) for c in f.read() if ord(c) >= 0x20 and not 0x7F <= ord(c) < 0xA0}


def main(source, weight, required_path, extra_path, out):
    required = characters(required_path)
    wanted = sorted(required | characters(extra_path))
    font = TTFont(source)
    cmap = font.getBestCmap()
    missing = sorted(cp for cp in required if cp not in cmap and cp not in OPTIONAL)
    if missing:
        sys.exit(f"{source} lacks " + " ".join(f"U+{cp:04X}" for cp in missing))
    font = instancer.instantiateVariableFont(font, {"wght": int(weight)}, updateFontNames=True)
    options = subset.Options()
    options.name_IDs += [13, 14]
    options.notdef_outline = True
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=[cp for cp in wanted if cp in cmap])
    subsetter.subset(font)
    # Keep the source's head.modified, so the same pins give the same file.
    font.recalcTimestamp = False
    font.save(out)
    kept = sum(1 for cp in wanted if cp in cmap)
    print(f"{out}: {len(font.getGlyphOrder())} glyphs, {kept} of {len(wanted)} characters")


if __name__ == "__main__":
    if len(sys.argv) != 6:
        sys.exit(__doc__)
    main(*sys.argv[1:])
