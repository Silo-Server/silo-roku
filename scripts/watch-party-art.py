#!/usr/bin/env python3
"""Write Watch Party's generated art into images/watchparty/ (docs/watch-party.md
section 4, tvOS's WatchPartyComponents at silo-apple 15f4153e).

  seat_shade.png          a 220 px white disc whose alpha rises from clear at
                          the top left to opaque at the bottom right: tinted
                          with a seat palette pair's second colour over a
                          disc (images/firstrun/avatar_disc.png) tinted with
                          its first, it draws tvOS's diagonal avatar gradient
  seat_ring.png           a seat's ring for its state, drawn at twice the 128
  seat_ring_dashed.png    px seat's 146 px ring (size * 1.14), 0.035 of the
  seat_ring_dotted.png    seat wide: solid (ready or watching), dashed 3 on,
                          2.2 off in ring widths (here, not ready, and the
                          Invite seat), and round dots 3 widths apart (away)
  suggest_card.png        the ballot's "Suggest a title" card at rest: a 220 x
                          330 rounded rectangle (radius 12) outlined 2 px,
                          dashed 10 on, 8 off, white for blendColor
  backdrop_fade_x.png     tvOS's two gradients over the lobby's backdrop, in
  backdrop_fade_y.png     black, 256 x 2 and 2 x 256, stretched over the
                          screen: leading to trailing black 92% at 0, 78% at
                          0.34, 25% at 0.62, 5% at 1; top to bottom 35% at
                          0, clear at 0.3, 40% at 0.7, 95% at 1

The shapes reuse scripts/first-run-art.py's coverage and PNG helpers. Every
image is white, for blendColor and opacity.
"""
import importlib.util
import math
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("first_run_art", HERE / "first-run-art.py")
art = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(art)

DISC = 220
SEAT = 128
# The ring art is drawn at 2x for the 128 px seat and scaled down for 80.
RING_SCALE = 2
RING_DIAMETER = round(SEAT * 1.14) * RING_SCALE
RING_WIDTH = SEAT * 0.035 * RING_SCALE
CARD = (220, 330)
CARD_RADIUS = 12
CARD_LINE = 2
CARD_DASH = 10
CARD_GAP = 8


def seat_shade():
    disc = art.disc_alpha(DISC, DISC / 2)
    rows = []
    for py in range(DISC):
        row = []
        for px in range(DISC):
            t = art.clamp((px + py + 1) / (2 * DISC))
            row.append(art.WHITE + (round(255 * disc[py][px] * t),))
        rows.append(row)
    return rows


def ring(style):
    """The ring inside the image's edge, solid, dashed, or dotted along its middle."""
    size, width = RING_DIAMETER, RING_WIDTH
    middle = size / 2 - width / 2
    circumference = 2 * math.pi * middle
    if style == "dashed":
        dash, gap = 3 * width, 2.2 * width
    else:
        dash, gap = 0.0, 3 * width
    periods = max(1, round(circumference / (dash + gap)))
    period = circumference / periods
    dash = period * dash / (dash + gap) if style == "dashed" else 0.0
    solid = art.disc_alpha(size, size / 2, ring=width)
    rows = []
    for py in range(size):
        row = []
        for px in range(size):
            x, y = px + 0.5 - size / 2, py + 0.5 - size / 2
            cover = solid[py][px]
            if style == "dashed":
                along = (math.atan2(y, x) % (2 * math.pi)) * middle % period
                cover *= art.clamp(min(along + 0.5, dash - along + 0.5, 1.0)) if along <= dash + 0.5 else art.clamp(along - period + 0.5)
            elif style == "dotted":
                # Round dots of the ring's width centred every period along its middle.
                angle = math.atan2(y, x) % (2 * math.pi)
                nearest = round(angle * middle / period) * period / middle
                cx, cy = middle * math.cos(nearest), middle * math.sin(nearest)
                cover = art.clamp(0.5 - (math.hypot(x - cx, y - cy) - width / 2))
            row.append(art.WHITE + (round(255 * cover),))
        rows.append(row)
    return rows


def suggest_card():
    width, height = CARD
    outline = art.shape_alpha(width, height, CARD_RADIUS, ring=CARD_LINE)
    # Distance along the outline's middle, walked as the rounded rectangle's
    # perimeter: straight edges and quarter arcs, clockwise from the top left.
    r = CARD_RADIUS - CARD_LINE / 2
    inner_w, inner_h = width - 2 * CARD_RADIUS, height - 2 * CARD_RADIUS
    arc = math.pi * r / 2
    perimeter = 2 * (inner_w + inner_h) + 4 * arc
    periods = max(1, round(perimeter / (CARD_DASH + CARD_GAP)))
    period = perimeter / periods
    dash = period * CARD_DASH / (CARD_DASH + CARD_GAP)

    def along(x, y):
        left, top = CARD_RADIUS, CARD_RADIUS
        right, bottom = width - CARD_RADIUS, height - CARD_RADIUS
        if y < top and left <= x <= right:
            return x - left
        if x > right and y < top:
            return inner_w + arc * (math.atan2(y - top, x - right) + math.pi / 2) / (math.pi / 2)
        if x > right and top <= y <= bottom:
            return inner_w + arc + (y - top)
        if x > right and y > bottom:
            return inner_w + arc + inner_h + arc * math.atan2(y - bottom, x - right) / (math.pi / 2)
        if y > bottom and left <= x <= right:
            return inner_w + 2 * arc + inner_h + (right - x)
        if x < left and y > bottom:
            return 2 * inner_w + inner_h + 2 * arc + arc * (math.atan2(y - bottom, x - left) - math.pi / 2) / (math.pi / 2)
        if x < left and top <= y <= bottom:
            return 2 * inner_w + inner_h + 3 * arc + (bottom - y)
        return 2 * inner_w + 2 * inner_h + 3 * arc + arc * (math.atan2(y - top, x - left) + math.pi) / (math.pi / 2)

    rows = []
    for py in range(height):
        row = []
        for px in range(width):
            cover = outline[py][px]
            if cover > 0:
                walked = along(px + 0.5, py + 0.5) % period
                if walked <= dash + 0.5:
                    cover *= art.clamp(min(walked + 0.5, dash - walked + 0.5, 1.0))
                else:
                    cover *= art.clamp(walked - period + 0.5)
            row.append(art.WHITE + (round(255 * cover),))
        rows.append(row)
    return rows


FADE_X = [(0, 0.92), (0.34, 0.78), (0.62, 0.25), (1, 0.05)]
FADE_Y = [(0, 0.35), (0.3, 0.0), (0.7, 0.4), (1, 0.95)]
FADE_STEPS = 256


def piecewise(stops, at):
    for (x0, y0), (x1, y1) in zip(stops, stops[1:]):
        if at <= x1:
            return y0 + (y1 - y0) * (at - x0) / (x1 - x0)
    return stops[-1][1]


def fade(stops, horizontal):
    alphas = [round(255 * piecewise(stops, i / (FADE_STEPS - 1))) for i in range(FADE_STEPS)]
    if horizontal:
        return [[(0, 0, 0, a) for a in alphas] for _ in range(2)]
    return [[(0, 0, 0, a)] * 2 for a in alphas]


def images():
    yield "backdrop_fade_x.png", fade(FADE_X, True)
    yield "backdrop_fade_y.png", fade(FADE_Y, False)
    yield "seat_shade.png", seat_shade()
    yield "seat_ring.png", ring("solid")
    yield "seat_ring_dashed.png", ring("dashed")
    yield "seat_ring_dotted.png", ring("dotted")
    yield "suggest_card.png", suggest_card()


def main():
    out = HERE.parent / "images" / "watchparty"
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in images():
        data = art.png(rows)
        (out / name).write_bytes(data)
        print(f"images/watchparty/{name}  {len(rows[0])}x{len(rows)}  {len(data)} bytes")


if __name__ == "__main__":
    main()
