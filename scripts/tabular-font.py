#!/usr/bin/env python3
"""Make an Inter TTF's tabular figures its default glyphs, for timecodes.

  tabular-font.py <Inter-Weight.ttf> <output.ttf>

LabelBase's monospacedDigits renders every digit of the packaged Inter as a box
(implementation assumption A-17), and Label has no way to turn on the font's
tnum feature, so the timecode font maps the characters themselves to Inter's
tabular glyphs. Every character tnum covers (digits, space, colon, period,
hyphen, minus, and more) points at its tabular form, as CSS tabular-nums would
render it. Colon, hyphen, and minus first take their case forms, which Inter's
calt chooses next to digits, so "1:02:03" and "-0:42" match the other Silo TV
apps.

The result is a Modified Version under the OFL, renamed to the family Inter
Tabular (PostScript InterTabular) with the change noted in its version string;
the copyright and license name records stay. scripts/subset-fonts.sh then
subsets it to the timecode characters. Requires fontTools; the timestamp is
kept, so the output is reproducible.
"""
import sys

from fontTools.ttLib import TTFont

FAMILY = "Inter Tabular"
POSTSCRIPT_FAMILY = "InterTabular"
VERSION_NOTE = "modified: tabular figures as the default glyphs"
CASE_FORMS = ":-−"
DIGITS = "0123456789"


def single_substitutions(font, tag):
    """The glyph-to-glyph map of a GSUB feature's single substitutions."""
    gsub = font["GSUB"].table
    mapping = {}
    for record in gsub.FeatureList.FeatureRecord:
        if record.FeatureTag != tag:
            continue
        for index in record.Feature.LookupListIndex:
            lookup = gsub.LookupList.Lookup[index]
            for subtable in lookup.SubTable:
                if lookup.LookupType == 7:
                    subtable = subtable.ExtSubTable
                mapping.update(getattr(subtable, "mapping", {}))
    if not mapping:
        sys.exit(f"no single substitutions in the {tag} feature")
    return mapping


def remap(font):
    case = single_substitutions(font, "case")
    tabular = single_substitutions(font, "tnum")
    cmap = {}
    for code_point, glyph in font.getBestCmap().items():
        if chr(code_point) in CASE_FORMS:
            glyph = case[glyph]
        cmap[code_point] = tabular.get(glyph, glyph)
    # Subtables may share one dict, so each gets a new one.
    for table in font["cmap"].tables:
        table.cmap = {code_point: cmap.get(code_point, glyph) for code_point, glyph in table.cmap.items()}
    advances = {font["hmtx"][cmap[ord(digit)]][0] for digit in DIGITS}
    if len(advances) != 1:
        sys.exit(f"digits have advances {sorted(advances)}, not one tabular width")


def rename(font):
    for record in font["name"].names:
        text = record.toUnicode()
        if record.nameID in (1, 4, 16):
            renamed = text.replace("Inter", FAMILY, 1)
        elif record.nameID in (3, 6):
            renamed = text.replace("Inter-", POSTSCRIPT_FAMILY + "-", 1)
        elif record.nameID == 5:
            renamed = text + ";" + VERSION_NOTE
        else:
            continue
        if renamed == text:
            sys.exit(f"name record {record.nameID} ({text!r}) does not name Inter")
        record.string = renamed


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    font = TTFont(sys.argv[1], recalcTimestamp=False)
    remap(font)
    rename(font)
    font.save(sys.argv[2])


if __name__ == "__main__":
    main()
