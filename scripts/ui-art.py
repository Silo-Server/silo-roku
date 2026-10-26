#!/usr/bin/env python3
"""Write the theme's generated UI art into images/ui/ (plan section 4.6).

  card_frame_{fhd,hd}.9.png  rounded-corner frame: the area outside a rounded
                             rectangle painted in the background colour, laid
                             over a square Poster so it reads as rounded
  focus_ring_{fhd,hd}.9.png  focus ring drawn inside the card edge, with the
                             card's corner radius
  scrim_left.png             black, opaque at the left edge and clear at the right
  scrim_bottom.png           black, clear at the top and opaque at the bottom
  card_placeholder.png       a card without artwork: Android TV's default
                             artwork, three brand glows over #16171C
  search_glyph.png           the top bar's magnifier, white, for blendColor;
                             2x its logical 28 px canvas for display scaling

tvOS's shared art (spec section 5, silo-apple b90a86ea; AG-222):

  backdrop_fade_bottom.png   the hero backdrop's vertical fade as a black
                             overlay, 2x756 for the 1229x756 backdrop box at
                             (691, 0): clear to y 287, black 12% at 393, 42% at
                             514, 76% at 612, opaque from 680 (TVRootHeroBackdrop's
                             mask, 1 less its alpha). Its horizontal fade is
                             scrim_left.png stretched over x 691-1527
  top_scrim.png              black 50% at the top to clear, 2x190, stretched
                             full width under the top bar
  hero_fade_{left,bottom}.png, detail_fade_{left,bottom}.png
                             the same two fades for the hero wash (spec 5.5,
                             AG-302), grey-coded for blendColor: alpha as
                             scrim_left.png (64 columns, stretched over the
                             same 836 px) and backdrop_fade_bottom.png, grey
                             the wash's weight at each row: white to y 287,
                             then falling linearly to black at the page's
                             wash foot, y 596 on Home (the row band) and 690
                             on detail (the hero's foot). Tinted with the
                             wash's colour, the art fades into the wash where
                             the wash is and into black below it; tinted
                             black, they are the black fades. The left fade's
                             rows are 4 px apart (189 rows)
  wash_fade.png              white, opaque at the top and clear at the bottom,
                             2x256, stretched from y 287 to the wash foot and
                             tinted with the wash's colour
  ambient_glow_half.png, ambient_glow_quarter.png
                             white, alpha falling linearly from 1 at the centre
                             to 0 at an ellipse, for the accent's glow (the top
                             half, centred on its bottom edge: 1152x324 at
                             x 768, the foot of the page) and the shadow's pool
                             (a quarter, centred on its bottom-left corner:
                             806x454 at the page's bottom left); tinted, at the
                             wash's opacity
  flat_fade_{left,bottom}.png
                             the backdrop's two fades in white, alpha as
                             scrim_left.png and backdrop_fade_bottom.png, for
                             the ambient wash's flat base (spec 5.5)
  progress_{12_4,18_6}.9.png a progress track where a card rounds its own
                             corners: white, 4 px (6 px) tall, its bottom
                             corners on a radius-12 (18) card's curve; FHD only
  still_frame_{fhd,hd}.9.png card_frame at radius 18, for detail episode stills
  card_shadow_{fhd,hd}.9.png a focused card's shadow, black 50% blurred with a
                             10 px sigma (EpisodeThumbCard's radius 20, read as
                             2 sigma), reaching SHADOW_MARGIN px past the card;
                             draw it under the card that much larger on each
                             side and theme.size.CARD_SHADOW_OFFSET px lower
  chip_{fhd,hd}.9.png        a badge chip: radius 6, white 7% fill, 1 px white
                             24% border, in its colours
  panel_{22,18}_{fhd,hd}.9.png
                             menu panels (radius 22) and the library flyout (18):
                             #23252C at 92% to #141519 at 95% top to bottom,
                             under a 1 px border from white 22% to 5%, in their
                             colours. The middle PANEL_BAND rows hold the
                             gradient and stretch, so it spans any panel height
  tab_{fill,ring}_{fhd,hd}.9.png
                             the top bar's 56 px tab capsule, filled or as a
                             1 px outline, white
  check_disc.png             the watched mark: a logical 40 px #EDEDED disc
                             with a black check, rasterized at 2x
  cast_shadow.png            circular portrait shadow using the card shadow blur
  circle_ring_3.png          the focused top bar avatar's ring: 3 px inside a 58 px
                             circle, white
  rounded_{14,12}_{fhd,hd}.9.png
                             white rounded rectangles, for blendColor: the avatar
                             menu's and library list's row fills (radius 14) and
                             the library flyout's section rows (12)
  button_14_{fhd,hd}.9.png   a dialog button at rest, radius 14: white 7% fill, 1 px
                             white 9% border, in its colours (rounded_14 tinted
                             #EDEDED when focused)
  dialog_30_{fhd,hd}.9.png   a confirmation dialog's card, radius 30: #15171C with a
                             1 px white 9% border, in its colours

The 9-patches are loaded through the manifest's uri_resolution_autosub
($$RES$$ becomes fhd or hd). HD sizes are the FHD sizes times 2/3, rounded to
whole pixels, and every image has even dimensions, as Roku's FHD-to-HD scaling
expects. Each 9-patch stretches a 2 px band in the middle (the panels, their
gradient band) and marks the whole image as content, so bitmapMargins are
zero. The scrims are plain ramps a Poster stretches over the fade area. Thin
borders stay 1 px in HD, where 2/3 px would vanish.

Edges are antialiased by 16x16 supersampling. Uses only the standard library,
so the pixels are the same on every machine. Run from anywhere:
python3 scripts/ui-art.py
"""
import math
import pathlib
import struct
import zlib

BACKGROUND = (0x00, 0x00, 0x00)  # spec 5.2 background
FOCUS_RING = (0xED, 0xED, 0xED)  # spec 5.2 poster and landscape focus ring
CARD_RADIUS = 12  # spec 5.2, FHD px
STILL_RADIUS = 18  # spec 5.2, detail episode stills
RING_WIDTH = 4  # spec 5.2, FHD px
STRETCH = 2  # stretchable band between the corners, px
SAMPLES = 16  # supersamples per pixel along each axis
RAMP = 256  # scrim length, px
PLACEHOLDER = (88, 132)  # stretched over any card
PLACEHOLDER_BASE = (0x16, 0x17, 0x1C)
# Android TV's DefaultArtwork: colour, alpha, and centre as a fraction of the size.
GLOWS = (((0x00, 0x34, 0xFB), 0.176, (0.0, 0.0)), ((0xFD, 0x74, 0x03), 0.144, (1.0, 1.0)), ((0xF5, 0x0B, 0x4F), 0.112, (0.7, 0.3)))
CIRCLE = 58  # top bar search and avatar circles, FHD px
GLYPH = 28  # magnifier, FHD px: SF Symbols' magnifyingglass at 27 pt semibold
GLYPH_SCALE = 2  # intrinsic pixels per logical FHD pixel; glyphs only
AVATAR_RING = 3  # the focused avatar's ring, inside the circle
WHITE = (0xFF, 0xFF, 0xFF)
INK = (0xED, 0xED, 0xED)
# The backdrop box's vertical fade (TVBackdropArtworkFadeMask): (y, art alpha).
BACKDROP_HEIGHT = 756
BACKDROP_STOPS = ((0, 1.0), (287, 1.0), (393, 0.88), (514, 0.58), (612, 0.24), (680, 0.0), (756, 0.0))
TOP_SCRIM = (190, 0.5)  # height, black alpha at the top
WASH_TOP = 287  # the wash is full to here, then fades (the backdrop mask's first stop)
WASH_FEET = (("hero", 596), ("detail", 690))  # where Home's and detail's wash reach black
FADE_LEFT_COLUMNS = 64
FADE_LEFT_ROW = 4  # px of the 756 px box per row of the grey-coded left fade
GLOW_HALF = (128, 36)
GLOW_QUARTER = (128, 72)
SHADOW_SIGMA = 10
SHADOW_ALPHA = 0.5
SHADOW_MARGIN = 3 * SHADOW_SIGMA  # past the card's edge on every side
CHIP = (6, (WHITE, 0.07), (WHITE, 0.24))  # radius, fill, border
PANEL_TOP = ((0x23, 0x25, 0x2C), 0.92, 0.22)  # fill, fill alpha, border alpha
PANEL_BOTTOM = ((0x14, 0x15, 0x19), 0.95, 0.05)
PANEL_BAND = 64  # gradient rows that stretch
TAB = 56  # capsule height, FHD px
CHECK_DISC = 40
ROW_RADII = (14, 12)  # menu row fills: library and avatar rows, flyout sections
BUTTON = (14, (WHITE, 0.07), (WHITE, 0.09))  # radius, fill, border (siloChromeResting*)
DIALOG = (30, ((0x15, 0x17, 0x1C), 1.0), (WHITE, 0.09))  # radius, fill, border


def hd(fhd_px):
    return round(fhd_px * 2 / 3)


def inside_rounded_rect(x, y, size, inset, radius, height=None):
    """Whether the point lies in [inset, size - inset] x [inset, height - inset]
    (a square unless height is given) with corner radius."""
    height = size if height is None else height
    low, right, bottom = inset, size - inset, height - inset
    if not (low <= x <= right and low <= y <= bottom):
        return False
    cx = min(max(x, low + radius), right - radius)
    cy = min(max(y, low + radius), bottom - radius)
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2


def coverage(size, covered, height=None, scale=1):
    """Per-pixel alpha (0-255) over a size-wide square (or height-tall rectangle) for a point predicate."""
    height = size if height is None else height
    rows = []
    for py in range(height * scale):
        row = []
        for px in range(size * scale):
            hits = sum(
                covered((px + (sx + 0.5) / SAMPLES) / scale, (py + (sy + 0.5) / SAMPLES) / scale, size)
                for sy in range(SAMPLES) for sx in range(SAMPLES))
            row.append(round(255 * hits / SAMPLES ** 2))
        rows.append(row)
    return rows


def card_frame(radius):
    return coverage(2 * radius + STRETCH, lambda x, y, size: not inside_rounded_rect(x, y, size, 0, radius))


def focus_ring(radius, width):
    def covered(x, y, size):
        return inside_rounded_rect(x, y, size, 0, radius) and not inside_rounded_rect(x, y, size, width, radius - width)
    return coverage(2 * radius + STRETCH, covered)


def progress_track(radius, height):
    """The bottom height rows of a rounded rectangle 2 * radius + STRETCH wide."""
    tall = 4 * radius
    width = 2 * radius + STRETCH
    alpha = coverage(width, lambda x, y, size: inside_rounded_rect(x, y + tall - height, size, 0, radius, tall), height)
    return nine_patch_rgba([[WHITE + (a,) for a in line] for line in alpha], band=height)


def nine_patch(alpha, rgb):
    """A square of one colour's alpha as a 9-patch stretching its middle STRETCH px."""
    return nine_patch_rgba([[rgb + (a,) for a in line] for line in alpha])


def nine_patch_rgba(pixels, band=STRETCH):
    """RGBA rows with the 1 px 9-patch border: stretch marks top and left (the
    middle STRETCH columns and the middle band rows), full content right and bottom."""
    height, width = len(pixels), len(pixels[0])
    clear, mark = (0, 0, 0, 0), (0, 0, 0, 255)
    first_x = (width - STRETCH) // 2 + 1  # border column index of the first stretch pixel
    first_y = (height - band) // 2 + 1
    rows = [[mark if first_x <= x < first_x + STRETCH else clear for x in range(width + 2)]]
    for y, line in enumerate(pixels, start=1):
        rows.append([mark if first_y <= y < first_y + band else clear] + list(line) + [mark])
    rows.append([clear] + [mark] * width + [clear])
    return rows


def placeholder(width, height):
    """Opaque rows: each glow fades linearly from its centre to its colour's full radius."""
    rows = []
    reach = (width ** 2 + height ** 2) ** 0.5 * 0.75
    for y in range(height):
        row = []
        for x in range(width):
            pixel = list(PLACEHOLDER_BASE)
            for colour, alpha, (cx, cy) in GLOWS:
                distance = ((x + 0.5 - cx * width) ** 2 + (y + 0.5 - cy * height) ** 2) ** 0.5
                a = alpha * max(0.0, 1 - distance / reach)
                pixel = [round(p * (1 - a) + c * a) for p, c in zip(pixel, colour)]
            row.append(tuple(pixel) + (255,))
        rows.append(row)
    return rows


def circle_ring(size, width):
    def covered(x, y, size):
        r = size / 2
        d = ((x - r) ** 2 + (y - r) ** 2) ** 0.5
        return r - width <= d <= r
    return [[WHITE + (a,) for a in line] for line in coverage(size, covered)]


def magnifier(size):
    """A ring in the upper left and a handle to the lower right, 3 px strokes
    (SF's semibold weight at this size)."""
    stroke = 3.0
    r = size * 0.30
    cx = cy = size * 0.40

    def covered(x, y, size):
        d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
        if r - stroke / 2 <= d <= r + stroke / 2:
            return True
        # The handle: a capsule from the ring's edge along the diagonal.
        t0, t1 = r + stroke / 2 - 1, size * 0.62
        u = ((x - cx) + (y - cy)) / 2 ** 0.5
        v = ((x - cx) - (y - cy)) / 2 ** 0.5
        return t0 <= u <= t1 and abs(v) <= stroke / 2 + 0.4
    return [[WHITE + (a,) for a in line] for line in coverage(size, covered, scale=GLYPH_SCALE)]


def scrim(width, height, alpha_at):
    return [[BACKGROUND + (alpha_at(x, y),) for x in range(width)] for y in range(height)]


def piecewise(stops, at):
    """Linear interpolation through (position, value) stops, sorted by position."""
    for (p0, v0), (p1, v1) in zip(stops, stops[1:]):
        if at <= p1:
            return v0 + (v1 - v0) * (at - p0) / (p1 - p0)
    return stops[-1][1]


def backdrop_fade_bottom():
    """Black over the backdrop box: 1 less the art's alpha at each row's centre."""
    return scrim(2, BACKDROP_HEIGHT, lambda x, y: round(255 * (1 - piecewise(BACKDROP_STOPS, y + 0.5))))


def wash_weight(y, foot):
    """The wash's strength at y: 1 to WASH_TOP, falling linearly to 0 at foot."""
    return min(max((foot - y) / (foot - WASH_TOP), 0.0), 1.0)


def hero_fade_left(foot):
    """scrim_left's alpha across, the wash's weight down, in grey."""
    rows = []
    for row in range(BACKDROP_HEIGHT // FADE_LEFT_ROW):
        grey = round(255 * wash_weight((row + 0.5) * FADE_LEFT_ROW, foot))
        rows.append([(grey, grey, grey, round(255 * (1 - x / (FADE_LEFT_COLUMNS - 1)))) for x in range(FADE_LEFT_COLUMNS)])
    return rows


def hero_fade_bottom(foot):
    """backdrop_fade_bottom's alpha, the wash's weight in grey."""
    rows = []
    for y in range(BACKDROP_HEIGHT):
        grey = round(255 * wash_weight(y + 0.5, foot))
        alpha = round(255 * (1 - piecewise(BACKDROP_STOPS, y + 0.5)))
        rows.append([(grey, grey, grey, alpha)] * 2)
    return rows


def glow(size, centre):
    """White, alpha 1 at centre (a fraction of size) falling linearly to 0 at
    the ellipse whose radii reach the image's far edges from it."""
    width, height = size
    cx, cy = centre[0] * width, centre[1] * height
    rx, ry = max(cx, width - cx), max(cy, height - cy)
    out = []
    for y in range(height):
        line = []
        for x in range(width):
            d = math.hypot((x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry)
            line.append(WHITE + (round(255 * max(0.0, 1 - d)),))
        out.append(line)
    return out


def top_scrim():
    height, top = TOP_SCRIM
    return scrim(2, height, lambda x, y: round(255 * top * (1 - (y + 0.5) / height)))


def card_shadow(sigma, margin):
    """A blurred rectangle margin px inside the image edge, as a 9-patch whose
    corners hold the whole falloff; corner rounding under the blur is ignored."""
    fixed = margin + 3 * sigma  # edge to where the blurred edge is solid
    size = 2 * fixed + STRETCH

    def edge(d):  # Gaussian-blurred step at the card's edge, d px from the image edge
        return 0.5 * (1 + math.erf((d + 0.5 - margin) / (sigma * 2 ** 0.5)))

    def along(i):
        return edge(min(i, size - 1 - i))
    return [[BACKGROUND + (round(255 * SHADOW_ALPHA * along(x) * along(y)),) for x in range(size)] for y in range(size)]


def cast_shadow(diameter=200):
    """Radial falloff for round cast portraits, with the Home card shadow's
    opacity, sigma, and margin; a regular PNG so it cannot stretch square."""
    size = diameter + 2 * SHADOW_MARGIN
    centre = size / 2
    return [[BACKGROUND + (round(255 * SHADOW_ALPHA * 0.5 * math.erfc(
        (math.hypot(x + 0.5 - centre, y + 0.5 - centre) - diameter / 2)
        / (SHADOW_SIGMA * 2 ** 0.5))),) for x in range(size)] for y in range(size)]


def over(top, bottom):
    """Straight-alpha (rgb, a) of top composited over bottom."""
    (rt, at), (rb, ab) = top, bottom
    a = at + ab * (1 - at)
    if a == 0:
        return (0, 0, 0), 0.0
    return tuple((ct * at + cb * ab * (1 - at)) / a for ct, cb in zip(rt, rb)), a


def bordered(width, height, radius, fill_at, border_at, band=STRETCH):
    """RGBA rows of a rounded rectangle with a 1 px border. fill_at and
    border_at give (rgb, alpha) for t, which runs 0 to 1 across the middle band
    rows (0 above it, 1 below)."""
    fill = coverage(width, lambda x, y, w: inside_rounded_rect(x, y, w, 0, radius, height), height)
    inner = coverage(width, lambda x, y, w: inside_rounded_rect(x, y, w, 1, radius - 1, height), height)
    first = (height - band) // 2
    rows = []
    for y in range(height):
        t = min(max((y + 0.5 - first) / band, 0.0), 1.0)
        (fill_rgb, fill_alpha), (border_rgb, border_alpha) = fill_at(t), border_at(t)
        row = []
        for x in range(width):
            ring = (fill[y][x] - inner[y][x]) / 255
            rgb, a = over((border_rgb, border_alpha * ring), (fill_rgb, fill_alpha * fill[y][x] / 255))
            row.append(tuple(round(c) for c in rgb) + (round(255 * a),))
        rows.append(row)
    return rows


def chip(radius, style=CHIP):
    """A rounded rectangle 9-patch in one fill and 1 px border: a badge chip,
    a dialog button at rest, or a dialog card."""
    _, fill, border = style
    return bordered(2 * radius + STRETCH, 2 * radius + STRETCH, radius, lambda t: fill, lambda t: border)


def rounded(radius):
    return coverage(2 * radius + STRETCH, lambda x, y, size: inside_rounded_rect(x, y, size, 0, radius))


def panel(radius):
    (top, top_alpha, top_border), (bottom, bottom_alpha, bottom_border) = PANEL_TOP, PANEL_BOTTOM

    def fill_at(t):
        return tuple(a + (b - a) * t for a, b in zip(top, bottom)), top_alpha + (bottom_alpha - top_alpha) * t

    def border_at(t):
        return WHITE, top_border + (bottom_border - top_border) * t
    return bordered(2 * radius + STRETCH, 2 * radius + PANEL_BAND, radius, fill_at, border_at, PANEL_BAND)


def capsule(height, ring):
    """A capsule 9-patch's alpha: radius half the height less 1 px, as scripts/first-run-art.py draws them."""
    radius = height // 2 - 1
    if ring:
        return focus_ring(radius, ring)
    return coverage(2 * radius + STRETCH, lambda x, y, size: inside_rounded_rect(x, y, size, 0, radius))


def check_disc(size):
    """An INK disc with a black check: SF checkmark at half the disc, bold."""
    half_stroke = size * 0.04
    points = [(size * 0.275, size * 0.52), (size * 0.425, size * 0.67), (size * 0.725, size * 0.33)]

    def segment_distance(x, y, a, b):
        (ax, ay), (bx, by) = a, b
        t = max(0.0, min(1.0, ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2)))
        return ((x - ax - t * (bx - ax)) ** 2 + (y - ay - t * (by - ay)) ** 2) ** 0.5

    def on_check(x, y, size):
        return min(segment_distance(x, y, a, b) for a, b in zip(points, points[1:])) <= half_stroke

    def on_disc(x, y, size):
        return (x - size / 2) ** 2 + (y - size / 2) ** 2 <= (size / 2) ** 2
    disc = coverage(size, on_disc, scale=GLYPH_SCALE)
    check = coverage(size, on_check, scale=GLYPH_SCALE)
    rows = []
    for d_line, c_line in zip(disc, check):
        row = []
        for d, c in zip(d_line, c_line):
            # The check is drawn on the disc, so its coverage darkens the ink.
            k = min(c, d) / 255
            row.append(tuple(round(i * (1 - k)) for i in INK) + (d,))
        rows.append(row)
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
    for res, radius, width in (("fhd", CARD_RADIUS, RING_WIDTH), ("hd", hd(CARD_RADIUS), hd(RING_WIDTH))):
        yield f"card_frame_{res}.9.png", nine_patch(card_frame(radius), BACKGROUND)
        yield f"focus_ring_{res}.9.png", nine_patch(focus_ring(radius, width), FOCUS_RING)
    yield "scrim_left.png", scrim(RAMP, 2, lambda x, y: 255 - x)
    yield "scrim_bottom.png", scrim(2, RAMP, lambda x, y: y)
    yield "card_placeholder.png", placeholder(*PLACEHOLDER)
    yield "search_glyph.png", magnifier(GLYPH)
    yield "backdrop_fade_bottom.png", backdrop_fade_bottom()
    yield "top_scrim.png", top_scrim()
    for page, foot in WASH_FEET:
        yield f"{page}_fade_left.png", hero_fade_left(foot)
        yield f"{page}_fade_bottom.png", hero_fade_bottom(foot)
    yield "wash_fade.png", [[WHITE + (255 - y,)] * 2 for y in range(RAMP)]
    yield "ambient_glow_half.png", glow(GLOW_HALF, (0.5, 1.0))
    yield "ambient_glow_quarter.png", glow(GLOW_QUARTER, (0.0, 1.0))
    yield "flat_fade_left.png", [[WHITE + (255 - x,) for x in range(RAMP)]] * 2
    yield "flat_fade_bottom.png", [[WHITE + (round(255 * (1 - piecewise(BACKDROP_STOPS, y + 0.5))),)] * 2 for y in range(BACKDROP_HEIGHT)]
    for res, scale in (("fhd", lambda px: px), ("hd", hd)):
        yield f"still_frame_{res}.9.png", nine_patch(card_frame(scale(STILL_RADIUS)), BACKGROUND)
        yield f"card_shadow_{res}.9.png", nine_patch_rgba(card_shadow(scale(SHADOW_SIGMA), scale(SHADOW_MARGIN)))
        yield f"chip_{res}.9.png", nine_patch_rgba(chip(scale(CHIP[0])))
        for radius in (22, 18):
            yield f"panel_{radius}_{res}.9.png", nine_patch_rgba(panel(scale(radius)), PANEL_BAND)
        yield f"tab_fill_{res}.9.png", nine_patch(capsule(scale(TAB), 0), WHITE)
        yield f"tab_ring_{res}.9.png", nine_patch(capsule(scale(TAB), 1), WHITE)
    for radius, height in ((CARD_RADIUS, 4), (STILL_RADIUS, 6)):
        yield f"progress_{radius}_{height}.9.png", progress_track(radius, height)
    yield "check_disc.png", check_disc(CHECK_DISC)
    yield "circle_ring_3.png", circle_ring(CIRCLE, AVATAR_RING)
    yield "cast_shadow.png", cast_shadow()
    for res, scale in (("fhd", lambda px: px), ("hd", hd)):
        for radius in ROW_RADII:
            yield f"rounded_{radius}_{res}.9.png", nine_patch(rounded(scale(radius)), WHITE)
        yield f"button_14_{res}.9.png", nine_patch_rgba(chip(scale(BUTTON[0]), BUTTON))
        yield f"dialog_30_{res}.9.png", nine_patch_rgba(chip(scale(DIALOG[0]), DIALOG))


def main():
    out = pathlib.Path(__file__).resolve().parent.parent / "images" / "ui"
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in images():
        (out / name).write_bytes(png(rows))
        print(f"images/ui/{name}  {len(rows[0])}x{len(rows)}")


if __name__ == "__main__":
    main()
