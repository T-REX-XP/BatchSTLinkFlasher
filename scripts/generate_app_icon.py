"""Generate Windows 11–style app icon / logo assets.

Run from repo root:
  python scripts/generate_app_icon.py

Prefers ``src/batch_stlink_flasher/assets/app_icon_source.png`` when present
(Fluent chip art). Corners outside the rounded tile are made transparent so
Explorer / installer / About sit cleanly on any background. Falls back to a
procedural Fluent-like glyph if the source file is missing.
"""

from __future__ import annotations

import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "batch_stlink_flasher" / "assets"
DOCS = ROOT / "docs" / "imgs"
SOURCE = OUT / "app_icon_source.png"
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


def _lerp(a: tuple[int, ...], b: tuple[int, ...], t: float) -> tuple[int, ...]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def _vertical_gradient(
    size: int,
    top: tuple[int, int, int, int],
    bottom: tuple[int, int, int, int],
) -> Image.Image:
    img = Image.new("RGBA", (size, size))
    px = img.load()
    assert px is not None
    for y in range(size):
        c = _lerp(top, bottom, y / max(1, size - 1))
        for x in range(size):
            px[x, y] = c  # type: ignore[index]
    return img


def _rounded_mask(size: int, radius: int, pad: int = 0) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (pad, pad, size - pad - 1, size - pad - 1),
        radius=radius,
        fill=255,
    )
    return mask


def apply_transparent_corners(img: Image.Image, *, radius_ratio: float = 0.22) -> Image.Image:
    """Keep artwork inside a Windows-11 squircle; clear pixels outside."""
    img = img.convert("RGBA")
    size = img.width
    radius = max(8, int(size * radius_ratio))
    mask = _rounded_mask(size, radius)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def draw_fluent_fallback(size: int) -> Image.Image:
    """Procedural Fluent-like chip when source art is unavailable."""
    pad = max(2, size // 16)
    tile = size - 2 * pad
    radius = max(6, tile // 5)

    plate = _vertical_gradient(size, (36, 48, 68, 255), (18, 24, 34, 255))
    highlight = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    hd = ImageDraw.Draw(highlight)
    hd.ellipse((-size * 0.2, -size * 0.55, size * 1.1, size * 0.55), fill=(255, 255, 255, 38))
    plate = Image.alpha_composite(plate, highlight)

    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    cx = cy = size / 2
    chip_w, chip_h = size * 0.46, size * 0.46
    left, top = cx - chip_w / 2, cy - chip_h / 2 + size * 0.02
    right, bottom = left + chip_w, top + chip_h
    sd.rounded_rectangle(
        (left + size * 0.02, top + size * 0.04, right + size * 0.02, bottom + size * 0.04),
        radius=max(4, size // 14),
        fill=(0, 0, 0, 90),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=max(1, size // 28)))
    plate = Image.alpha_composite(plate, shadow)

    d = ImageDraw.Draw(plate)
    chip_r = max(4, size // 14)
    d.rounded_rectangle((left, top, right, bottom), radius=chip_r, fill=(47, 158, 136, 255))
    inset = size * 0.07
    d.rounded_rectangle(
        (left + inset, top + inset, right - inset, bottom - inset),
        radius=max(2, size // 22),
        fill=(74, 190, 168, 255),
    )

    # Dual chevron (flash / program)
    cw = size * 0.16
    for dy in (-size * 0.04, size * 0.05):
        y0 = cy + dy - size * 0.02
        d.polygon(
            [
                (cx, y0 - size * 0.06),
                (cx - cw, y0 + size * 0.04),
                (cx - cw * 0.35, y0 + size * 0.04),
                (cx, y0 - size * 0.01),
                (cx + cw * 0.35, y0 + size * 0.04),
                (cx + cw, y0 + size * 0.04),
            ],
            fill=(200, 255, 245, 255),
        )

    pin_w = max(2, int(size * 0.045))
    pin_h = max(2, int(size * 0.035))
    gap = chip_h / 5
    for i in (-1.5, -0.5, 0.5, 1.5):
        y = cy + i * gap - pin_h / 2 + size * 0.01
        d.rectangle((left - pin_w, y, left + 1, y + pin_h), fill=(212, 175, 95, 255))
        d.rectangle((right - 1, y, right + pin_w, y + pin_h), fill=(212, 175, 95, 255))

    mask = _rounded_mask(size, radius, pad=pad)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(plate, (0, 0), mask)
    return out


def load_master(size: int = 1024) -> Image.Image:
    if SOURCE.is_file():
        src = Image.open(SOURCE).convert("RGBA")
        # Drop near-white / light-gray studio backdrop → transparent.
        px = src.load()
        assert px is not None
        w, h = src.size
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]  # type: ignore[misc]
                if a > 0 and r > 230 and g > 230 and b > 230:
                    px[x, y] = (r, g, b, 0)  # type: ignore[index]
                elif a > 0 and min(r, g, b) > 200 and max(r, g, b) - min(r, g, b) < 18:
                    # Soft light-gray fringe around AI renders
                    px[x, y] = (r, g, b, 0)  # type: ignore[index]
        src = apply_transparent_corners(src)
        if src.size != (size, size):
            src = src.resize((size, size), Image.Resampling.LANCZOS)
        return src
    return draw_fluent_fallback(size)


def resize_icon(master: Image.Image, size: int) -> Image.Image:
    return master.resize((size, size), Image.Resampling.LANCZOS)


def write_ico(path: Path, frames: list[Image.Image]) -> None:
    """Write a valid multi-size ICO with PNG-compressed entries (Vista+).

    Pillow's ``save(..., format='ICO', append_images=...)`` often produces a
    corrupt directory that Windows Explorer / Inno Setup render as garbage.
    """
    from io import BytesIO

    entries: list[tuple[int, int, bytes]] = []
    for im in frames:
        im = im.convert("RGBA")
        w, h = im.size
        if w > 256 or h > 256:
            raise ValueError(f"ICO frame too large: {w}x{h}")
        bio = BytesIO()
        im.save(bio, format="PNG", optimize=True)
        entries.append((w, h, bio.getvalue()))

    # ICONDIR + ICONDIRENTRY[] + image data
    count = len(entries)
    header = struct.pack("<HHH", 0, 1, count)
    offset = 6 + 16 * count
    dir_entries = bytearray()
    payloads = bytearray()
    for w, h, data in entries:
        dir_entries += struct.pack(
            "<BBBBHHII",
            0 if w == 256 else w,
            0 if h == 256 else h,
            0,
            0,
            1,
            32,
            len(data),
            offset,
        )
        payloads += data
        offset += len(data)

    path.write_bytes(header + dir_entries + payloads)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)

    master = load_master(1024)
    ui = resize_icon(master, 512)
    ui.save(OUT / "app_icon.png", "PNG", optimize=True)
    ui.save(OUT / "logo.png", "PNG", optimize=True)
    # Splash keeps a larger brand mark (same art).
    ui.save(OUT / "splash.png", "PNG", optimize=True)
    resize_icon(master, 256).save(OUT / "app_icon_256.png", "PNG", optimize=True)

    # Inno Setup wizard sidebar (164x314 classic) + small (55x55)
    wizard = Image.new("RGBA", (164, 314), (27, 33, 44, 255))
    mark = resize_icon(master, 128)
    wizard.paste(mark, ((164 - 128) // 2, 70), mark)
    wizard.convert("RGB").save(OUT / "wizard_image.bmp", format="BMP")
    resize_icon(master, 55).convert("RGB").save(OUT / "wizard_small.bmp", format="BMP")

    frames = [resize_icon(master, s) for s in ICO_SIZES]
    write_ico(OUT / "app_icon.ico", frames)

    # README docs copy
    resize_icon(master, 512).save(DOCS / "logo.png", "PNG", optimize=True)
    resize_icon(master, 256).save(DOCS / "app_icon.png", "PNG", optimize=True)

    ico_bytes = (OUT / "app_icon.ico").stat().st_size
    print(f"Wrote icons to {OUT}")
    print(f"  master: Fluent chip + transparent corners ({SOURCE.name if SOURCE.is_file() else 'fallback'})")
    print(f"  app_icon.ico: {ico_bytes} bytes, sizes {list(ICO_SIZES)}")


if __name__ == "__main__":
    main()
