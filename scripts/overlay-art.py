#!/usr/bin/env python3
"""Write the player's Skip Intro and Up Next art into images/overlays/.

  pill_72_{fill,ring2,ring3}_{fhd,hd}.9.png
                     the Skip Intro button: tvOS's 72 pt capsule, filled or
                     as its 2 px resting and 3 px lit borders
  frame_8_{fhd,hd}.9.png, ring_8_{fhd,hd}.9.png
                     Up Next's video box: the corners outside radius 8 in
                     black, and a 1 px outline at that radius
  countdown_NN.png   Up Next's countdown arc after NN of 30 steps: tvOS's
                     58 pt ring with a 3 px stroke and round caps, from 12
                     o'clock clockwise. countdown_30.png is the whole ring,
                     which also serves as the track at 12%
                     (components/theme/upNext.bs)

Shapes are white, for a Poster's blendColor and opacity. The 9-patches follow
scripts/first-run-art.py: HD sizes are the FHD sizes times 2/3, a capsule's
radius is half its height less 1 px, each stretches a 2 px band in the
middle, and the whole image is content. Roku cannot draw arcs, so the ring
is stepped: 30 steps divide the 10 s end countdown evenly, and only the step
on screen holds a texture.

HD borders are the FHD ones times 2/3, at least 1 px. Edges are antialiased analytically from signed distances. Uses only the
standard library, so the pixels are the same on every machine. Run from
anywhere: python3 scripts/overlay-art.py
"""
import math
import pathlib
import struct
import zlib

WHITE = (0xFF, 0xFF, 0xFF)
STRETCH = 2  # stretchable band between the corners, px
PILL = 72  # FHD px
PILL_RINGS = (2, 3)  # FHD px: resting and lit borders
FRAME_RADIUS = 8
RING = 58  # FHD px
RING_STROKE = 3
STEPS = 30


def hd(fhd_px):
    return round(fhd_px * 2 / 3)


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def rounded_rect_distance(x, y, width, height, radius):
    """Signed distance from (x, y) to a width x height rectangle at the origin with corner radius."""
    qx = abs(x - width / 2) - (width / 2 - radius)
    qy = abs(y - height / 2) - (height / 2 - radius)
    outside = math.hypot(max(qx, 0.0), max(qy, 0.0))
    return outside + min(max(qx, qy), 0.0) - radius


def rounded_alpha(size, radius, ring=0):
    """Coverage rows of a size x size rounded square 9-patch body, or of its outline ring px wide."""
    rows = []
    for py in range(size):
        row = []
        for px in range(size):
            x, y = px + 0.5, py + 0.5
            outer = clamp(0.5 - rounded_rect_distance(x, y, size, size, radius))
            if ring:
                inner = clamp(0.5 - rounded_rect_distance(x - ring, y - ring, size - 2 * ring, size - 2 * ring, max(radius - ring, 0)))
                outer = max(outer - inner, 0.0)
            row.append(outer)
        rows.append(row)
    return rows


def capsule_alpha(size, ring=0):
    """Coverage rows of a size x size capsule 9-patch body, or of its outline ring px wide."""
    return rounded_alpha(size, size // 2 - 1, ring)


def arc_alpha(size, stroke, fraction):
    """Coverage rows of a round-capped arc from 12 o'clock clockwise over fraction of the circle."""
    centre = size / 2
    mid = centre - stroke / 2
    sweep = 2 * math.pi * fraction
    ends = [(0.0, -mid), (mid * math.sin(sweep), -mid * math.cos(sweep))]
    rows = []
    for py in range(size):
        row = []
        for px in range(size):
            x, y = px + 0.5 - centre, py + 0.5 - centre
            angle = math.atan2(x, -y) % (2 * math.pi)
            if fraction >= 1 or angle <= sweep:
                distance = abs(math.hypot(x, y) - mid) - stroke / 2
            else:
                distance = min(math.hypot(x - ex, y - ey) for ex, ey in ends) - stroke / 2
            row.append(clamp(0.5 - distance))
        rows.append(row)
    return rows


def rgba(alpha):
    return [[WHITE + (round(255 * a),) for a in line] for line in alpha]


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


def png(rows):
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    height, width = len(rows), len(rows[0])
    raw = b"".join(b"\x00" + bytes(channel for pixel in row for channel in pixel) for row in rows)
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def images():
    for res, scale in (("fhd", lambda px: px), ("hd", hd)):
        size = scale(PILL)
        yield f"pill_{PILL}_fill_{res}.9.png", nine_patch(capsule_alpha(size))
        for ring in PILL_RINGS:
            yield f"pill_{PILL}_ring{ring}_{res}.9.png", nine_patch(capsule_alpha(size, max(1, scale(ring))))
        radius = scale(FRAME_RADIUS)
        body = rounded_alpha(2 * radius + STRETCH, radius)
        yield f"frame_{FRAME_RADIUS}_{res}.9.png", nine_patch([[1 - a for a in line] for line in body], (0, 0, 0))
        yield f"ring_{FRAME_RADIUS}_{res}.9.png", nine_patch(rounded_alpha(2 * radius + STRETCH, radius, 1))
    for step in range(1, STEPS + 1):
        yield f"countdown_{step:02d}.png", rgba(arc_alpha(RING, RING_STROKE, step / STEPS))


def main():
    out = pathlib.Path(__file__).resolve().parent.parent / "images" / "overlays"
    out.mkdir(parents=True, exist_ok=True)
    written = set()
    for name, rows in images():
        data = png(rows)
        (out / name).write_bytes(data)
        written.add(name)
        print(f"images/overlays/{name}  {len(rows[0])}x{len(rows)}  {len(data)} bytes")
    for stale in sorted(out.glob("*.png")):
        if stale.name not in written:
            stale.unlink()
            print(f"removed images/overlays/{stale.name}")


if __name__ == "__main__":
    main()
