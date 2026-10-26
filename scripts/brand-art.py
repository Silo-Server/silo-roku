#!/usr/bin/env python3
"""Write the channel poster, splash screens, and wordmark into images/ from the
silo-branding repository's SVG masters.

  icon_focus_{fhd,hd}.png  the channel poster (mm_icon_focus_*), 540x405 and
                           290x218: the wordmark for dark fields centred on the
                           deep blue radial field of the Android TV banner and
                           the tvOS Top Shelf image
  splash_{fhd,hd,sd}.png   the splash (splash_screen_*), 1920x1080, 1280x720,
                           and 720x480: the same wordmark centred on #161616
                           (splash_color), as the other apps' startup splash
                           ends on black
  brand/wordmark.png       the wordmark for dark fields at 150x78, the size the
                           first-run screens draw it (the top bar draws it
                           smaller)

The poster and splashes are opaque RGB, as Roku requires. The artwork is used
as supplied (the brand rules forbid recolouring or redrawing it), so the
wordmark is embedded from the master SVG rather than rebuilt here.

Needs rsvg-convert (librsvg) and ImageMagick's magick.
Run: python3 scripts/brand-art.py /path/to/silo-branding
"""
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMAGES = ROOT / "images"

# The radial field of the Android TV banner and tvOS Top Shelf image: their
# centre colour, fading to the palette's deep field rather than their darker
# corners, and the splash's near black, so that the art keeps a black level of at
# least 16 (implementation plan, criterion 6.4).
FIELD_CENTRE = "#1330BE"
FIELD_EDGE = "#070B82"
SPLASH = "#161616"

# The wordmark master is 1388.9048 x 720.
WORDMARK_ASPECT = 1388.9048 / 720

# File, size, background, and the wordmark's height as a fraction of the image's.
# The poster's wordmark sits well inside Roku's 486x365 safe zone; the splash's
# is the Top Shelf image's proportion of a 1080-line screen.
ART = [
    ("icon_focus_fhd.png", 540, 405, "field", 0.40),
    ("icon_focus_hd.png", 290, 218, "field", 0.40),
    ("splash_fhd.png", 1920, 1080, "black", 0.22),
    ("splash_hd.png", 1280, 720, "black", 0.22),
    ("splash_sd.png", 720, 480, "black", 0.22),
]
WORDMARK_SIZE = (150, 78)


def compose(width, height, background, fraction, wordmark):
    mark_height = round(height * fraction)
    mark_width = round(mark_height * WORDMARK_ASPECT)
    x = (width - mark_width) / 2
    y = (height - mark_height) / 2
    if background == "field":
        fill = (
            '<defs><radialGradient id="f" cx="50%" cy="50%" r="75%">'
            f'<stop offset="0" stop-color="{FIELD_CENTRE}"/>'
            f'<stop offset="1" stop-color="{FIELD_EDGE}"/>'
            '</radialGradient></defs><rect width="100%" height="100%" fill="url(#f)"/>'
        )
    else:
        fill = f'<rect width="100%" height="100%" fill="{SPLASH}"/>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">{fill}'
        f'<image x="{x}" y="{y}" width="{mark_width}" height="{mark_height}" '
        f'xlink:href="{wordmark}"/></svg>'
    )


def run(*args):
    subprocess.run(args, check=True)


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: brand-art.py /path/to/silo-branding")
    wordmark = pathlib.Path(sys.argv[1]).resolve() / "logo/svg/silo-wordmark-white.svg"
    if not wordmark.is_file():
        sys.exit(f"missing {wordmark}")
    with tempfile.TemporaryDirectory() as scratch:
        scratch = pathlib.Path(scratch)
        # librsvg loads an <image> only from the referencing file's directory.
        (scratch / wordmark.name).write_bytes(wordmark.read_bytes())
        for name, width, height, background, fraction in ART:
            svg = scratch / (name + ".svg")
            svg.write_text(compose(width, height, background, fraction, wordmark.name))
            rendered = scratch / name
            run("rsvg-convert", "-w", str(width), "-h", str(height), str(svg), "-o", str(rendered))
            # Drop the (fully opaque) alpha channel and any metadata.
            run("magick", str(rendered), "-alpha", "off", "-strip", "PNG24:" + str(IMAGES / name))
        width, height = WORDMARK_SIZE
        rendered = scratch / "wordmark.png"
        run("rsvg-convert", "-w", str(width), "-h", str(height), "--keep-aspect-ratio",
            str(wordmark), "-o", str(rendered))
        run("magick", str(rendered), "-background", "none", "-gravity", "center",
            "-extent", f"{width}x{height}", "-strip", "PNG32:" + str(IMAGES / "brand/wordmark.png"))


if __name__ == "__main__":
    main()
