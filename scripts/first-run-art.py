#!/usr/bin/env python3
"""Write the first-run, profile, and PIN screens' generated art into images/firstrun/.

  mesh_setup.png          the brand light behind server setup and sign-in: a
                          3x3 colour mesh of #0034FB, #F50B4F, and #FD7403
                          mixed toward black, light on the right, darkened on
                          the left and at the bottom (spec section 5.4)
  mesh_profiles.png       the same light, warmer and lower, behind the profile
                          picker and the PIN screen, darkened towards the bottom
  capsule_{76,60}_{fill,ring}_{fhd,hd}.9.png, capsule_52_fill_{fhd,hd}.9.png
                          capsules for buttons (76 px), chips (60 px), and
                          a series' season capsules (52 px), filled or (76
                          and 60) as a 2 px outline
  rounded_16_{fill,ring}_{fhd,hd}.9.png, rounded_40_fill_{fhd,hd}.9.png
                          rounded rectangles for fields (radius 16), filled
                          or as a 2 px outline, and the card (radius 40)
  avatar_disc.png         a 220 px white disc, tinted with the profile's colour,
                          and the mask that rounds an avatar image
  avatar_shade.png        light top left and shade bottom right over the disc,
                          with a 2 px white 14% outline, as the apps draw it
  avatar_ring.png         the focused avatar's 6 px ring, its outer edge
                          12 px outside a 220 px avatar (244 px), as tvOS
                          draws it
  lock_badge.png          the 60 px padlock badge of a PIN-locked profile
  pin_dot.png, pin_dot_ring.png
                          a 26 px PIN dot, filled or as a 3 px outline
  add_ring.png            the picker's Add profile tile: a 220 px circle's
                          2 px dashed outline (6 px dashes, 5 px gaps), as
                          tvOS's AddProfileTile strokes it
  add_plus.png            its 66 px plus, light weight
  spinner.png             the 128 px loading spinner (spec section 5.8)

tvOS's first-run art (spec section 5.4, silo-apple b90a86ea; AG-222):

  {capsule_{76,52},rounded_{16,40,12}}_line_{fhd,hd}.9.png
                          1 px outlines of the button, the TV-name chip, the
                          field, the card, and the person page's portrait,
                          as tvOS strokes them
  rounded_16_ring3_{fhd,hd}.9.png
                          a field's 3 px error outline
  rounded_30_{fill,line}_{fhd,hd}.9.png
                          the sign-in server card, radius 30
  capsule_36_{fill,line}_{fhd,hd}.9.png
                          the server card's badge and the KIDS badge
  server_mark.png         the server card's 80 px mark: a rounded square
                          (radius 20) shaded #EAA65C to #A8521D to #5E290D
                          from top left to bottom right, with a 1 px white
                          18% outline, under the server's initial
  warning_triangle.png    an error state's 48 px warning triangle, white, with
                          the exclamation mark cut out

tvOS's phone-first setup, code sign-in, and pairing screens (silo-apple
6fb70758: TVServerSetupView, TVLoginView, TVPairingReceiverView, MarqueeTV):

  glyph_*.png             line glyphs in white, after the SF Symbols the
                          screens name, drawn at 2x (GLYPH_SCALE) so a
                          Poster sets their size in FHD px: globe, person,
                          lock, key, qrcode, phone (iphone.gen3), tv, and
                          retry (arrow.clockwise) at 32; eye and eye_slash at
                          40; gear (gearshape), check, and number at 28;
                          check_large at 64 (the 140 px card's checkmark);
                          phone_large, wifi_alert (wifi.exclamationmark),
                          pause_circle, xmark_circle, and alert_large
                          (exclamationmark.triangle) at 52 for the card's
                          112 px symbol circle
  card_symbol{,_96,_140}.png
                          the card's glass circle at 112, 96, and 140 px:
                          white 8% with a 1 px white 14% outline
  step_tile.png           a setup step's 168 px tile: radius 34, white 6%
                          with a 1 px white 14% outline
  step_badge.png          a step's number disc: a 52 px white disc at (11, 6)
                          in a 74x76 canvas, over a black 50% shadow 6 px
                          lower, blurred as SwiftUI's radius 7 (sigma 3.5)
  step_app_icon.png       the Silo app icon, 92 px at 2x: #010D9F
                          (siloIconField), radius 22, a 1 px white 18%
                          outline, and the Silo mark 77 px tall, embedded
                          from silo-branding's logo/svg/silo-mark-flat.svg
                          (needs rsvg-convert and magick, and the branding
                          checkout as the first argument; without it the
                          committed file is kept)
  step_done.png           the last step's 96 px check at 2x, in #30D158
                          (tvOS siloSuccess, the system green): the disc at
                          16%, a 3 px outline, and a bold checkmark
  rounded_{20,24}_fill_{fhd,hd}.9.png, rounded_20_line_{fhd,hd}.9.png
                          the Set Up picture's card (radius 20) and the QR
                          code's white frame (radius 24)
  capsule_30_fill_{fhd,hd}.9.png
                          the picture's 30 px Set Up button
  capsule_30_ring4_{fhd,hd}.9.png
                          its 4 px ring, 38 px tall, drawn 4 px outside it
  dot_10.png              a 10 px waiting dot

Everything is white or greyscale unless it carries a fixed colour, so screens
tint it with a Poster's blendColor and opacity. The mesh follows the Android
TV app's MarqueeBackdrop at rest: the middle palette ("all three colours once
the server answers") for setup, the last one for profiles, mirrored so the
light pools on the right behind the card, with the TV scrim baked in. It is
drawn at 640x360 and stretched by the Poster, with a 4x4 ordered dither so
the dark ramps do not band. Shapes are plain geometry, not brand assets.

The 9-patches follow scripts/ui-art.py: HD sizes are the FHD sizes times 2/3,
each stretches a 2 px band in the middle, and the whole image is content. A
capsule's radius is half its height less 1 px, so the corners and the band fit
the height exactly.

Edges are antialiased analytically. Uses only the standard library, so the
pixels are the same on every machine, except step_app_icon.png's mark. Run
from anywhere:
python3 scripts/first-run-art.py [/path/to/silo-branding]
"""
import math
import pathlib
import shutil
import struct
import subprocess
import sys
import zlib

BLUE = (0x00, 0x34, 0xFB)
RED = (0xF5, 0x0B, 0x4F)
ORANGE = (0xFD, 0x74, 0x03)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
INK = (0xED, 0xED, 0xED)
STRETCH = 2

AVATAR = 220
AVATAR_RING_GAP = 6
AVATAR_RING_WIDTH = 6
LOCK_BADGE = 60
PIN_DOT = 26
PIN_DOT_RING = 3
SPINNER = 128
MESH_SIZE = (640, 360)
ADD_RING_WIDTH = 2
ADD_DASH = 6
ADD_GAP = 5
ADD_PLUS = 66
ADD_PLUS_STROKE = 4
SERVER_MARK = 80
HELP_SYMBOL = 112
WARNING = (56, 48)
# Only the lock, remote and warning use 2x intrinsic resolution. Their geometry
# stays in logical FHD pixels; meshes, masks, rings and other shapes stay 1x.
GLYPH_SCALE = 2
MARK_GRADIENT = [(0xEA, 0xA6, 0x5C), (0xA8, 0x52, 0x1D), (0x5E, 0x29, 0x0D)]


def hd(fhd_px):
    return round(fhd_px * 2 / 3)


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def lerp(a, b, t):
    return a + (b - a) * t


def mix(color, other, t):
    return tuple(lerp(c, o, t) for c, o in zip(color, other))


def rounded_rect_distance(x, y, width, height, radius):
    """Signed distance from (x, y) to a width x height rectangle at the origin with corner radius."""
    qx = abs(x - width / 2) - (width / 2 - radius)
    qy = abs(y - height / 2) - (height / 2 - radius)
    outside = math.hypot(max(qx, 0.0), max(qy, 0.0))
    return outside + min(max(qx, qy), 0.0) - radius


def shape_alpha(width, height, radius, ring=0, inset=0, scale=1):
    """Coverage rows of a rounded rectangle inset from the image edge, or of its outline ring px wide."""
    rows = []
    for py in range(height * scale):
        row = []
        for px in range(width * scale):
            x, y = (px + 0.5) / scale - inset, (py + 0.5) / scale - inset
            w, h = width - 2 * inset, height - 2 * inset
            outer = clamp(0.5 - scale * rounded_rect_distance(x, y, w, h, radius))
            if ring:
                inner = clamp(0.5 - scale * rounded_rect_distance(x - ring, y - ring, w - 2 * ring, h - 2 * ring, max(radius - ring, 0)))
                outer = max(outer - inner, 0.0)
            row.append(outer)
        rows.append(row)
    return rows


def disc_alpha(size, radius, ring=0, scale=1):
    return shape_alpha(size, size, radius, ring, inset=size / 2 - radius, scale=scale)


def nine_patch(alpha, rgb=WHITE):
    """RGBA rows with the 1 px 9-patch border: stretch marks top and left, full content right and bottom."""
    height, width = len(alpha), len(alpha[0])
    clear, mark = (0, 0, 0, 0), (0, 0, 0, 255)
    first_x = (width - STRETCH) // 2 + 1
    first_y = (height - STRETCH) // 2 + 1
    rows = [[mark if first_x <= x < first_x + STRETCH else clear for x in range(width + 2)]]
    for y, line in enumerate(alpha, start=1):
        side = mark if first_y <= y < first_y + STRETCH else clear
        rows.append([side] + [rgb + (round(255 * a),) for a in line] + [mark])
    rows.append([clear] + [mark] * width + [clear])
    return rows


def rounded_nine_patches(name, radius_fhd, radius_hd, with_ring=True):
    for res, radius in (("fhd", radius_fhd), ("hd", radius_hd)):
        size = 2 * radius + STRETCH
        ring = 2 if res == "fhd" else hd(2)
        yield f"{name}_fill_{res}.9.png", nine_patch(shape_alpha(size, size, radius))
        if with_ring:
            yield f"{name}_ring_{res}.9.png", nine_patch(shape_alpha(size, size, radius, ring))


def capsule_nine_patches(height, with_ring=True):
    yield from rounded_nine_patches(f"capsule_{height}", height // 2 - 1, hd(height) // 2 - 1, with_ring)


def line_nine_patches(name, radius_fhd, radius_hd, ring_fhd, suffix="line"):
    """Outlines ring_fhd px wide in FHD, at least 1 px in HD."""
    for res, radius in (("fhd", radius_fhd), ("hd", radius_hd)):
        size = 2 * radius + STRETCH
        ring = ring_fhd if res == "fhd" else max(hd(ring_fhd), 1)
        yield f"{name}_{suffix}_{res}.9.png", nine_patch(shape_alpha(size, size, radius, ring))


def capsule_line_nine_patches(height):
    yield from line_nine_patches(f"capsule_{height}", height // 2 - 1, hd(height) // 2 - 1, 1)


def rgba(alpha, color):
    return [[tuple(round(c) for c in color) + (round(255 * a),) for a in line] for line in alpha]


def avatar_shade():
    """The apps' radial gradient over a tint disc, as a white or black overlay.

    The apps blend from the tint lightened 35% towards white at (0.3, 0.25)
    of the disc, through the tint at half the 0.8-wide radius, to the tint
    darkened 45% towards black. Over a disc of the tint, white at 35% x (1 - 2t)
    and then black at 45% x (2t - 1) give exactly those colours. The outline
    is laid over that.
    """
    cover = disc_alpha(AVATAR, AVATAR / 2)
    outline = disc_alpha(AVATAR, AVATAR / 2, ring=2)
    rows = []
    for py in range(AVATAR):
        row = []
        for px in range(AVATAR):
            t = clamp(math.hypot(px + 0.5 - AVATAR * 0.3, py + 0.5 - AVATAR * 0.25) / (AVATAR * 0.8))
            color, alpha = (WHITE, 0.35 * (1 - 2 * t)) if t < 0.5 else (BLACK, 0.45 * (2 * t - 1))
            edge = 0.14 * outline[py][px]
            # The outline over the shade, both in straight alpha.
            total = edge + alpha * (1 - edge)
            if total > 0:
                color = tuple((w * edge + c * alpha * (1 - edge)) / total for w, c in zip(WHITE, color))
            row.append(tuple(round(c) for c in color) + (round(255 * total * cover[py][px]),))
        rows.append(row)
    return rows


def avatar_ring():
    size = AVATAR + 2 * (AVATAR_RING_GAP + AVATAR_RING_WIDTH)
    return rgba(disc_alpha(size, size / 2, ring=AVATAR_RING_WIDTH), WHITE)


def lock_badge(scale=GLYPH_SCALE):
    """#1C1C1E disc with a black edge and a padlock in #EDEDED at 75%."""
    size = LOCK_BADGE
    disc = disc_alpha(size, size / 2, scale=scale)
    edge = disc_alpha(size, size / 2, ring=round(size * 0.07), scale=scale)
    glyph = size * 0.42
    left, top = (size - glyph) / 2, (size - glyph) / 2
    stroke = glyph * 0.16
    body_top = top + glyph * 0.45
    rows = []
    for py in range(size * scale):
        row = []
        for px in range(size * scale):
            x, y = (px + 0.5) / scale, (py + 0.5) / scale
            color = mix((0x1C, 0x1C, 0x1E), BLACK, edge[py][px])
            # The body: a rounded rectangle in the lower part of the glyph box.
            body = clamp(0.5 - scale * rounded_rect_distance(x - left, y - body_top, glyph, glyph * 0.55, glyph * 0.1))
            # The shackle: the upper half of a ring above the body.
            cx, cy, r = size / 2, body_top, glyph * 0.3
            arc = clamp(0.5 - scale * (abs(math.hypot(x - cx, y - cy) - r) - stroke / 2)) if y <= cy else 0.0
            ink = max(body, arc) * 0.75
            color = mix(color, INK, ink)
            row.append(tuple(round(c) for c in color) + (round(255 * disc[py][px]),))
        rows.append(row)
    return rows


def add_ring():
    """A 2 px outline inside the 220 px circle, dashed evenly: 6 px on, 5 px off along its middle."""
    size, width = AVATAR, ADD_RING_WIDTH
    ring = disc_alpha(size, size / 2, ring=width)
    radius = size / 2 - width / 2
    periods = round(2 * math.pi * radius / (ADD_DASH + ADD_GAP))
    period = 2 * math.pi * radius / periods
    dash = period * ADD_DASH / (ADD_DASH + ADD_GAP)
    rows = []
    for py in range(size):
        row = []
        for px in range(size):
            angle = math.atan2(py + 0.5 - size / 2, px + 0.5 - size / 2) % (2 * math.pi)
            along = (angle * radius) % period
            # Coverage across the dash's two ends, antialiased over a pixel.
            cover = clamp(min(along + 0.5, dash - along + 0.5, 1.0))
            if along > dash + 0.5:
                cover = clamp(along - period + 0.5)
            row.append(WHITE + (round(255 * ring[py][px] * cover),))
        rows.append(row)
    return rows


def add_plus(scale=GLYPH_SCALE):
    """A plus ADD_PLUS px across with ADD_PLUS_STROKE px round-ended strokes."""
    size, stroke = ADD_PLUS, ADD_PLUS_STROKE
    half = size / 2
    rows = []
    for py in range(size * scale):
        row = []
        for px in range(size * scale):
            x, y = (px + 0.5) / scale, (py + 0.5) / scale
            reach = half - stroke / 2
            across = segment_distance(x, y, half - reach, half, half + reach, half)
            down = segment_distance(x, y, half, half - reach, half, half + reach)
            cover = clamp(0.5 - scale * (min(across, down) - stroke / 2))
            row.append(WHITE + (round(255 * cover),))
        rows.append(row)
    return rows


def spinner():
    """A 10 px arc of three quarters of a circle that fades out towards its tail."""
    size, width = SPINNER, 10
    ring = disc_alpha(size, size / 2 - 2, ring=width)
    rows = []
    for py in range(size):
        row = []
        for px in range(size):
            angle = math.atan2(py + 0.5 - size / 2, px + 0.5 - size / 2)
            sweep = ((angle + math.pi / 2) % (2 * math.pi)) / (2 * math.pi)
            fade = clamp((sweep - 0.25) / 0.75)
            row.append(INK + (round(255 * ring[py][px] * fade),))
        rows.append(row)
    return rows


def server_mark():
    """tvOS's MarqueeServerMark without branding: its warm gradient on a rounded square."""
    size = SERVER_MARK
    cover = shape_alpha(size, size, size * 0.25)
    outline = shape_alpha(size, size, size * 0.25, ring=1)
    rows = []
    for py in range(size):
        row = []
        for px in range(size):
            t = clamp(((px + 0.5) + (py + 0.5)) / (2 * size))
            color = mix(MARK_GRADIENT[0], MARK_GRADIENT[1], t * 2) if t < 0.5 else mix(MARK_GRADIENT[1], MARK_GRADIENT[2], t * 2 - 1)
            color = mix(color, WHITE, 0.18 * outline[py][px])
            row.append(tuple(round(c) for c in color) + (round(255 * cover[py][px]),))
        rows.append(row)
    return rows


def segment_distance(x, y, ax, ay, bx, by):
    """Distance from (x, y) to the segment from (ax, ay) to (bx, by)."""
    dx, dy = bx - ax, by - ay
    t = clamp(((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)) if dx or dy else 0.0
    return math.hypot(x - ax - t * dx, y - ay - t * dy)


def warning_triangle(scale=GLYPH_SCALE):
    """exclamationmark.triangle.fill: a triangle with rounded corners, white,
    with the mark cut out, for blendColor."""
    width, height = WARNING
    radius = 5
    corners = [(width / 2, radius + 1), (width - radius - 1, height - radius - 1), (radius + 1, height - radius - 1)]
    rows = []
    for py in range(height * scale):
        row = []
        for px in range(width * scale):
            x, y = (px + 0.5) / scale, (py + 0.5) / scale
            inside = all((bx - ax) * (y - ay) - (by - ay) * (x - ax) >= 0
                         for (ax, ay), (bx, by) in zip(corners, corners[1:] + corners[:1]))
            edge = min(segment_distance(x, y, *a, *b) for a, b in zip(corners, corners[1:] + corners[:1]))
            distance = -edge if inside else edge
            shape = clamp(0.5 - scale * (distance - radius))
            bar = clamp(0.5 - scale * (segment_distance(x, y, width / 2, height * 0.36, width / 2, height * 0.62) - 2.5))
            dot = clamp(0.5 - scale * (math.hypot(x - width / 2, y - height * 0.77) - 3))
            row.append(WHITE + (round(255 * shape * (1 - max(bar, dot))),))
        rows.append(row)
    return rows


# --- Onboarding glyphs ------------------------------------------------------
#
# Each glyph is a function of (x, y) in logical FHD px giving the ink's
# coverage there, sampled at GLYPH_SCALE. Line work is a distance to its
# centre line, stroked to a width; fills are signed distances.

ICON_FIELD = (0x01, 0x0D, 0x9F)
SUCCESS = (0x30, 0xD1, 0x58)


def stroked(distance, stroke, scale):
    return clamp(0.5 - scale * (distance - stroke / 2))


def filled(signed, scale):
    return clamp(0.5 - scale * signed)


def ring_distance(x, y, cx, cy, r):
    return abs(math.hypot(x - cx, y - cy) - r)


def arc_distance(x, y, cx, cy, r, start, end):
    """Distance to the arc from start to end degrees, clockwise on screen (y down)."""
    angle = math.degrees(math.atan2(y - cy, x - cx))
    span = (end - start) % 360 or 360
    if (angle - start) % 360 <= span:
        return ring_distance(x, y, cx, cy, r)
    ends = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in (start, end)]
    return min(math.hypot(x - ex, y - ey) for ex, ey in ends)


def ellipse_distance(x, y, cx, cy, rx, ry):
    """Approximate distance to an ellipse's outline: its implicit value over its gradient."""
    dx, dy = (x - cx) / rx, (y - cy) / ry
    length = math.hypot(dx, dy)
    if length == 0:
        return min(rx, ry)
    gradient = math.hypot(dx / rx, dy / ry) / length
    return abs(length - 1) / gradient


def polyline_distance(x, y, points):
    return min(segment_distance(x, y, *a, *b) for a, b in zip(points, points[1:]))


def rect_outline_distance(x, y, left, top, width, height, radius):
    return abs(rounded_rect_distance(x - left, y - top, width, height, radius))


def rect_signed(x, y, left, top, width, height, radius):
    return rounded_rect_distance(x - left, y - top, width, height, radius)


def glyph(size, cover, scale=GLYPH_SCALE):
    """White rows of a size px glyph whose coverage at (x, y) is cover(x, y, scale)."""
    rows = []
    for py in range(size * scale):
        row = []
        for px in range(size * scale):
            row.append(WHITE + (round(255 * clamp(cover((px + 0.5) / scale, (py + 0.5) / scale, scale))),))
        rows.append(row)
    return rows


def globe(x, y, s):
    stroke = 2.4
    d = min(ring_distance(x, y, 16, 16, 13), ellipse_distance(x, y, 16, 16, 5.6, 13))
    for line_y in (10, 22):
        reach = math.sqrt(13 ** 2 - (line_y - 16) ** 2)
        d = min(d, segment_distance(x, y, 16 - reach, line_y, 16 + reach, line_y))
    return stroked(d, stroke, s)


def person(x, y, s):
    stroke = 2.4
    d = ring_distance(x, y, 16, 10, 5.5)
    shoulders = arc_distance(x, y, 16, 28.5, 10.5, 180, 360)
    d = min(d, shoulders, segment_distance(x, y, 5.5, 28.5, 26.5, 28.5))
    return stroked(d, stroke, s)


def lock(x, y, s):
    stroke = 2.4
    d = rect_outline_distance(x, y, 7, 14.5, 18, 14.5, 3.5)
    d = min(d, arc_distance(x, y, 16, 10.5, 5.5, 180, 360),
            segment_distance(x, y, 10.5, 10.5, 10.5, 14.5), segment_distance(x, y, 21.5, 10.5, 21.5, 14.5))
    return stroked(d, stroke, s)


def lock_open(x, y, s):
    """lock.open: the body, its shackle lifted and swung open to the right."""
    stroke = 2.4
    d = rect_outline_distance(x, y, 4, 14.5, 18, 14.5, 3.5)
    d = min(d, arc_distance(x, y, 24, 8.5, 5.5, 180, 360),
            segment_distance(x, y, 18.5, 8.5, 18.5, 14.5), segment_distance(x, y, 29.5, 8.5, 29.5, 11.5))
    return stroked(d, stroke, s)


def eye_shape(x, y, size):
    """The eye's almond outline and pupil, scaled from a 40 px box."""
    k = size / 40
    chord, sag = 16 * k, 10 * k
    radius = (chord ** 2 + sag ** 2) / (2 * sag)
    mid = 20 * k
    if y <= mid:
        lid = ring_distance(x, y, mid, mid - sag + radius, radius)
    else:
        lid = ring_distance(x, y, mid, mid + sag - radius, radius)
    corners = min(math.hypot(x - (mid - chord), y - mid), math.hypot(x - (mid + chord), y - mid))
    if abs(x - mid) > chord:
        lid = corners
    return lid, math.hypot(x - mid, y - mid) - 5.5 * k


def eye(x, y, s):
    lid, pupil = eye_shape(x, y, 40)
    return max(stroked(lid, 2.6, s), filled(pupil, s))


def eye_slash(x, y, s):
    lid, pupil = eye_shape(x, y, 40)
    ink = max(stroked(lid, 2.6, s), filled(pupil, s))
    line = segment_distance(x, y, 8, 6, 32, 34)
    # The eye is cut back on the slash's lower side, as SF Symbols draw it.
    cut = stroked(segment_distance(x, y, 9.8, 4.6, 33.8, 32.6), 2.6 * 1.6, s)
    return max(ink * (1 - cut), stroked(line, 2.6, s))


def key(x, y, s):
    """key: upright, the bow on top and two teeth on the shaft's right."""
    stroke = 2.4
    d = min(ring_distance(x, y, 16, 9.5, 6),
            segment_distance(x, y, 16, 15.5, 16, 29),
            segment_distance(x, y, 16, 23.5, 20.5, 23.5),
            segment_distance(x, y, 16, 28, 19.5, 28))
    return stroked(d, stroke, s)


def qrcode(x, y, s):
    ink = 0.0
    for left, top in ((3, 3), (19, 3), (3, 19)):
        ink = max(ink, stroked(rect_outline_distance(x, y, left + 1.2, top + 1.2, 7.6, 7.6, 1.6), 2.4, s),
                  filled(rect_signed(x, y, left + 3.5, top + 3.5, 3, 3, 0.6), s))
    for left, top in ((19.5, 19.5), (25.5, 19.5), (22.5, 22.5), (19.5, 25.5), (25.5, 25.5)):
        ink = max(ink, filled(rect_signed(x, y, left, top, 3.2, 3.2, 0.6), s))
    return ink


def phone_glyph(size):
    k = size / 32
    width, height, stroke = 14 * k, 26 * k, 2.4 * k
    if size > 32:
        width, height = 26, 48
        stroke = 3.4
    left, top = (size - width) / 2, (size - height) / 2
    radius = width * 0.3

    def cover(x, y, s):
        d = rect_outline_distance(x, y, left + stroke / 2, top + stroke / 2, width - stroke, height - stroke, radius - stroke / 2)
        notch = segment_distance(x, y, size / 2 - width * 0.14, top + height * 0.12, size / 2 + width * 0.14, top + height * 0.12)
        return max(stroked(d, stroke, s), stroked(notch, stroke * 0.85, s))
    return cover


def tv(x, y, s):
    stroke = 2.4
    d = min(rect_outline_distance(x, y, 3.2, 5.2, 25.6, 18, 3), segment_distance(x, y, 11, 27.5, 21, 27.5))
    return stroked(d, stroke, s)


def gear(x, y, s):
    cx = cy = 14
    angle = math.atan2(y - cy, x - cx)
    teeth = clamp(math.cos(8 * angle) * 2.2 + 0.4, -1, 1)
    outer = 9.6 + 1.9 * teeth
    body = abs(math.hypot(x - cx, y - cy) - outer)
    return max(stroked(body, 2.2, s), stroked(ring_distance(x, y, cx, cy, 3.6), 2.2, s))


def check(x, y, s):
    return stroked(polyline_distance(x, y, [(6, 14.5), (11.5, 20.5), (22.5, 7.5)]), 3, s)


def check_large(x, y, s):
    return stroked(polyline_distance(x, y, [(13, 33), (26, 46), (51, 19)]), 7, s)


def retry(x, y, s):
    stroke = 2.4
    d = min(arc_distance(x, y, 16, 17, 10, -50, 270),
            polyline_distance(x, y, [(13, 3), (17.5, 7), (13, 11)]))
    return stroked(d, stroke, s)


def number(x, y, s):
    d = min(segment_distance(x, y, 11.5, 4, 9.5, 24), segment_distance(x, y, 19.5, 4, 17.5, 24),
            segment_distance(x, y, 5.5, 10.5, 23, 10.5), segment_distance(x, y, 5, 17.5, 22.5, 17.5))
    return stroked(d, 2.4, s)


def wifi_alert(x, y, s):
    stroke = 3.6
    cx, cy = 21, 38
    d = min(arc_distance(x, y, cx, cy, 11, 225, 315), arc_distance(x, y, cx, cy, 19.5, 225, 315))
    dot = math.hypot(x - cx, y - cy) - 3.4
    mark = segment_distance(x, y, 45, 13, 45, 29)
    mark_dot = math.hypot(x - 45, y - 37) - 2.6
    return max(stroked(d, stroke, s), filled(dot, s), stroked(mark, stroke, s), filled(mark_dot, s))


def pause_circle(x, y, s):
    ring = stroked(ring_distance(x, y, 26, 26, 22), 3.2, s)
    bars = max(filled(rect_signed(x, y, 19.5, 17, 4.2, 18, 1.4), s), filled(rect_signed(x, y, 28.3, 17, 4.2, 18, 1.4), s))
    return max(ring, bars)


def xmark_circle(x, y, s):
    d = min(ring_distance(x, y, 26, 26, 22), segment_distance(x, y, 19, 19, 33, 33), segment_distance(x, y, 33, 19, 19, 33))
    return stroked(d, 3.2, s)


def alert_large(x, y, s):
    corners = [(26, 6.5), (47.5, 44.5), (4.5, 44.5)]
    edge = polyline_distance(x, y, corners + corners[:1])
    bar = segment_distance(x, y, 26, 19.5, 26, 31.5)
    dot = math.hypot(x - 26, y - 38.5) - 2.4
    return max(stroked(edge, 3.2, s), stroked(bar, 3.4, s), filled(dot, s))


def glass_circle(size):
    """The card's symbol circle: white 8% under a 1 px white 14% outline."""
    disc = disc_alpha(size, size / 2)
    edge = disc_alpha(size, size / 2, ring=1)
    return [[WHITE + (round(255 * (0.08 + 0.06 * e) * d),) for d, e in zip(dl, el)] for dl, el in zip(disc, edge)]


def step_tile():
    size = 168
    cover = shape_alpha(size, size, 34)
    edge = shape_alpha(size, size, 34, ring=1)
    return [[WHITE + (round(255 * (0.06 + 0.08 * e) * c),) for c, e in zip(cl, el)] for cl, el in zip(cover, edge)]


BADGE = 52
BADGE_CANVAS = (74, 76)
BADGE_AT = (11, 6)
BADGE_SHADOW = (0, 6, 3.5, 0.5)  # x and y offset, sigma, alpha


def step_badge():
    width, height = BADGE_CANVAS
    left, top = BADGE_AT
    radius = BADGE / 2
    cx, cy = left + radius, top + radius
    dx, dy, sigma, strength = BADGE_SHADOW
    rows = []
    for py in range(height):
        row = []
        for px in range(width):
            x, y = px + 0.5, py + 0.5
            disc = clamp(0.5 - (math.hypot(x - cx, y - cy) - radius))
            # A disc blurred by a Gaussian: across its edge, the error function.
            d = math.hypot(x - cx - dx, y - cy - dy) - radius
            shadow = strength * 0.5 * math.erfc(d / (sigma * math.sqrt(2)))
            total = disc + shadow * (1 - disc)
            color = tuple(255 * disc / total for _ in range(3)) if total > 0 else WHITE
            row.append(tuple(round(c) for c in color) + (round(255 * total),))
        rows.append(row)
    return rows


def step_done(scale=GLYPH_SCALE):
    size = 96
    disc = disc_alpha(size, size / 2, scale=scale)
    ring = disc_alpha(size, size / 2, ring=3, scale=scale)
    rows = []
    for py in range(size * scale):
        row = []
        for px in range(size * scale):
            x, y = (px + 0.5) / scale, (py + 0.5) / scale
            mark = stroked(polyline_distance(x, y, [(29, 48), (42, 61), (67, 33)]), 7, scale)
            ink = max(ring[py][px], mark)
            alpha = ink + 0.16 * disc[py][px] * (1 - ink)
            row.append(SUCCESS + (round(255 * alpha),))
        rows.append(row)
    return rows


APP_ICON = 92
APP_MARK_HEIGHT = 77


def rendered_mark(branding, height):
    """RGBA rows of the flat Silo mark height px tall, from the branding master."""
    svg = pathlib.Path(branding) / "logo" / "svg" / "silo-mark-flat.svg"
    if not svg.is_file() or not shutil.which("rsvg-convert") or not shutil.which("magick"):
        return None
    drawn = subprocess.run(["rsvg-convert", "-h", str(height), str(svg)], check=True, capture_output=True).stdout
    size = subprocess.run(["magick", "png:-", "-format", "%w %h", "info:"], input=drawn, check=True, capture_output=True).stdout
    width, rows_count = (int(v) for v in size.split())
    raw = subprocess.run(["magick", "png:-", "-depth", "8", "rgba:-"], input=drawn, check=True, capture_output=True).stdout
    return [[tuple(raw[(r * width + c) * 4:(r * width + c) * 4 + 4]) for c in range(width)] for r in range(rows_count)]


def step_app_icon(mark, scale=GLYPH_SCALE):
    size = APP_ICON * scale
    cover = shape_alpha(APP_ICON, APP_ICON, 22, scale=scale)
    edge = shape_alpha(APP_ICON, APP_ICON, 22, ring=1, scale=scale)
    mark_height, mark_width = len(mark), len(mark[0])
    left, top = (size - mark_width) // 2, (size - mark_height) // 2
    rows = []
    for py in range(size):
        row = []
        for px in range(size):
            color = mix(ICON_FIELD, WHITE, 0.18 * edge[py][px])
            mx, my = px - left, py - top
            if 0 <= mx < mark_width and 0 <= my < mark_height:
                r, g, b, a = mark[my][mx]
                color = mix(color, (r, g, b), a / 255)
            row.append(tuple(round(c) for c in color) + (round(255 * cover[py][px]),))
        rows.append(row)
    return rows


def onboarding_images():
    for name, size, cover in (
        ("globe", 32, globe), ("person", 32, person), ("lock", 32, lock), ("lock_open", 32, lock_open), ("eye", 40, eye),
        ("eye_slash", 40, eye_slash), ("key", 32, key), ("qrcode", 32, qrcode),
        ("phone", 32, phone_glyph(32)), ("phone_large", 52, phone_glyph(52)), ("tv", 32, tv),
        ("gear", 28, gear), ("check", 28, check), ("check_large", 64, check_large),
        ("retry", 32, retry), ("number", 28, number), ("wifi_alert", 52, wifi_alert),
        ("pause_circle", 52, pause_circle), ("xmark_circle", 52, xmark_circle), ("alert_large", 52, alert_large),
    ):
        yield f"glyph_{name}.png", glyph(size, cover)
    yield "card_symbol.png", glass_circle(112)
    yield "card_symbol_96.png", glass_circle(96)
    yield "card_symbol_140.png", glass_circle(140)
    yield "step_tile.png", step_tile()
    yield "step_badge.png", step_badge()
    yield "step_done.png", step_done()
    for name, radius in (("rounded_20", 20), ("rounded_24", 24)):
        for res, r in (("fhd", radius), ("hd", hd(radius))):
            yield f"{name}_fill_{res}.9.png", nine_patch(shape_alpha(2 * r + STRETCH, 2 * r + STRETCH, r))
    yield from line_nine_patches("rounded_20", 20, hd(20), 1)
    yield from capsule_nine_patches(30, with_ring=False)
    for res, r, ring in (("fhd", 38 // 2 - 1, 4), ("hd", hd(38) // 2 - 1, hd(4))):
        yield f"capsule_30_ring4_{res}.9.png", nine_patch(shape_alpha(2 * r + STRETCH, 2 * r + STRETCH, r, ring))
    yield "dot_10.png", rgba(disc_alpha(10, 5), WHITE)


# --- Brand mesh -------------------------------------------------------------

def dimmed(color, amount):
    return tuple(c / 255 * (1 - amount) for c in color)


PALETTES = {
    "setup": [
        dimmed(BLUE, 0.5), dimmed(RED, 0.58), dimmed(ORANGE, 0.58),
        dimmed(BLUE, 0.76), dimmed(RED, 0.74), dimmed(ORANGE, 0.82),
        (0, 0, 0), (0, 0, 0), (0, 0, 0),
    ],
    "profiles": [
        dimmed(RED, 0.56), dimmed(ORANGE, 0.52), dimmed(BLUE, 0.56),
        dimmed(ORANGE, 0.7), dimmed(RED, 0.66), dimmed(BLUE, 0.72),
        dimmed(BLUE, 0.9), dimmed(RED, 0.9), dimmed(ORANGE, 0.92),
    ],
}
# Where the mesh's middle row and column sit for each palette, at rest.
MIDDLE = {"setup": (0.5, 0.55), "profiles": (0.6, 0.5)}

# Black over the light: (position, alpha) stops, horizontal then vertical.
SCRIMS = {
    "setup": ([(0, 0.8), (0.3, 0.55), (0.58, 0.2), (0.8, 0.1), (1, 0.3)], [(0, 0), (0.65, 0), (1, 0.5)]),
    "profiles": ([(0, 0), (1, 0)], [(0, 0.35), (0.25, 0.2), (0.55, 0.75), (0.78, 1), (1, 1)]),
}

BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def smooth(t):
    return t * t * (3 - 2 * t)


def ramp(stops, t):
    for (p0, a0), (p1, a1) in zip(stops, stops[1:]):
        if t <= p1:
            return lerp(a0, a1, (t - p0) / (p1 - p0) if p1 > p0 else 1)
    return stops[-1][1]


def mesh_sample(mesh, u, v):
    gx, gy = min(u * 2, 1.9999), min(v * 2, 1.9999)
    cx, cy = int(gx), int(gy)
    fx, fy = smooth(gx - cx), smooth(gy - cy)
    top_left = cy * 3 + cx
    out = []
    for channel in range(3):
        top = lerp(mesh[top_left][channel], mesh[top_left + 1][channel], fx)
        bottom = lerp(mesh[top_left + 3][channel], mesh[top_left + 4][channel], fx)
        out.append(lerp(top, bottom, fy))
    return out


def mesh_image(name):
    """The Android TV backdrop with its drift at phase 0 (a = 0, b = 1), mirrored, under its scrim."""
    width, height = MESH_SIZE
    mesh = PALETTES[name]
    middle, center_x = MIDDLE[name]
    top_x, bottom_x = 0.5, 0.5 - 0.1
    left_y, right_y = middle + 0.06, middle
    c_x, c_y = center_x + 0.1, middle
    across, down = SCRIMS[name]
    rows = []
    for py in range(height):
        y = (py + 0.5) / height
        row = []
        for px in range(width):
            x = 1 - (px + 0.5) / width  # mirrored: the light sits on the right
            row_y = lerp(left_y, c_y, x / c_x) if x < c_x else lerp(c_y, right_y, (x - c_x) / (1 - c_x))
            col_x = lerp(top_x, c_x, y / row_y) if y < row_y else lerp(c_x, bottom_x, (y - row_y) / (1 - row_y))
            u = 0.5 * x / col_x if x < col_x else 0.5 + 0.5 * (x - col_x) / (1 - col_x)
            v = 0.5 * y / row_y if y < row_y else 0.5 + 0.5 * (y - row_y) / (1 - row_y)
            color = mesh_sample(mesh, clamp(u), clamp(v))
            screen_x = (px + 0.5) / width
            keep = (1 - ramp(across, screen_x)) * (1 - ramp(down, y))
            dither = (BAYER[py % 4][px % 4] + 0.5) / 16 - 0.5
            row.append(tuple(int(clamp(c * keep * 255 + dither + 0.5, 0, 255)) for c in color))
        rows.append(row)
    return rows


# --- PNG --------------------------------------------------------------------

def paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def png(rows):
    """An 8-bit RGB or RGBA PNG, every row Paeth-filtered, which suits smooth ramps."""
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    height, width = len(rows), len(rows[0])
    channels = len(rows[0][0])
    previous = bytes(width * channels)
    raw = bytearray()
    for row in rows:
        line = bytes(channel for pixel in row for channel in pixel)
        filtered = bytearray([4])
        for i, value in enumerate(line):
            left = line[i - channels] if i >= channels else 0
            up_left = previous[i - channels] if i >= channels else 0
            filtered.append((value - paeth(left, previous[i], up_left)) & 0xFF)
        raw += filtered
        previous = line
    color_type = 6 if channels == 4 else 2
    header = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def images():
    yield "mesh_setup.png", mesh_image("setup")
    yield "mesh_profiles.png", mesh_image("profiles")
    for height in (76, 60):
        yield from capsule_nine_patches(height)
    yield from capsule_nine_patches(52, with_ring=False)
    yield from rounded_nine_patches("rounded_16", 16, hd(16))
    yield from rounded_nine_patches("rounded_40", 40, hd(40), with_ring=False)
    yield "avatar_disc.png", rgba(disc_alpha(AVATAR, AVATAR / 2), WHITE)
    yield "avatar_shade.png", avatar_shade()
    yield "avatar_ring.png", avatar_ring()
    yield "lock_badge.png", lock_badge()
    yield "pin_dot.png", rgba(disc_alpha(PIN_DOT, PIN_DOT / 2), WHITE)
    yield "pin_dot_ring.png", rgba(disc_alpha(PIN_DOT, PIN_DOT / 2, ring=PIN_DOT_RING), WHITE)
    yield "spinner.png", spinner()
    yield "add_ring.png", add_ring()
    yield "add_plus.png", add_plus()
    for height in (76, 52):
        yield from capsule_line_nine_patches(height)
    yield from line_nine_patches("rounded_16", 16, hd(16), 1)
    yield from line_nine_patches("rounded_16", 16, hd(16), 3, suffix="ring3")
    yield from line_nine_patches("rounded_40", 40, hd(40), 1)
    yield from line_nine_patches("rounded_12", 12, hd(12), 1)
    for name, radius in (("rounded_30", 30),):
        for res, r in (("fhd", radius), ("hd", hd(radius))):
            yield f"{name}_fill_{res}.9.png", nine_patch(shape_alpha(2 * r + STRETCH, 2 * r + STRETCH, r))
        yield from line_nine_patches(name, radius, hd(radius), 1)
    for res, r in (("fhd", 36 // 2 - 1), ("hd", hd(36) // 2 - 1)):
        yield f"capsule_36_fill_{res}.9.png", nine_patch(shape_alpha(2 * r + STRETCH, 2 * r + STRETCH, r))
    yield from capsule_line_nine_patches(36)
    yield "server_mark.png", server_mark()
    yield "warning_triangle.png", warning_triangle()
    yield from onboarding_images()


def main():
    out = pathlib.Path(__file__).resolve().parent.parent / "images" / "firstrun"
    out.mkdir(parents=True, exist_ok=True)
    generated = list(images())
    mark = rendered_mark(sys.argv[1], APP_MARK_HEIGHT * GLYPH_SCALE) if len(sys.argv) > 1 else None
    if mark is not None:
        generated.append(("step_app_icon.png", step_app_icon(mark)))
    else:
        print("step_app_icon.png kept: pass the silo-branding checkout to redraw it (needs rsvg-convert and magick)")
    for name, rows in generated:
        data = png(rows)
        (out / name).write_bytes(data)
        print(f"images/firstrun/{name}  {len(rows[0])}x{len(rows)}  {len(data)} bytes")


if __name__ == "__main__":
    main()
