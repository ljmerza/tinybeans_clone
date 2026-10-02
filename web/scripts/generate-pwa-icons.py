"""Draw the Circles app icon at every size web/public/ needs.

The mark is three interlocking rings (a family circle) on the app's default
dark primary color.

Writes:
  logo512.png, logo192.png  manifest "any" icons, full-bleed square
  maskable-512.png          Android adaptive icon (rings kept inside the 80% safe zone)
  apple-touch-icon.png      iOS home-screen icon, 180x180, opaque
  favicon.ico               16/32/48/64, with heavier rings so they survive at 16px

Usage (needs Pillow): python web/scripts/generate-pwa-icons.py
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw

PUBLIC = Path(__file__).resolve().parent.parent / "public"

BACKGROUND = (24, 24, 27)  # #18181b, the default theme's --primary
RING_COLORS = [
    (251, 113, 133),  # coral
    (251, 191, 36),  # amber
    (56, 189, 248),  # sky
]
SUPERSAMPLE = 4


def draw_icon(size: int, *, extent: float, stroke: float) -> Image.Image:
    """Three rings whose group spans `extent` of the icon's width; `stroke` is a fraction of the size."""
    big = size * SUPERSAMPLE
    image = Image.new("RGB", (big, big), BACKGROUND)
    draw = ImageDraw.Draw(image)
    center = big / 2
    # Ring centers sit on a small circle, one at the top and two below. The
    # group is 2 * (offset * cos 30deg + radius) wide.
    radius = big * extent / (2 * (0.76 * math.cos(math.radians(30)) + 1))
    offset = radius * 0.76
    width = max(1, round(big * stroke))
    for index, color in enumerate(RING_COLORS):
        angle = math.radians(-90 + index * 120)
        cx = center + offset * math.cos(angle)
        # The top ring sticks out further than the bottom two; shift down to center the group.
        cy = center + offset * math.sin(angle) + offset * 0.25
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            outline=color,
            width=width,
        )
    return image.resize((size, size), Image.LANCZOS)


def main() -> None:
    # Full-bleed icons: the rings fill most of the square.
    draw_icon(512, extent=0.8, stroke=0.055).save(PUBLIC / "logo512.png", optimize=True)
    draw_icon(192, extent=0.8, stroke=0.055).save(PUBLIC / "logo192.png", optimize=True)
    draw_icon(180, extent=0.78, stroke=0.055).save(PUBLIC / "apple-touch-icon.png", optimize=True)
    # Maskable: launchers may crop to a circle of 80% diameter, so keep the rings well inside it.
    draw_icon(512, extent=0.62, stroke=0.045).save(PUBLIC / "maskable-512.png", optimize=True)
    # Favicon: fewer pixels, so a bigger group and heavier rings.
    favicon = draw_icon(256, extent=0.94, stroke=0.09)
    favicon.save(PUBLIC / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])


if __name__ == "__main__":
    main()
