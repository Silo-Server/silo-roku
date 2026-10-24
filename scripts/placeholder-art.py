#!/usr/bin/env python3
"""Write the placeholder icons and splash screens into images/.

Each image is opaque RGB on the #161616 splash colour (black level above 16)
with "Silo" in a blocky pixel font: a neutral stand-in, not the Silo logo or
wordmark. Uses only the standard library, so the pixels are the same on every
machine. Run from anywhere: python3 scripts/placeholder-art.py
"""
import pathlib
import struct
import zlib

BACKGROUND = (0x16, 0x16, 0x16)
FOREGROUND = (0xC8, 0xC8, 0xC8)

# 5x7 glyphs for the letters of "Silo", one string per row.
GLYPHS = {
    "S": [".###.", "#...#", "#....", ".###.", "....#", "#...#", ".###."],
    "i": ["..#..", ".....", ".##..", "..#..", "..#..", "..#..", ".###."],
    "l": [".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "o": [".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."],
}

# Manifest key, file, size (Roku's channel-manifest page), and pixels per font cell.
IMAGES = [
    ("mm_icon_focus_fhd", "icon_focus_fhd.png", 540, 405, 12),
    ("mm_icon_focus_hd", "icon_focus_hd.png", 290, 218, 6),
    ("splash_screen_fhd", "splash_fhd.png", 1920, 1080, 16),
    ("splash_screen_hd", "splash_hd.png", 1280, 720, 11),
    ("splash_screen_sd", "splash_sd.png", 720, 480, 6),
]


def render(width, height, scale):
    # One string per pixel-font row, with a blank column between letters.
    mask = [".".join(GLYPHS[char][y] for char in "Silo") for y in range(7)]
    left = (width - len(mask[0]) * scale) // 2
    top = (height - len(mask) * scale) // 2
    background_row = bytes(BACKGROUND) * width
    text_rows = []
    for line in mask:
        row = bytearray(background_row)
        for x, cell in enumerate(line):
            if cell == "#":
                start = (left + x * scale) * 3
                row[start:start + scale * 3] = bytes(FOREGROUND) * scale
        text_rows.append(bytes(row))
    raw = bytearray()
    for y in range(height):
        cell = (y - top) // scale
        row = text_rows[cell] if y >= top and cell < len(text_rows) else background_row
        raw += b"\x00" + row  # PNG filter type 0 (none) per scanline
    return png(width, height, bytes(raw))


def png(width, height, raw):
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB, no alpha
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def main():
    images = pathlib.Path(__file__).resolve().parent.parent / "images"
    images.mkdir(exist_ok=True)
    for key, name, width, height, scale in IMAGES:
        (images / name).write_bytes(render(width, height, scale))
        print(f"{key}=pkg:/images/{name}  {width}x{height}")


if __name__ == "__main__":
    main()
