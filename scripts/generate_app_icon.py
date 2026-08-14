"""Generate modern Windows 11 Fluent-style app icon / logo assets.

Run from repo root:
  python scripts/generate_app_icon.py

Prefers ``src/batch_stlink_flasher/assets/app_icon_source.png`` when present
for the *Windows app icon* only. UI logo/splash always use a transparent chip
glyph (no dark Fluent plate).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "batch_stlink_flasher" / "assets"
SOURCE = OUT / "app_icon_source.png"
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


def _lerp(a: tuple[int, ...], b: tuple[int, ...], t: float) -> tuple[int, ...]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def _vertical_gradient(
    size: int,
    top: tuple[int, int, int, int],
    bottom: tuple[int, int, int, int],
    radius: int,
) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    assert px is not None
    for y in range(size):
        t = y / max(1, size - 1)
        color = _lerp(top, bottom, t)
        for x in range(size):
            px[x, y] = color
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def _soft_shadow(size: int, box: tuple[float, float, float, float], radius: int) -> Image.Image:
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(box, radius=radius, fill=(0, 0, 0, 90))
    blur = max(1, size // 40)
    return layer.filter(ImageFilter.GaussianBlur(radius=blur))


def draw_chip_glyph(
    size: int,
    *,
    scale: float = 1.0,
    center_y_bias: float = 0.0,
) -> Image.Image:
    """Transparent chip mark for About / splash (no Fluent plate)."""
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    offset = max(1, size // 48)
    cx = size / 2
    cy = size / 2 + size * center_y_bias
    chip_w = size * 0.56 * scale
    chip_h = size * 0.48 * scale
    left = cx - chip_w / 2
    top = cy - chip_h / 2
    right = cx + chip_w / 2
    bottom = cy + chip_h / 2
    chip_r = max(3, int(size * 0.06 * scale))

    canvas = Image.alpha_composite(
        canvas,
        _soft_shadow(size, (left, top + offset, right, bottom + offset), chip_r),
    )

    chip = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cd = ImageDraw.Draw(chip)

    pin_w = max(2, int(size * 0.07 * scale))
    pin_h = max(2, int(size * 0.055 * scale))
    gap = chip_h / 5
    for i in (-1.5, -0.5, 0.5, 1.5):
        y = cy + i * gap - pin_h / 2
        cd.rounded_rectangle(
            (left - pin_w, y, left + 2, y + pin_h), radius=1, fill=(232, 196, 110, 255)
        )
        cd.rounded_rectangle(
            (right - 2, y, right + pin_w, y + pin_h), radius=1, fill=(232, 196, 110, 255)
        )
        cd.line((left - pin_w + 1, y + 1, left, y + 1), fill=(255, 235, 180, 160))
        cd.line((right, y + 1, right + pin_w - 1, y + 1), fill=(255, 235, 180, 160))

    cd.rounded_rectangle((left, top, right, bottom), radius=chip_r, fill=(36, 150, 130, 255))
    inset = size * 0.04 * scale
    cd.rounded_rectangle(
        (left + inset, top + inset, right - inset, bottom - inset * 0.6),
        radius=max(2, chip_r - 1),
        fill=(78, 210, 185, 255),
    )

    die_pad = size * 0.09 * scale
    cd.rounded_rectangle(
        (left + die_pad, top + die_pad, right - die_pad, bottom - die_pad),
        radius=max(2, int(size * 0.035 * scale)),
        fill=(210, 250, 240, 235),
    )

    tw = size * 0.12 * scale
    th = size * 0.10 * scale
    cd.polygon(
        [
            (cx, cy - th * 0.05),
            (cx - tw, cy + th * 0.65),
            (cx + tw, cy + th * 0.65),
        ],
        fill=(22, 34, 48, 255),
    )
    s = size * 0.05 * scale
    cd.rounded_rectangle(
        (cx - s, cy - th * 0.75, cx + s, cy - th * 0.15),
        radius=max(1, size // 64),
        fill=(90, 220, 255, 255),
    )

    return Image.alpha_composite(canvas, chip)


def draw_fluent_icon(size: int) -> Image.Image:
    """Windows 11-ish layered icon: gradient plate + chip glyph."""
    margin = max(2, int(size * 0.08))
    plate = size - 2 * margin
    plate_r = max(6, int(plate * 0.22))

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    offset = max(1, size // 48)
    sd.rounded_rectangle(
        (
            margin + offset,
            margin + offset * 2,
            margin + plate - 1 + offset,
            margin + plate - 1 + offset * 2,
        ),
        radius=plate_r,
        fill=(0, 0, 0, 70),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=max(1, size // 28)))
    canvas = Image.alpha_composite(canvas, shadow)

    plate_img = _vertical_gradient(
        plate,
        (42, 54, 72, 255),
        (18, 23, 32, 255),
        plate_r,
    )
    sheen = Image.new("RGBA", (plate, plate), (0, 0, 0, 0))
    sheen_draw = ImageDraw.Draw(sheen)
    sheen_draw.ellipse(
        (-plate * 0.2, -plate * 0.35, plate * 0.95, plate * 0.55),
        fill=(255, 255, 255, 28),
    )
    sheen = sheen.filter(ImageFilter.GaussianBlur(radius=max(2, plate // 18)))
    plate_img = Image.alpha_composite(plate_img, sheen)

    rim = ImageDraw.Draw(plate_img)
    rim.rounded_rectangle(
        (1, 1, plate - 2, plate - 2),
        radius=max(4, plate_r - 1),
        outline=(120, 150, 170, 55),
        width=max(1, plate // 64),
    )
    canvas.paste(plate_img, (margin, margin), plate_img)

    # Smaller chip so it sits inside the Fluent plate.
    chip = draw_chip_glyph(size, scale=0.72, center_y_bias=0.01)
    return Image.alpha_composite(canvas, chip)


def render_from_source(size: int, source: Image.Image) -> Image.Image:
    """Scale a master Fluent artwork into a transparent square canvas."""
    img = source.convert("RGBA")
    return img.resize((size, size), Image.Resampling.LANCZOS)


def make_icon(size: int, source: Image.Image | None) -> Image.Image:
    if source is not None and _source_has_transparency(source):
        return render_from_source(size, source)
    return draw_fluent_icon(size)


def _source_has_transparency(source: Image.Image) -> bool:
    """Reject fully-opaque masters (they look like a black box in title bars)."""
    rgba = source.convert("RGBA")
    # Sample corners + a coarse grid; any soft edge means usable alpha.
    w, h = rgba.size
    samples = [
        (0, 0),
        (w - 1, 0),
        (0, h - 1),
        (w - 1, h - 1),
        (w // 2, 0),
        (0, h // 2),
    ]
    for x, y in samples:
        if rgba.getpixel((x, y))[3] < 250:
            return True
    return False


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    source = Image.open(SOURCE).convert("RGBA") if SOURCE.is_file() else None
    if source is not None and _source_has_transparency(source):
        print(f"Using source artwork for app icon: {SOURCE}")
    elif source is not None:
        print(
            f"Ignoring opaque {SOURCE.name} (no transparency) - "
            "drawing Fluent icon with transparent corners instead"
        )
        source = None
    else:
        print("Drawing Fluent app icon + transparent logo glyph")

    # Windows EXE / taskbar: Fluent plate (or custom source with alpha).
    master = make_icon(512, source)
    master.save(OUT / "app_icon.png", "PNG", optimize=True)
    make_icon(256, source).save(OUT / "app_icon_256.png", "PNG", optimize=True)

    frames = [make_icon(s, source) for s in ICO_SIZES]
    frames[-1].save(
        OUT / "app_icon.ico",
        format="ICO",
        sizes=[(s, s) for s in ICO_SIZES],
        append_images=frames[:-1],
    )

    # About / splash: transparent chip only (no dark plate).
    logo = draw_chip_glyph(512)
    logo.save(OUT / "logo.png", "PNG", optimize=True)
    logo.save(OUT / "splash.png", "PNG", optimize=True)

    print(f"Wrote icons to {OUT}")
    print("  app_icon.* = Windows Fluent tile (transparent outside plate)")
    print("  logo.png / splash.png = transparent chip (no plate)")


if __name__ == "__main__":
    main()
