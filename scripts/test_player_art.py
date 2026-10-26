"""Player backdrop regression checks; run python3 -I scripts/test_player_art.py.

Contrast uses encoded-sRGB alpha compositing over a white SDR video frame.
It checks the generated asset and actual overlay layout, not a Roku screenshot
(those omit the video plane). Physical HDR/display validation remains separate.
"""
import importlib.util
import math
import pathlib
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("player_art", ROOT / "scripts/player-art.py")
PLAYER_ART = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PLAYER_ART)


def luminance(value):
    return value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4


class PlayerBackdropTests(unittest.TestCase):
    def setUp(self):
        self.rows = PLAYER_ART.controls_gradient()
        xml = ET.parse(ROOT / "components/player/controls/ControlsOverlay.xml")
        self.gradient = xml.find(".//Poster[@id='gradient']")
        self.source = (ROOT / "components/player/controls/ControlsOverlay.bs").read_text()
        self.top = float(self.gradient.get("translation").strip("[]").split(",")[1])
        self.height = float(self.gradient.get("height"))
        self.opacity = float(self.gradient.get("opacity", "1"))

    def constant(self, name):
        return re.search(rf'^const {name} = (.+)$', self.source, re.M)[1].strip('"')

    def alpha_at(self, y):
        self.assertGreaterEqual(y, self.top)
        self.assertLess(y, self.top + self.height)
        # Pixel-centre mapping when scaleToFill stretches this small texture.
        pos = max(0, min(len(self.rows) - 1, (y + .5 - self.top) / self.height * len(self.rows) - .5))
        lo, hi = math.floor(pos), math.ceil(pos)
        alpha = self.rows[lo][0][3] * (1 - pos + lo) + self.rows[hi][0][3] * (pos - lo)
        return alpha / 255 * self.opacity

    def test_packaged_asset_matches_generator_and_overlay(self):
        self.assertIn('m.top.findNode("gradient").uri = ART + "controls_gradient.png"', self.source)
        self.assertEqual((ROOT / "images/player/controls_gradient.png").read_bytes(), PLAYER_ART.art.png(self.rows))
        self.assertEqual(self.gradient.get("loadDisplayMode"), "scaleToFill")
        self.assertEqual(float(self.gradient.get("width")), 1920)
        self.assertEqual(self.top + self.height, 1080)

    def test_backdrop_is_smooth_translucent_black(self):
        alphas = [row[0][3] for row in self.rows]
        self.assertEqual(alphas[0], 0)
        self.assertLess(max(alphas), 255)
        self.assertTrue(all(0 <= b - a <= 3 for a, b in zip(alphas, alphas[1:])))
        self.assertTrue(all(row == [(0, 0, 0, row[0][3])] * 2 for row in self.rows))

    def test_text_contrast_on_white_video_throughout_each_label(self):
        for name, color in [("SERIES", "SERIES_COLOR"), ("TITLE", None), ("TITLE", "TAG_COLOR"), ("TIME", None)]:
            text_alpha = int(self.constant(color)[-2:], 16) / 255 if color else 1
            top = int(self.constant(name + "_Y"))
            height = int(self.constant(name + "_HEIGHT"))
            for y in range(top, top + height):
                background = 1 - self.alpha_at(y)
                foreground = text_alpha + background * (1 - text_alpha)
                contrast = (luminance(foreground) + .05) / (luminance(background) + .05)
                self.assertGreaterEqual(contrast, 4.5, f"{color or name} at y={y}: {contrast:.2f}:1")


if __name__ == "__main__":
    unittest.main()
