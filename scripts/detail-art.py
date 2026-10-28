#!/usr/bin/env python3
"""Write the detail pages' generated glyphs into images/detail/ (spec section 5.6).

  play.png       a triangle pointing right: Play and Resume
  restart.png    an arrow turning back on itself: Start Over
  versions.png   a rounded frame with two layers stacked behind it: Versions
  audio.png      a speaker with two sound waves: Audio
  subtitles.png  a rounded frame with two lines of text: Subtitles
  bookmark.png   a bookmark's outline: Watchlist, not on the list
  bookmark_fill.png
                 the bookmark filled: Watchlist, on the list (tvOS's
                 bookmark and bookmark.fill)
  more.png       three dots in a row: More (tvOS's ellipsis)
  heart_fill.png a filled heart: Favorites in the For You menu (tvOS's
                 heart.fill)
  sparkles.png   a large four-pointed star with two small ones: For You's
                 Recommendations (tvOS's sparkles)
  check.png      a bold check mark, 26 px: the choice in the Version, Audio
                 Tracks, and Subtitles menus (tvOS's 20 pt bold checkmark in
                 its 26 pt column)
  film.png       a film frame with sprocket holes down both sides, 48 px:
                 a Trailers & More card without a still (tvOS's 48 pt film)
  plus.png       a plus: Request on a request page (tvOS's plus)
  bell.png       a bell: Notify Me (tvOS's bell)
  bell_slash.png the bell struck through: Stop Notifying Me (bell.slash)
  xmark.png      an X: Cancel Request (tvOS's xmark)
  open.png       an arrow up and to the right: Open in Library
                 (arrow.up.right)
  status_{clock,arrow,check,alert}.png
                 20 px: a request card's corner badge for pending, on the
                 way, in the library, and needing the viewer (tvOS's clock,
                 arrow.down, checkmark, and exclamationmark)
  rounded_{8,10,14}_fill_{fhd,hd}.9.png
                 rounded rectangles of radius 8, 10, and 14: the Details
                 table's focus fill, the season placeholders, and the menu
                 rows' highlight and the action placeholders

Each glyph is white on transparent, for a Poster's blendColor: 34 px square
inside the action row's 76 px round buttons. Glyphs are rasterized at 2x
those logical FHD sizes for aligned bilinear minification. Their
geometry, stroke widths and optical offsets stay in logical pixels.
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
FILM = 48  # FHD px
STATUS = 20  # FHD px
STATUS_STROKE = 2.6
GLYPH_SCALE = 2  # intrinsic pixels per logical FHD pixel
STROKE = 3.4
STRETCH = 2  # a 9-patch's stretchable band between the corners, px
FILL_RADII = (8, 10, 14)  # FHD px
SAMPLES = 16
WHITE = (0xFF, 0xFF, 0xFF)


def coverage(size, covered, scale=1):
    """White RGBA rows over a size x size square for a point predicate."""
    rows = []
    for py in range(size * scale):
        row = []
        for px in range(size * scale):
            hits = sum(
                covered((px + (sx + 0.5) / SAMPLES) / scale, (py + (sy + 0.5) / SAMPLES) / scale)
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
    return coverage(size, lambda x, y: inside_triangle(x, y, points), GLYPH_SCALE)


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
    return coverage(size, covered, GLYPH_SCALE)


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
    return coverage(size, covered, GLYPH_SCALE)


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
    return coverage(size, covered, GLYPH_SCALE)


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
    return coverage(size, covered, GLYPH_SCALE)


def bookmark_outline(size):
    """A tall rectangle whose foot is cut by a V up to 0.66 of the height."""
    left, right, top, bottom, notch = size * 0.24, size * 0.76, size * 0.10, size * 0.90, size * 0.66
    cx = size / 2
    edges = ((left, top, right, top), (right, top, right, bottom), (right, bottom, cx, notch),
             (cx, notch, left, bottom), (left, bottom, left, top))

    def covered(x, y):
        return any(segment_distance(x, y, *edge) <= STROKE / 2 for edge in edges)
    return coverage(size, covered, GLYPH_SCALE)


def bookmark_fill(size):
    """The bookmark's outline, filled."""
    left, right, top, bottom, notch = size * 0.24, size * 0.76, size * 0.10, size * 0.90, size * 0.66
    cx = size / 2
    half = STROKE / 2
    outline = bookmark_outline(size)
    l, r, t, b = left - half, right + half, top - half, bottom + half

    def covered(x, y):
        if not (l <= x <= r and t <= y <= b):
            return False
        # Below the notch's V is outside: the V runs from the feet to the notch.
        if y > notch:
            depth = (y - notch) / (bottom - notch)
            return abs(x - cx) >= depth * (cx - left) - half
        return True
    filled = coverage(size, covered, GLYPH_SCALE)
    return [[a if a[3] >= f[3] else f for a, f in zip(row_a, row_f)] for row_a, row_f in zip(outline, filled)]


def more(size):
    """Three discs across the middle, as tvOS's ellipsis."""
    radius = size * 0.085
    centres = [(size * x, size / 2) for x in (0.20, 0.50, 0.80)]

    def covered(x, y):
        return any(math.hypot(x - cx, y - cy) <= radius for cx, cy in centres)
    return coverage(size, covered, GLYPH_SCALE)


def heart_fill(size):
    """The heart curve (x^2 + y^2 - 1)^3 <= x^2 y^3, filling the square."""
    cx, cy, scale = size / 2, size * 0.47, size * 0.33

    def covered(x, y):
        u, v = (x - cx) / scale, (cy - y) / scale
        return (u * u + v * v - 1) ** 3 - u * u * v ** 3 <= 0
    return coverage(size, covered, GLYPH_SCALE)


def sparkles(size):
    """Four-pointed stars with concave sides (|x|^0.5 + |y|^0.5 <= r^0.5):
    a large one low on the left, a small one high on the right, and a
    smaller one below it, as SF Symbols' sparkles."""
    stars = ((size * 0.40, size * 0.58, size * 0.38), (size * 0.76, size * 0.22, size * 0.20), (size * 0.80, size * 0.70, size * 0.13))

    def covered(x, y):
        return any(math.sqrt(abs(x - sx)) + math.sqrt(abs(y - sy)) <= math.sqrt(r) for sx, sy, r in stars)
    return coverage(size, covered, GLYPH_SCALE)


def check(size):
    """SF Symbols' checkmark at its bold weight: a short stroke down to the
    foot and a long one up to the right, round-capped."""
    half_stroke = size * 0.07
    points = ((size * 0.18, size * 0.53), (size * 0.40, size * 0.74), (size * 0.82, size * 0.27))

    def covered(x, y):
        return any(segment_distance(x, y, *a, *b) <= half_stroke for a, b in zip(points, points[1:]))
    return coverage(size, covered, GLYPH_SCALE)


def film(size):
    """SF Symbols' film: a rounded frame, a band down each side cut off by a
    line, and three sprocket holes in each band, in a 4 px stroke."""
    stroke = 4.0
    cx, cy = size / 2, size / 2
    half_w, half_h, radius = size * 0.42, size * 0.34, size * 0.09
    bands = (size * 0.29, size * 0.71)
    hole = size * 0.034
    holes = [(x, size * y) for x in (size * 0.185, size * 0.815) for y in (0.30, 0.50, 0.70)]

    def frame_distance(x, y):
        qx = abs(x - cx) - (half_w - radius)
        qy = abs(y - cy) - (half_h - radius)
        return math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - radius

    def covered(x, y):
        if abs(frame_distance(x, y)) <= stroke / 2:
            return True
        if any(segment_distance(x, y, band, cy - half_h, band, cy + half_h) <= stroke / 2 for band in bands):
            return True
        return any(abs(x - hx) <= hole and abs(y - hy) <= hole for hx, hy in holes)
    return coverage(size, covered, GLYPH_SCALE)


def plus(size):
    """Two round-capped strokes crossing at the centre."""
    half, reach = STROKE / 2, size * 0.32
    c = size / 2

    def covered(x, y):
        return segment_distance(x, y, c - reach, c, c + reach, c) <= half or segment_distance(x, y, c, c - reach, c, c + reach) <= half
    return coverage(size, covered, GLYPH_SCALE)


def xmark(size):
    """Two round-capped strokes crossing diagonally."""
    half, reach = STROKE / 2, size * 0.25
    c = size / 2

    def covered(x, y):
        return segment_distance(x, y, c - reach, c - reach, c + reach, c + reach) <= half or segment_distance(x, y, c - reach, c + reach, c + reach, c - reach) <= half
    return coverage(size, covered, GLYPH_SCALE)


def bell_shape(size):
    """A filled bell: a dome over flaring sides, a rim, and a clapper."""
    c = size / 2

    def covered(x, y):
        top, rim = size * 0.20, size * 0.70
        if top <= y <= rim:
            t = (y - top) / (rim - top)
            half = size * (0.20 + 0.10 * t * t)
            if y < size * 0.36:  # the dome
                return math.hypot((x - c) / (size * 0.20), (y - size * 0.36) / (size * 0.16)) <= 1
            return abs(x - c) <= half
        if rim < y <= rim + size * 0.06:
            return abs(x - c) <= size * 0.34
        if math.hypot(x - c, y - size * 0.82) <= size * 0.07:
            return True
        return math.hypot(x - c, y - size * 0.17) <= size * 0.05
    return covered


def bell(size):
    return coverage(size, bell_shape(size), GLYPH_SCALE)


def bell_slash(size):
    """The bell with a stroke from top left to bottom right, cut clear on
    either side."""
    shape = bell_shape(size)
    a, b = (size * 0.14, size * 0.12), (size * 0.86, size * 0.90)

    def covered(x, y):
        d = segment_distance(x, y, *a, *b)
        if d <= STROKE / 2:
            return True
        return d > STROKE * 1.2 and shape(x, y)
    return coverage(size, covered, GLYPH_SCALE)


def open_arrow(size):
    """An arrow up and to the right: a diagonal and its two head strokes."""
    half = STROKE / 2
    tip = (size * 0.74, size * 0.26)

    def covered(x, y):
        return (segment_distance(x, y, size * 0.26, size * 0.74, *tip) <= half
                or segment_distance(x, y, size * 0.38, size * 0.26, *tip) <= half
                or segment_distance(x, y, size * 0.74, size * 0.62, *tip) <= half)
    return coverage(size, covered, GLYPH_SCALE)


def status_clock(size):
    """A ring with hands at twelve and three."""
    c, r, half = size / 2, size * 0.38, STATUS_STROKE / 2

    def covered(x, y):
        if abs(math.hypot(x - c, y - c) - r) <= half:
            return True
        return segment_distance(x, y, c, c, c, c - r * 0.6) <= half or segment_distance(x, y, c, c, c + r * 0.5, c) <= half
    return coverage(size, covered, GLYPH_SCALE)


def status_arrow(size):
    """An arrow pointing down."""
    half = STATUS_STROKE / 2
    tip = (size / 2, size * 0.80)

    def covered(x, y):
        return (segment_distance(x, y, size / 2, size * 0.18, *tip) <= half
                or segment_distance(x, y, size * 0.24, size * 0.54, *tip) <= half
                or segment_distance(x, y, size * 0.76, size * 0.54, *tip) <= half)
    return coverage(size, covered, GLYPH_SCALE)


def status_check(size):
    half = STATUS_STROKE / 2 + 0.2
    points = ((size * 0.20, size * 0.52), (size * 0.41, size * 0.72), (size * 0.80, size * 0.30))

    def covered(x, y):
        return any(segment_distance(x, y, *a, *b) <= half for a, b in zip(points, points[1:]))
    return coverage(size, covered, GLYPH_SCALE)


def status_alert(size):
    """An exclamation mark: a stroke and a dot."""
    half = STATUS_STROKE / 2 + 0.2

    def covered(x, y):
        return segment_distance(x, y, size / 2, size * 0.18, size / 2, size * 0.58) <= half or math.hypot(x - size / 2, y - size * 0.80) <= half * 1.1
    return coverage(size, covered, GLYPH_SCALE)


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
    yield "bookmark.png", bookmark_outline(GLYPH)
    yield "bookmark_fill.png", bookmark_fill(GLYPH)
    yield "more.png", more(GLYPH)
    yield "heart_fill.png", heart_fill(GLYPH)
    yield "sparkles.png", sparkles(GLYPH)
    yield "check.png", check(CHECK)
    yield "film.png", film(FILM)
    yield "plus.png", plus(GLYPH)
    yield "bell.png", bell(GLYPH)
    yield "bell_slash.png", bell_slash(GLYPH)
    yield "xmark.png", xmark(GLYPH)
    yield "open.png", open_arrow(GLYPH)
    yield "status_clock.png", status_clock(STATUS)
    yield "status_arrow.png", status_arrow(STATUS)
    yield "status_check.png", status_check(STATUS)
    yield "status_alert.png", status_alert(STATUS)
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
