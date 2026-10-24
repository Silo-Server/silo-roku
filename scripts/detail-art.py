#!/usr/bin/env python3
"""Write the detail pages' generated glyphs into images/detail/ (spec section 5.6).

  play.png       a triangle pointing right: Play and Resume
  restart.png    an arrow turning back on itself: Start Over
  versions.png   a rounded frame with two layers stacked behind it: Versions
  audio.png      a speaker with two sound waves: Audio
  subtitles.png  a rounded frame with two lines of text: Subtitles
  check.png      a bold check mark, 26 px: the choice in the Version, Audio
                 Tracks, and Subtitles menus (tvOS's 20 pt bold checkmark in
                 its 26 pt column)
  rounded_{8,10,14}_fill_{fhd,hd}.9.png
                 rounded rectangles of radius 8, 10, and 14: the Details
                 table's focus fill, the season placeholders, and the menu
                 rows' highlight and the action placeholders

Each glyph is white on transparent, for a Poster's blendColor: 34 px square
inside the action row's 76 px round buttons; Roku scales it for an HD UI.
The fills are white 9-patches for blendColor and opacity, loaded through the
manifest's uri_resolution_autosub ($$RES$$ becomes fhd or hd); HD radii are
the FHD radii times 2/3, rounded. Shapes are plain geometry, not brand
assets. Edges are antialiased by 16x16 supersampling. Uses only the standard
library, so the pixels are the same on every machine. Run from anywhere:
python3 scripts/detail-art.py
"""
import math
import pathlib
import struct
import zlib

GLYPH = 34  # FHD px
CHECK = 26  # FHD px
STROKE = 3.4
STRETCH = 2  # a 9-patch's stretchable band between the corners, px
FILL_RADII = (8, 10, 14)  # FHD px
SAMPLES = 16
WHITE = (0xFF, 0xFF, 0xFF)


def coverage(size, covered):
    """White RGBA rows over a size x size square for a point predicate."""
    rows = []
    for py in range(size):
        row = []
        for px in range(size):
            hits = sum(
                covered(px + (sx + 0.5) / SAMPLES, py + (sy + 0.5) / SAMPLES)
                for sy in range(SAMPLES) for sx in range(SAMPLES))
            row.append(WHITE + (round(255 * hits / SAMPLES ** 2),))
        rows.append(row)
    return rows


def segment_distance(x, y, ax, ay, bx, by):
    """Distance from a point to the segment a-b."""
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(x - ax - t * dx, y - ay - t * dy)


def inside_triangle(x, y, points):
    (ax, ay), (bx, by), (cx, cy) = points

    def side(px, py, qx, qy):
        return (x - qx) * (py - qy) - (px - qx) * (y - qy)
    d1, d2, d3 = side(ax, ay, bx, by), side(bx, by, cx, cy), side(cx, cy, ax, ay)
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))


def play(size):
    """Its centroid sits a little right of centre, as the apps draw it."""
    top, bottom = size * 0.16, size * 0.84
    left, right = size * 0.24, size * 0.86
    points = ((left, top), (right, size / 2), (left, bottom))
    return coverage(size, lambda x, y: inside_triangle(x, y, points))


def restart(size):
    """Three quarters of a ring from the top, clockwise round to the left,
    with an arrowhead at the top pointing back the way it came."""
    cx = cy = size / 2
    r = size * 0.34
    head = ((cx - size * 0.02, cy - r - size * 0.16), (cx - size * 0.02, cy - r + size * 0.16), (cx - size * 0.22, cy - r))

    def covered(x, y):
        angle = math.degrees(math.atan2(x - cx, cy - y)) % 360  # 0 at the top, clockwise
        on_ring = abs(math.hypot(x - cx, y - cy) - r) <= STROKE / 2
        return (on_ring and angle <= 290) or inside_triangle(x, y, head)
    return coverage(size, covered)


def versions(size):
    """A rounded frame in a 3.4 px stroke, with two shorter lines above it for
    the layers behind, as tvOS's square.stack draws a stack."""
    cx = size / 2
    top, bottom = size * 0.38, size * 0.88
    half_w, radius = size * 0.36, size * 0.10
    cy, half_h = (top + bottom) / 2, (bottom - top) / 2
    layers = ((size * 0.24, size * 0.25, size * 0.76, size * 0.25), (size * 0.34, size * 0.12, size * 0.66, size * 0.12))

    def frame_distance(x, y):
        qx = abs(x - cx) - (half_w - radius)
        qy = abs(y - cy) - (half_h - radius)
        return math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - radius

    def covered(x, y):
        if abs(frame_distance(x, y)) <= STROKE / 2:
            return True
        return any(segment_distance(x, y, *line) <= STROKE / 2 for line in layers)
    return coverage(size, covered)


def audio(size):
    """A speaker cone on the left and two arcs to its right."""
    cy = size / 2
    body = (size * 0.10, size * 0.38, size * 0.26, size * 0.62)
    cone = ((size * 0.24, size * 0.38), (size * 0.46, size * 0.16), (size * 0.46, size * 0.84), (size * 0.24, size * 0.62))
    ox = size * 0.40

    def covered(x, y):
        if body[0] <= x <= body[2] and body[1] <= y <= body[3]:
            return True
        if inside_triangle(x, y, cone[:3]) or inside_triangle(x, y, (cone[0], cone[2], cone[3])):
            return True
        if x <= ox + size * 0.12:
            return False
        d = math.hypot(x - ox, y - cy)
        span = abs(math.degrees(math.atan2(y - cy, x - ox))) <= 48
        return span and any(abs(d - radius) <= STROKE / 2 for radius in (size * 0.26, size * 0.42))
    return coverage(size, covered)


def subtitles(size):
    """A rounded frame in a 3.4 px stroke, with two text lines near its foot."""
    cx, cy = size / 2, size / 2
    half_w, half_h, radius = size * 0.42, size * 0.30, size * 0.12
    lines = ((size * 0.24, size * 0.48, size * 0.76, size * 0.48), (size * 0.24, size * 0.63, size * 0.58, size * 0.63))

    def frame_distance(x, y):
        """Signed distance to the frame's rounded rectangle."""
        qx = abs(x - cx) - (half_w - radius)
        qy = abs(y - cy) - (half_h - radius)
        return math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - radius

    def covered(x, y):
        if abs(frame_distance(x, y)) <= STROKE / 2:
            return True
        return any(segment_distance(x, y, *line) <= STROKE / 2 for line in lines)
    return coverage(size, covered)


def check(size):
    """SF Symbols' checkmark at its bold weight: a short stroke down to the
    foot and a long one up to the right, round-capped."""
    half_stroke = size * 0.07
    points = ((size * 0.18, size * 0.53), (size * 0.40, size * 0.74), (size * 0.82, size * 0.27))

    def covered(x, y):
        return any(segment_distance(x, y, *a, *b) <= half_stroke for a, b in zip(points, points[1:]))
    return coverage(size, covered)


def rounded_fill(radius):
    """A white rounded square of 2 * radius + STRETCH px as a 9-patch: the
    1 px border marks the middle STRETCH px to stretch and the whole image as
    content, so a Poster of any size keeps the corners."""
    size = 2 * radius + STRETCH

    def covered(x, y):
        qx = abs(x - size / 2) - STRETCH / 2
        qy = abs(y - size / 2) - STRETCH / 2
        return math.hypot(max(qx, 0), max(qy, 0)) <= radius
    pixels = coverage(size, covered)
    clear, mark = (0, 0, 0, 0), (0, 0, 0, 255)
    first = radius + 1  # the border column or row of the first stretch pixel
    rows = [[mark if first <= x < first + STRETCH else clear for x in range(size + 2)]]
    for y, line in enumerate(pixels, start=1):
        rows.append([mark if first <= y < first + STRETCH else clear] + line + [mark])
    rows.append([clear] + [mark] * size + [clear])
    return rows


def png(rows):
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    height, width = len(rows), len(rows[0])
    raw = b"".join(b"\x00" + bytes(channel for pixel in row for channel in pixel) for row in rows)
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def images():
    yield "play.png", play(GLYPH)
    yield "restart.png", restart(GLYPH)
    yield "versions.png", versions(GLYPH)
    yield "audio.png", audio(GLYPH)
    yield "subtitles.png", subtitles(GLYPH)
    yield "check.png", check(CHECK)
    for radius in FILL_RADII:
        yield f"rounded_{radius}_fill_fhd.9.png", rounded_fill(radius)
        yield f"rounded_{radius}_fill_hd.9.png", rounded_fill(round(radius * 2 / 3))


def main():
    out = pathlib.Path(__file__).resolve().parent.parent / "images" / "detail"
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in images():
        (out / name).write_bytes(png(rows))
        print(f"images/detail/{name}  {len(rows[0])}x{len(rows)}")


if __name__ == "__main__":
    main()
