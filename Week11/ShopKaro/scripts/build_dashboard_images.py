"""
Resize the dashboard's studio photos for the web (src/shopkaro/dashboard/assets -> .../static).

The originals are 0.6-0.9 MB each. Embedding them as base64 in every product card made one storefront render send
~30 MB to the browser. The dashboard now serves these resized copies as static files (cached by the browser).

Usage:  python scripts/build_dashboard_images.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "src" / "shopkaro" / "dashboard"
SRC, DST = DASHBOARD / "assets", DASHBOARD / "static"
MAX_WIDTH, QUALITY = 640, 78
# Homepage promo carousel: full-width banners need larger copies (desktop + phone sizes for srcset).
BANNER_SRC, BANNER_WIDTHS, BANNER_QUALITY = ROOT / "assets" / "web", (1600, 800), 80


def _save_resized(src: Path, dst: Path, width: int, quality: int) -> int:
    with Image.open(src) as im:
        im = im.convert("RGB")
        if im.width > width:
            im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        im.save(dst, "JPEG", quality=quality, optimize=True, progressive=True)
    return dst.stat().st_size


def main() -> None:
    DST.mkdir(exist_ok=True)
    before = after = 0
    for src in sorted(SRC.glob("*.jpg")):
        after += _save_resized(src, DST / src.name, MAX_WIDTH, QUALITY)
        before += src.stat().st_size
    print(f"{len(list(SRC.glob('*.jpg')))} product images: {before / 1e6:.1f} MB -> {after / 1e6:.1f} MB")

    banners = sorted(BANNER_SRC.glob("carousel*.jpg"))
    b_before = b_after = 0
    for src in banners:
        b_before += src.stat().st_size
        for width in BANNER_WIDTHS:
            b_after += _save_resized(src, DST / f"promo_{src.stem}_{width}.jpg", width, BANNER_QUALITY)
    print(f"{len(banners)} carousel banners x {len(BANNER_WIDTHS)} sizes: {b_before / 1e6:.1f} MB -> {b_after / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
