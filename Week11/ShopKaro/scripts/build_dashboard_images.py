"""
Resize the dashboard's studio photos for the web (src/shopkaro/dashboard/assets -> .../static).

The originals are 0.6-0.9 MB each. Embedding them as base64 in every product card made one storefront render send
~30 MB to the browser. The dashboard now serves these resized copies as static files (cached by the browser).

Usage:  python scripts/build_dashboard_images.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

DASHBOARD = Path(__file__).resolve().parents[1] / "src" / "shopkaro" / "dashboard"
SRC, DST = DASHBOARD / "assets", DASHBOARD / "static"
MAX_WIDTH, QUALITY = 640, 78


def main() -> None:
    DST.mkdir(exist_ok=True)
    before = after = 0
    for src in sorted(SRC.glob("*.jpg")):
        dst = DST / src.name
        with Image.open(src) as im:
            im = im.convert("RGB")
            if im.width > MAX_WIDTH:
                im = im.resize((MAX_WIDTH, round(im.height * MAX_WIDTH / im.width)), Image.LANCZOS)
            im.save(dst, "JPEG", quality=QUALITY, optimize=True, progressive=True)
        before += src.stat().st_size
        after += dst.stat().st_size
    print(f"{len(list(DST.glob('*.jpg')))} images: {before / 1e6:.1f} MB -> {after / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
