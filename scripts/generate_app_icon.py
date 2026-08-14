"""Generate Batch ST-Link Flasher app icon / logo assets.

Run from repo root:
  python scripts/generate_app_icon.py

Draws the flat charcoal rounded-tile mark with transparent corners
(outside the tile). Same artwork for EXE icon, About, and splash.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

# Brand colors (match ui/theme.py)
BG = (27, 33, 44, 255)  # #1b212c
ACCENT = (47, 158, 136, 255)  # #2f9e88
ACCENT_LT = (92, 201, 180, 255)
GOLD = (212, 175, 95, 255)
CYAN = (120, 220, 210, 255)
EDGE = (58, 69, 86, 255)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "batch_stlink_flasher" / "assets"
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


def draw_logo(size: int) -> Image.Image:
    """Flat chip + flash mark on a charcoal tile; corners are transparent."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    pad = max(1, size // 32)
    tile_r = max(4, size // 6)
    d.rounded_rectangle(
        (pad, pad, size - pad - 1, size - pad - 1),
        radius=tile_r,
        fill=BG,
        outline=EDGE,
        width=max(1, size // 64),
    )

    cx = cy = size / 2
    chip_w = size * 0.42
    chip_h = size * 0.36
    left = cx - chip_w / 2
    top = cy - chip_h / 2
    right = cx + chip_w / 2
    bottom = cy + chip_h / 2
    chip_r = max(2, size // 18)
    d.rounded_rectangle((left, top, right, bottom), radius=chip_r, fill=ACCENT)

    inset = size * 0.08
    d.rounded_rectangle(
        (left + inset, top + inset, right - inset, bottom - inset),
        radius=max(1, size // 28),
        fill=ACCENT_LT,
    )

    # Flash / program mark
    tw = size * 0.12
    th = size * 0.10
    d.polygon(
        [
            (cx, cy - th * 0.2),
            (cx - tw, cy + th * 0.55),
            (cx + tw, cy + th * 0.55),
        ],
        fill=BG,
    )
    s = size * 0.05
    d.rounded_rectangle(
        (cx - s, cy - th * 0.85, cx + s, cy - th * 0.15),
        radius=max(1, size // 64),
        fill=CYAN,
    )

    pin_w = max(2, int(size * 0.055))
    pin_h = max(2, int(size * 0.045))
    gap = chip_h / 5
    for i in (-1.5, -0.5, 0.5, 1.5):
        y = cy + i * gap - pin_h / 2
        d.rectangle((left - pin_w, y, left + 1, y + pin_h), fill=GOLD)
        d.rectangle((right - 1, y, right + pin_w, y + pin_h), fill=GOLD)

    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    master = draw_logo(512)
    master.save(OUT / "app_icon.png", "PNG", optimize=True)
    master.save(OUT / "logo.png", "PNG", optimize=True)
    master.save(OUT / "splash.png", "PNG", optimize=True)
    draw_logo(256).save(OUT / "app_icon_256.png", "PNG", optimize=True)

    frames = [draw_logo(s) for s in ICO_SIZES]
    frames[-1].save(
        OUT / "app_icon.ico",
        format="ICO",
        sizes=[(s, s) for s in ICO_SIZES],
        append_images=frames[:-1],
    )
    print(f"Wrote icons to {OUT}")
    print("  flat charcoal tile + chip; transparent outside rounded corners")


if __name__ == "__main__":
    main()
