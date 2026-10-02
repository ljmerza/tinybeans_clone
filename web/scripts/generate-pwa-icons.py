"""Derive the home-screen icons in web/public/ from one square source image.

Writes:
  maskable-512.png      Android adaptive icon (artwork kept inside the 80% safe zone)
  apple-touch-icon.png  iOS home-screen icon, 180x180, opaque (iOS turns transparency black)

Usage (needs Pillow, e.g. the backend's uv env):
  python web/scripts/generate-pwa-icons.py [source.png]   # default: web/public/logo512.png

To change the app icon: replace public/logo192.png and public/logo512.png, then re-run this.
"""

import sys
from pathlib import Path

from PIL import Image

PUBLIC = Path(__file__).resolve().parent.parent / "public"
BACKGROUND = (255, 255, 255, 255)  # matches manifest background_color #ffffff


def _compose(art: Image.Image, size: int, art_fraction: float) -> Image.Image:
    """Center the artwork's visible pixels on an opaque square canvas."""
    art = art.crop(art.getchannel("A").getbbox() or (0, 0, *art.size))
    scale = size * art_fraction / max(art.size)
    art = art.resize((round(art.width * scale), round(art.height * scale)), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), BACKGROUND)
    canvas.alpha_composite(art, ((size - art.width) // 2, (size - art.height) // 2))
    return canvas.convert("RGB")


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else PUBLIC / "logo512.png"
    art = Image.open(source).convert("RGBA")
    # Maskable: launchers may crop to a circle of 80% diameter; 0.56 (< 0.8/sqrt 2)
    # keeps even a square artwork's corners inside it.
    _compose(art, 512, 0.56).save(PUBLIC / "maskable-512.png", optimize=True)
    _compose(art, 180, 0.8).save(PUBLIC / "apple-touch-icon.png", optimize=True)


if __name__ == "__main__":
    main()
