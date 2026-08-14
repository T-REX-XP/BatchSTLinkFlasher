"""Generate modern Windows 11 Fluent-style app icon / logo assets.

Run from repo root:
  python scripts/generate_app_icon.py

Prefers ``src/batch_stlink_flasher/assets/app_icon_source.png`` when present;
otherwise draws a Fluent-like layered glyph with Pillow.
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


def draw_fluent_logo(size: int) -> Image.Image:
    """Windows 11-ish layered icon: gradient plate + shadowed chip glyph."""
    # Win11 icons keep ~10% margin around the plate.
    margin = max(2, int(size * 0.08))
    plate = size - 2 * margin
    plate_r = max(6, int(plate * 0.22))

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # Drop shadow under the plate
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

    # Gradient plate (Fluent dark)
    plate_img = _vertical_gradient(
        plate,
        (42, 54, 72, 255),  # #2a3648
        (18, 23, 32, 255),  # #121720
        plate_r,
    )
    # Top-left specular sheen
    sheen = Image.new("RGBA", (plate, plate), (0, 0, 0, 0))
    sheen_draw = ImageDraw.Draw(sheen)
    sheen_draw.ellipse(
        (-plate * 0.2, -plate * 0.35, plate * 0.95, plate * 0.55),
        fill=(255, 255, 255, 28),
    )
    sheen = sheen.filter(ImageFilter.GaussianBlur(radius=max(2, plate // 18)))
    plate_img = Image.alpha_composite(plate_img, sheen)

    # Subtle rim
    rim = ImageDraw.Draw(plate_img)
    rim.rounded_rectangle(
        (1, 1, plate - 2, plate - 2),
        radius=max(4, plate_r - 1),
        outline=(120, 150, 170, 55),
        width=max(1, plate // 64),
    )

    canvas.paste(plate_img, (margin, margin), plate_img)

    # Chip geometry relative to full canvas
    cx = cy = size / 2
    chip_w = size * 0.40
    chip_h = size * 0.34
    left = cx - chip_w / 2
    top = cy - chip_h / 2 + size * 0.3
    right = cx + chip_w / 2
    bottom = cy + chip_h / 2 + offset * 0.3
    chip_r = max(3, int(size * 0.05))

    # Soft shadow under chip
    canvas = Image.alpha_composite(
        canvas,
        _soft_shadow(size, (left, top + offset, right, bottom + offset), chip_r),
    )

    chip = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cd = ImageDraw.Draw(chip)

    # Pins (gold with slight highlight)
    pin_w = max(2, int(size * 0.05))
    pin_h = max(2, int(size * 0.04))
    gap = chip_h / 5
    for i in (-1.5, -0.5, 0.5, 1.5):
        y = cy + i * gap - pin_h / 2 + offset * 0.3
        cd.rounded_rectangle((left - pin_w, y, left + 2, y + pin_h), radius=1, fill=(232, 196, 110, 255))
        cd.rounded_rectangle((right - 2, y, right + pin_w, y + pin_h), radius=1, fill=(232, 196, 110, 255))
        # pin highlight
        cd.line((left - pin_w + 1, y + 1, left, y + 1), fill=(255, 235, 180, 160))
        cd.line((right, y + 1, right + pin_w - 1, y + 1), fill=(255, 235, 180, 160))

    # Chip body gradient approximation (two layered rounded rects)
    cd.rounded_rectangle((left, top, right, bottom), radius=chip_r, fill=(36, 150, 130, 255))
    inset = size * 0.035
    cd.rounded_rectangle(
        (left + inset, top + inset, right - inset, bottom - inset * 0.6),
        radius=max(2, chip_r - 1),
        fill=(78, 210, 185, 255),
    )

    # Inner die
    die_pad = size * 0.07
    cd.rounded_rectangle(
        (left + die_pad, top + die_pad, right - die_pad, bottom - die_pad),
        radius=max(2, size // 30),
        fill=(210, 250, 240, 235),
    )

    # Flash mark (chevron + contact)
    tw = size * 0.09
    th = size * 0.08
    cd.polygon(
        [
            (cx, cy - th * 0.05 + offset * 0.3),
            (cx - tw, cy + th * 0.65 + offset * 0.3),
            (cx + tw, cy + th * 0.65 + offset * 0.3),
        ],
        fill=(22, 34, 48, 255),
    )
    s = size * 0.04
    cd.rounded_rectangle(
        (cx - s, cy - th * 0.75 + offset * 0.3, cx + s, cy - th * 0.15 + offset * 0.3),
        radius=max(1, size // 64),
        fill=(90, 220, 255, 255),
    )

    canvas = Image.alpha_composite(canvas, chip)
    return canvas


def render_from_source(size: int, source: Image.Image) -> Image.Image:
    """Scale a master Fluent artwork into a transparent square canvas."""
    img = source.convert("RGBA")
    # Fit artwork into the square with smooth scaling
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    return img


def make_icon(size: int, source: Image.Image | None) -> Image.Image:
    if source is not None:
        return render_from_source(size, source)
    return draw_fluent_logo(size)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    source = Image.open(SOURCE).convert("RGBA") if SOURCE.is_file() else None
    if source is not None:
        print(f"Using source artwork: {SOURCE}")
    else:
        print("No app_icon_source.png — drawing Fluent glyph")

    master = make_icon(512, source)
    master.save(OUT / "app_icon.png", "PNG", optimize=True)
    master.save(OUT / "logo.png", "PNG", optimize=True)

    # Also keep a 256 master for docs / store listings
    make_icon(256, source).save(OUT / "app_icon_256.png", "PNG", optimize=True)

    frames = [make_icon(s, source) for s in ICO_SIZES]
    frames[-1].save(
        OUT / "app_icon.ico",
        format="ICO",
        sizes=[(s, s) for s in ICO_SIZES],
        append_images=frames[:-1],
    )
    print(f"Wrote Fluent icons to {OUT}")


if __name__ == "__main__":
    main()
