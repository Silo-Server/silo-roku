#!/usr/bin/env python3
"""Write the player's generated art into images/player/ (spec section 5.7, tvOS's sizes).

  capsule_{66,36,46,62,84}_{fill,ring}_{fhd,hd}.9.png
                          capsules of exactly that height, filled or as a 1 px
                          outline: the round buttons (66), the rate chip and busy capsule (36), the
                          Options tabs (46), the error buttons (62, its ring
                          the 4 px focus stroke), and the hold indicator's chip (84)
  capsule_26_ring_{fhd,hd}.9.png
                          the Info pane's outlined badges
  capsule_44_{fill,ring}_{fhd,hd}.9.png
                          Up Next's auto-play toggle outline (2 px)
  rounded_{8,10,20,28}_{fill,ring}_{fhd,hd}.9.png
                          rounded rectangles with a 1 px outline: track rows
                          (8), setting rows (10), the preview card (20), and the
                          Options panel, its picker, and the notice card (28)
  frame_14_{fhd,hd}.9.png the preview thumbnail's corners outside radius 14,
                          tinted to the card's colour
  knob.png, knob_scrub.png
                          the scrubber's 30 px knob, and the 42 px knob with
                          its 8 px white 55% stroke (4 px of it outside)
  play.png, pause.png     44 px glyphs (tvOS's 30 pt play.fill and pause.fill)
  skip_back.png, skip_forward.png, up_next.png, options.png, close.png
                          36 px glyphs (25 pt): a circular arrow each way with
                          room for the skip interval, stacked cards
                          (rectangle.stack.fill), three sliders, and a cross
  seek_back.png, seek_forward.png
                          the rate chips' double triangles (backward.fill,
                          forward.fill), 40x28
  skip_end.png            Skip Recap's forward.end.fill, 30 px
  check.png, chevron.png  the Options rows' check (20 pt checkmark) and
                          chevron (15 pt chevron.right)
  warning.png, info.png   40 px exclamationmark.triangle.fill and
                          info.circle.fill: the error screen and the notices
  keep_watching.png, back.png
                          Up Next's rectangle.inset.filled and chevron.left, 30 px

Everything is white, so the player tints it with a Poster's blendColor and
opacity. The glyphs are plain geometry drawn here after the shapes of tvOS's
SF Symbols, on a 48-unit design grid scaled to each canvas; no icon file is
copied. The 9-patches follow scripts/first-run-art.py: HD sizes are the FHD
sizes times 2/3, a capsule's radius is half its height less 1 px, a 2 px band
stretches in the middle, and 1 px outlines stay 1 px in HD.

Glyph edges are antialiased by 8x8 supersampling. Uses only the standard
library, so the pixels are the same on every machine. Run from anywhere:
python3 scripts/player-art.py
"""
import importlib.util
import math
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("first_run_art", HERE / "first-run-art.py")
art = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(art)

GRID = 48  # glyph design units
SAMPLES = 8
WHITE = (255, 255, 255)
STRETCH = 2


def coverage(covered, width, height):
    """Per-pixel alpha (0-1) over width x height for a predicate in design units."""
    scale = GRID / max(width, height)
    left = (GRID - width * scale) / 2
    top = (GRID - height * scale) / 2
    rows = []
    for py in range(height):
        row = []
        for px in range(width):
            hits = sum(
                covered(left + (px + (sx + 0.5) / SAMPLES) * scale, top + (py + (sy + 0.5) / SAMPLES) * scale)
                for sy in range(SAMPLES) for sx in range(SAMPLES))
            row.append(hits / SAMPLES ** 2)
        rows.append(row)
    return rows


def in_polygon(x, y, points):
    inside = False
    for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def near_segment(x, y, a, b, half_width):
    (ax, ay), (bx, by) = a, b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(x - ax - t * dx, y - ay - t * dy) <= half_width


def near_polyline(x, y, points, half_width):
    return any(near_segment(x, y, a, b, half_width) for a, b in zip(points, points[1:]))


def in_rect(x, y, left, top, right, bottom):
    return left <= x <= right and top <= y <= bottom


def in_rounded_rect(x, y, left, top, right, bottom, radius):
    if not in_rect(x, y, left, top, right, bottom):
        return False
    cx = min(max(x, left + radius), right - radius)
    cy = min(max(y, top + radius), bottom - radius)
    return math.hypot(x - cx, y - cy) <= radius


def glyph(size, *shapes, height=None, cut=()):
    """White RGBA rows covering the union of shapes less the cut shapes, on a size (x height) canvas."""
    def covered(x, y):
        return any(shape(x, y) for shape in shapes) and not any(hole(x, y) for hole in cut)
    return art.rgba(coverage(covered, size, height or size), WHITE)


# --- Glyphs ---------------------------------------------------------------------------


def play():
    return glyph(44, lambda x, y: in_polygon(x, y, [(15, 9), (15, 39), (39, 24)]))


def pause():
    return glyph(44, lambda x, y: in_rounded_rect(x, y, 12, 9, 20, 39, 2), lambda x, y: in_rounded_rect(x, y, 28, 9, 36, 39, 2))


def skip_arrow(mirror):
    """A ring open at the top left with an arrowhead pointing back along it; mirrored, forward."""
    cx, cy, radius, half = 24, 26, 17, 2.0
    gap_from, gap_to = 225, 270  # degrees, y down, clockwise from the +x axis

    def ring(x, y):
        if mirror:
            x = GRID - x
        if abs(math.hypot(x - cx, y - cy) - radius) > half:
            return False
        angle = math.degrees(math.atan2(y - cy, x - cx)) % 360
        return not gap_from < angle < gap_to

    def head(x, y):
        if mirror:
            x = GRID - x
        top = cy - radius
        return in_polygon(x, y, [(cx + 1, top - 7), (cx + 1, top + 7), (cx - 8, top)])

    return glyph(36, ring, head)


def stack():
    """rectangle.stack.fill: a filled card with two narrower edges behind it."""
    return glyph(36, lambda x, y: in_rounded_rect(x, y, 6, 19, 42, 42, 4),
                 lambda x, y: in_rounded_rect(x, y, 10, 12.5, 38, 16, 1.6),
                 lambda x, y: in_rounded_rect(x, y, 14, 6, 34, 9.5, 1.6))


def sliders():
    shapes = []
    for row, knob in ((12, 31), (24, 15), (36, 27)):
        shapes.append(lambda x, y, row=row: near_segment(x, y, (5, row), (43, row), 2.2))
        shapes.append(lambda x, y, row=row, knob=knob: math.hypot(x - knob, y - row) <= 5.6)
    return glyph(36, *shapes)


def cross():
    return glyph(36, lambda x, y: near_segment(x, y, (11, 11), (37, 37), 2.6), lambda x, y: near_segment(x, y, (37, 11), (11, 37), 2.6))


def seek(mirror):
    def flip(points):
        return [(GRID - px, py) for px, py in points] if mirror else points
    first, second = flip([(3, 9), (3, 39), (24, 24)]), flip([(24, 9), (24, 39), (45, 24)])
    return glyph(40, lambda x, y: in_polygon(x, y, first), lambda x, y: in_polygon(x, y, second), height=28)


def skip_end():
    return glyph(30, lambda x, y: in_polygon(x, y, [(8, 8), (8, 40), (33, 24)]), lambda x, y: in_rounded_rect(x, y, 35, 8, 41, 40, 1.5))


def check():
    return glyph(20, lambda x, y: near_polyline(x, y, [(7, 25), (18, 36), (41, 11)], 3.4))


def chevron(mirror=False, size=15):
    points = [(17, 6), (33, 24), (17, 42)]
    if mirror:
        points = [(GRID - px, py) for px, py in points]
    return glyph(size, lambda x, y: near_polyline(x, y, points, 4.2))


def warning():
    """exclamationmark.triangle.fill: a rounded triangle with the mark cut out."""
    def triangle(x, y):
        corners = [(24, 4), (45, 42), (3, 42)]
        return in_polygon(x, y, corners) or near_polyline(x, y, corners + corners[:1], 2.4)
    return glyph(40, triangle, cut=(lambda x, y: in_rounded_rect(x, y, 21.6, 15, 26.4, 31, 2.2),
                                    lambda x, y: math.hypot(x - 24, y - 36.5) <= 2.8))


def info():
    """info.circle.fill: a disc with the i cut out."""
    return glyph(40, lambda x, y: math.hypot(x - 24, y - 24) <= 22,
                 cut=(lambda x, y: in_rounded_rect(x, y, 21.5, 20, 26.5, 36, 2.2), lambda x, y: math.hypot(x - 24, y - 13.5) <= 3))


def keep_watching():
    """rectangle.inset.filled: an outlined frame with a filled panel inside."""
    def frame(x, y):
        return in_rounded_rect(x, y, 4, 9, 44, 39, 5) and not in_rounded_rect(x, y, 7.5, 12.5, 40.5, 35.5, 2.5)
    return glyph(30, frame, lambda x, y: in_rounded_rect(x, y, 11, 16, 37, 32, 2))


# --- Shapes ---------------------------------------------------------------------------


def rounded(radius, rings=(0, 1)):
    """rounded_<radius> 9-patches, FHD and HD: filled (ring 0) and as a 1 px outline."""
    for res in ("fhd", "hd"):
        r = radius if res == "fhd" else art.hd(radius)
        size = 2 * r + STRETCH
        for ring in rings:
            kind = "fill" if ring == 0 else "ring"
            yield f"rounded_{radius}_{kind}_{res}.9.png", art.nine_patch(art.shape_alpha(size, size, r, ring))


def capsule(height, rings=(0, 1)):
    """A capsule exactly height px tall: its radius is half the height less 1 px."""
    for res in ("fhd", "hd"):
        size = height if res == "fhd" else art.hd(height)
        radius = size // 2 - 1
        size = 2 * radius + STRETCH
        for ring in rings:
            kind = "fill" if ring == 0 else "ring"
            width = ring if ring <= 1 or res == "fhd" else art.hd(ring)
            yield f"capsule_{height}_{kind}_{res}.9.png", art.nine_patch(art.shape_alpha(size, size, radius, width))


def corner_frame(radius):
    """The corners outside a rounded rectangle, white, for tinting to the colour around it."""
    for res in ("fhd", "hd"):
        r = radius if res == "fhd" else art.hd(radius)
        size = 2 * r + STRETCH
        inside = art.shape_alpha(size, size, r)
        yield f"frame_{radius}_{res}.9.png", art.nine_patch([[1 - a for a in line] for line in inside])


def scrub_knob():
    """A 42 px white disc under an 8 px white 55% stroke centred on its edge: 50 px across."""
    size = 50
    disc = art.disc_alpha(size, 21)
    halo = art.disc_alpha(size, 25)
    return [[WHITE + (round(255 * max(d, 0.55 * h)),) for d, h in zip(dl, hl)] for dl, hl in zip(disc, halo)]


def images():
    yield from capsule(66)
    yield from capsule(36)
    yield from capsule(46)
    yield from capsule(62, rings=(0, 4))
    yield from capsule(84)
    yield from capsule(26, rings=(1,))
    yield from capsule(44, rings=(2,))
    for radius in (8, 10, 20, 28):
        yield from rounded(radius)
    yield from corner_frame(14)
    yield "knob.png", art.rgba(art.disc_alpha(30, 15), WHITE)
    yield "knob_scrub.png", scrub_knob()
    yield "play.png", play()
    yield "pause.png", pause()
    yield "skip_back.png", skip_arrow(False)
    yield "skip_forward.png", skip_arrow(True)
    yield "up_next.png", stack()
    yield "options.png", sliders()
    yield "close.png", cross()
    yield "seek_back.png", seek(True)
    yield "seek_forward.png", seek(False)
    yield "skip_end.png", skip_end()
    yield "check.png", check()
    yield "chevron.png", chevron()
    yield "warning.png", warning()
    yield "info.png", info()
    yield "keep_watching.png", keep_watching()
    yield "back.png", chevron(mirror=True, size=30)


def main():
    out = HERE.parent / "images" / "player"
    out.mkdir(parents=True, exist_ok=True)
    written = set()
    for name, rows in images():
        (out / name).write_bytes(art.png(rows))
        written.add(name)
        print(f"images/player/{name}  {len(rows[0])}x{len(rows)}")
    for stale in sorted(out.glob("*.png")):
        if stale.name not in written:
            stale.unlink()
            print(f"removed images/player/{stale.name}")


if __name__ == "__main__":
    main()
