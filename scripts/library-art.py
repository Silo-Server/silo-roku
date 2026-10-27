#!/usr/bin/env python3
"""Write the library and Search pages' generated art into images/library/ (spec
sections 5.5 and 5.6, silo-apple b90a86ea).

  capsule_52_{fill,ring}_{fhd,hd}.9.png
                          the Sort pill and the Search segments: tvOS's 24 px
                          label with 12 px of padding above and below, filled
                          or as a 1 px outline, white
  capsule_26_fill_{fhd,hd}.9.png
                          the Filter pill's count: tvOS's 18 px bold number
                          with 2 px of padding above and below, white
  segments_{fhd,hd}.9.png the Search filter's 60 px track in its colours: white
                          7% inside a 1 px white 9% border
  rounded_12_fill_{fhd,hd}.9.png
                          the Sort menu's focused row, radius 12, white
  rail_chip.png           a focused alphabet rail letter's 38 px chip, radius 8,
                          white
  rail_dot.png            the resting rail's current letter, a 10 px disc
                          (tvOS's radius 8 rounds a 10 px chip to a circle),
                          white
  mark_{radio,box}_{off,on}.png
                          the filter panel's 22 px marks, white, drawn at 2x
                          for display scaling: SF's circle and
                          checkmark.circle.fill, square and
                          checkmark.square.fill (radius 5), 2 px strokes, the
                          filled ones with the check cut out so the row shows
                          through, as SF draws them
  mark_check.png          the panel's Done row: SF's checkmark alone

The shapes come from scripts/ui-art.py's generator, so they follow its rules:
HD sizes are the FHD sizes times 2/3, each 9-patch stretches a 2 px band in the
middle and marks the whole image as content, a capsule's radius is half its
height less 1 px, and thin borders stay 1 px in HD. The rail's chip and dot are
plain images a Poster scales. Uses only the standard library, so the pixels are
the same on every machine. Run from anywhere: python3 scripts/library-art.py
"""
import importlib.util
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("ui_art", HERE / "ui-art.py")
art = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(art)

PILL = 52  # capsule height, FHD px
BADGE = 26  # the Filter pill's count capsule, FHD px
TRACK = (60, (art.WHITE, 0.07), (art.WHITE, 0.09))  # height, fill, border
ROW_RADIUS = 12
RAIL_CHIP = (38, 8)  # size, radius
RAIL_DOT = 10
MARK = 22  # the filter panel's marks, FHD px
MARK_STROKE = 2.0
MARK_RADIUS = 5  # the box marks' corner radius


def check_points(size):
    """SF checkmark's three points inside a size box (as ui-art's check_disc)."""
    return [(size * 0.275, size * 0.52), (size * 0.425, size * 0.67), (size * 0.725, size * 0.33)]


def on_check(x, y, size, half_stroke):
    def segment_distance(a, b):
        (ax, ay), (bx, by) = a, b
        t = max(0.0, min(1.0, ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2)))
        return ((x - ax - t * (bx - ax)) ** 2 + (y - ay - t * (by - ay)) ** 2) ** 0.5
    points = check_points(size)
    return min(segment_distance(a, b) for a, b in zip(points, points[1:])) <= half_stroke


def on_disc(x, y, size, inset=0.0):
    r = size / 2 - inset
    return (x - size / 2) ** 2 + (y - size / 2) ** 2 <= r ** 2


def mark(kind, filled):
    """A 22 px mark at GLYPH_SCALE: a ring or a box outline, or filled with the check cut out."""
    def shape(x, y, size, inset=0.0):
        if kind == "radio":
            return on_disc(x, y, size, inset)
        return art.inside_rounded_rect(x, y, size, inset, MARK_RADIUS - inset)

    def covered(x, y, size):
        if filled:
            return shape(x, y, size) and not on_check(x, y, size, size * 0.06)
        return shape(x, y, size) and not shape(x, y, size, MARK_STROKE)
    return plain(art.coverage(MARK, covered, scale=art.GLYPH_SCALE))


def track(height):
    _, fill, border = TRACK
    radius = height // 2 - 1
    size = 2 * radius + art.STRETCH
    return art.bordered(size, size, radius, lambda t: fill, lambda t: border)


def rounded(radius):
    return art.coverage(2 * radius + art.STRETCH, lambda x, y, size: art.inside_rounded_rect(x, y, size, 0, radius))


def plain(alpha):
    return [[art.WHITE + (a,) for a in line] for line in alpha]


def images():
    for res, scale in (("fhd", lambda px: px), ("hd", art.hd)):
        yield f"capsule_52_fill_{res}.9.png", art.nine_patch(art.capsule(scale(PILL), 0), art.WHITE)
        yield f"capsule_52_ring_{res}.9.png", art.nine_patch(art.capsule(scale(PILL), 1), art.WHITE)
        yield f"capsule_26_fill_{res}.9.png", art.nine_patch(art.capsule(scale(BADGE), 0), art.WHITE)
        yield f"segments_{res}.9.png", art.nine_patch_rgba(track(scale(TRACK[0])))
        yield f"rounded_12_fill_{res}.9.png", art.nine_patch(rounded(scale(ROW_RADIUS)), art.WHITE)
    size, radius = RAIL_CHIP
    yield "rail_chip.png", plain(art.coverage(size, lambda x, y, s: art.inside_rounded_rect(x, y, s, 0, radius)))
    yield "rail_dot.png", plain(art.coverage(RAIL_DOT, lambda x, y, s: (x - s / 2) ** 2 + (y - s / 2) ** 2 <= (s / 2) ** 2))
    for kind in ("radio", "box"):
        yield f"mark_{kind}_off.png", mark(kind, False)
        yield f"mark_{kind}_on.png", mark(kind, True)
    yield "mark_check.png", plain(art.coverage(MARK, lambda x, y, s: on_check(x, y, s, MARK_STROKE / 2 + 0.25), scale=art.GLYPH_SCALE))


def main():
    out = HERE.parent / "images" / "library"
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in images():
        (out / name).write_bytes(art.png(rows))
        print(f"images/library/{name}  {len(rows[0])}x{len(rows)}")


if __name__ == "__main__":
    main()
