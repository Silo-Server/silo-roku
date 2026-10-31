#!/usr/bin/env python3
"""Write Settings' generated glyphs into images/settings/ (spec section 5.8.1).

  general.png    gearshape: a toothed wheel with a round hole
  playback.png   play.rectangle: a rounded frame around a play triangle
  subtitles.png  captions.bubble: a speech bubble with two lines of text
  server.png     server.rack: two stacked rounded units, each with a light
  sign_out.png   rectangle.portrait.and.arrow.right: an open frame with an
                 arrow leaving it to the right
  diagnostics.png  waveform.path.ecg.rectangle: a rounded frame around a
                 heartbeat trace

Each glyph has a logical 40 px square canvas, rasterized at 2x by player-art
for aligned bilinear minification, white on transparent for blendColor:
the rail draws it at 30 px beside each category, and the pane header at 40 px
inside its 72 px icon tile. The glyphs are plain geometry drawn after the
shapes of the tvOS rail's SF Symbols on scripts/player-art.py's 48-unit grid;
no icon file is copied. Uses only the standard library, so the pixels are the
same on every machine. Run from anywhere: python3 scripts/settings-art.py
"""
import importlib.util
import math
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("player_art", HERE / "player-art.py")
player = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(player)

SIZE = 40  # FHD px
STROKE = 1.7  # half the outline width, design units


def frame(left, top, right, bottom, radius):
    """A rounded rectangle's outline, STROKE * 2 units wide, centred on its edge."""
    def covered(x, y):
        outer = player.in_rounded_rect(x, y, left - STROKE, top - STROKE, right + STROKE, bottom + STROKE, radius + STROKE)
        inner = player.in_rounded_rect(x, y, left + STROKE, top + STROKE, right - STROKE, bottom - STROKE, max(radius - STROKE, 0))
        return outer and not inner
    return covered


def line(*points):
    return lambda x, y: player.near_polyline(x, y, list(points), STROKE)


def general():
    """Eight flat-topped teeth on a wheel, with a round hole in the middle."""
    def covered(x, y):
        dx, dy = x - 24, y - 24
        r = math.hypot(dx, dy)
        if r < 6.5:
            return False
        if r <= 15.5:
            return True
        # Each tooth is a band 7.5 units wide centred on its spoke.
        angle = math.atan2(dy, dx)
        spoke = round(angle / (math.pi / 4)) * (math.pi / 4)
        across = abs(r * math.sin(angle - spoke))
        return r <= 21 and across <= 3.75
    return player.glyph(SIZE, covered)


def playback():
    triangle = [(20, 17), (20, 31), (31.5, 24)]
    return player.glyph(SIZE, frame(5, 9, 43, 39, 6), lambda x, y: player.in_polygon(x, y, triangle))


def subtitles():
    def tail(x, y):
        return player.in_polygon(x, y, [(12, 33), (12, 43), (23, 33)])
    return player.glyph(
        SIZE,
        frame(5, 7, 43, 35, 7),
        tail,
        line((13, 18), (23, 18)), line((28, 18), (35, 18)),
        line((13, 25), (19, 25)), line((24, 25), (35, 25)),
    )


def server():
    def light(cy):
        return lambda x, y: math.hypot(x - 35, y - cy) <= 2.4
    return player.glyph(
        SIZE,
        frame(6, 7, 42, 21, 4), frame(6, 27, 42, 41, 4),
        light(14), light(34),
        line((12, 14), (22, 14)), line((12, 34), (22, 34)),
    )


def sign_out():
    return player.glyph(
        SIZE,
        line((26, 15), (26, 7), (7, 7), (7, 41), (26, 41), (26, 33)),
        line((17, 24), (42, 24)),
        line((34, 16), (42, 24), (34, 32)),
    )


def diagnostics():
    return player.glyph(
        SIZE,
        frame(5, 9, 43, 39, 6),
        line((10, 25), (17, 25), (20.5, 17), (25.5, 32), (29.5, 21), (32, 25), (38, 25)),
    )


def images():
    yield "general.png", general()
    yield "playback.png", playback()
    yield "subtitles.png", subtitles()
    yield "server.png", server()
    yield "sign_out.png", sign_out()
    yield "diagnostics.png", diagnostics()


def main():
    out = HERE.parent / "images" / "settings"
    out.mkdir(parents=True, exist_ok=True)
    written = set()
    for name, rows in images():
        (out / name).write_bytes(player.art.png(rows))
        written.add(name)
        print(f"images/settings/{name}  {len(rows[0])}x{len(rows)}")
    for stale in sorted(out.glob("*.png")):
        if stale.name not in written:
            stale.unlink()
            print(f"removed images/settings/{stale.name}")


if __name__ == "__main__":
    main()
