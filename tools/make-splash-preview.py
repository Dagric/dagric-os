#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 IMPRESSIONSDIRECT360 LLC <repo@dagric.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Render the Splash Screen KCM's preview tile for org.dagric.splash.

WHY THIS EXISTS
---------------
Plasma's Splash Screen page (kcm_splashscreen) builds each grid tile from the
look-and-feel package's contents/previews/splash.png. org.dagric.splash shipped
without one, so the OS's *own default* splash rendered as an empty placeholder
tile, sitting directly beside Breeze's fully drawn preview. On a paid product
whose pitch is polish, the one broken-looking row was ours.

WHY IT IS DRAWN RATHER THAN SCREENSHOTTED
-----------------------------------------
A real capture needs a running Plasma session. This reproduces the same
composition from the same inputs Splash.qml uses -- the identical gradient stops,
the same logo asset, the same accent -- so the tile shows what the splash
actually looks like and stays honest if either is changed. Anyone editing
Splash.qml should re-run this.

WHY PIL AND NOT A REAL SVG RASTERISER
-------------------------------------
This tree is developed on a Windows host with no ImageMagick, rsvg-convert,
inkscape or cairosvg -- checked, all four absent. But the preview needs no
vector work: it is a gradient, an existing raster logo, and a hairline. The
256x256 dagric-logo.png is plenty at the ~64px this tile draws it, so the
missing rasteriser never mattered. (Splash.qml itself points at the SVG, which
is a different problem with a different fix -- see the comment there.)

USAGE
    python3 tools/make-splash-preview.py
Writes, relative to the repo root:
    config/includes.chroot/usr/share/plasma/look-and-feel/org.dagric.splash/contents/previews/splash.png
"""

import os
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("Pillow is required: python3 -m pip install Pillow")

# 400x225 is 16:9 and matches what the KCM scales its tiles to. Bigger costs
# ISO bytes for a thumbnail nobody inspects; smaller looks soft on HiDPI.
W, H = 400, 225

# The exact stops from Splash.qml. If those change, change these -- a preview
# that lies about the colour is worse than no preview, because it is believed.
TOP = (0x0E, 0x18, 0x26)
BOTTOM = (0x05, 0x08, 0x10)
ACCENT = (0x3F, 0xA9, 0xF5)
TRACK = (0x1C, 0x2B, 0x40)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO = os.path.join(ROOT, "config", "includes.chroot", "usr", "share",
                    "dagric", "logo", "dagric-logo.png")
OUT = os.path.join(ROOT, "config", "includes.chroot", "usr", "share", "plasma",
                   "look-and-feel", "org.dagric.splash", "contents", "previews",
                   "splash.png")


def main():
    img = Image.new("RGB", (W, H), TOP)
    draw = ImageDraw.Draw(img)

    # Vertical gradient, one row at a time. Linear in sRGB on purpose: that is
    # what QML's Gradient does too, so matching it means matching the artifact.
    for y in range(H):
        t = y / (H - 1)
        draw.line(
            [(0, y), (W, y)],
            fill=tuple(round(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3)),
        )

    # The mark, at the same optical position Splash.qml uses: horizontally
    # centred, lifted 6% of the height above centre.
    mark = 64
    logo_y = (H - mark) // 2 - round(H * 0.06)
    if os.path.exists(LOGO):
        logo = Image.open(LOGO).convert("RGBA").resize((mark, mark), Image.LANCZOS)
        img.paste(logo, ((W - mark) // 2, logo_y), logo)
    else:
        # Same contract as Splash.qml's Text fallback: never leave a hole.
        print("WARNING: %s missing -- drawing the wordmark as text" % LOGO,
              file=sys.stderr)
        draw.text((W // 2, logo_y + mark // 2), "Dagric OS",
                  fill=(0xE7, 0xEE, 0xF7), anchor="mm")

    # The progress hairline. Drawn part-filled because a preview showing an
    # empty track reads as a splash that is not doing anything, and one showing
    # a full track reads as finished.
    tw, th = round(W * 0.24), 2
    tx, ty = (W - tw) // 2, logo_y + mark + 34
    draw.rectangle([tx, ty, tx + tw, ty + th], fill=TRACK)
    draw.rectangle([tx, ty, tx + round(tw * 0.55), ty + th], fill=ACCENT)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    # optimize + 8-bit-safe: build.sh and container-build.sh both refuse any
    # shipped PNG whose IHDR bit depth is over 8, so this must not be 16-bit.
    img.save(OUT, "PNG", optimize=True)
    print("wrote %s (%dx%d, %d bytes)" % (OUT, W, H, os.path.getsize(OUT)))


if __name__ == "__main__":
    main()
