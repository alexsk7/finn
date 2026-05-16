"""Generate static/favicon.ico from the finn icon mark.

Draws the rounded-square chart icon at 16, 32, and 48px sizes,
then packs them into a single multi-resolution .ico file.

Usage: uv run python scripts/gen_favicon.py
"""

from pathlib import Path
from PIL import Image, ImageDraw


# ── Palette (matches style.css CSS variables) ─────────────────────────────────
BG      = (19,  24,  32)   # --bg2
BORDER  = (35,  45,  63)   # --border
BLUE    = (64, 128, 240)   # --accent
GREEN   = (34, 211, 160)   # --green
GRID    = (26,  32,  48)   # subtle grid line


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def draw_icon(size: int) -> Image.Image:
    scale = size / 48  # design at 48px, then scale
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Rounded background square (full canvas)
    r = max(2, int(size * 0.175))
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=BG + (255,), outline=BORDER + (180,))

    # Chart data points — normalised to [0,1] within the icon content area
    # (x, y) where y=0 is top, y=1 is bottom
    points_norm = [
        (0.10, 0.82),
        (0.28, 0.64),
        (0.43, 0.71),
        (0.58, 0.50),
        (0.72, 0.38),
        (0.88, 0.18),
    ]

    pad = int(size * 0.15)
    w = size - pad * 2
    h = size - pad * 2

    def pt(nx, ny):
        return (pad + nx * w, pad + ny * h)

    # Grid lines (only visible at 32px+)
    if size >= 32:
        for gy in [0.33, 0.58, 0.82]:
            x0, y0 = pt(0.08, gy)
            x1, _  = pt(0.92, gy)
            d.line([(x0, y0), (x1, y0)], fill=GRID + (180,), width=1)

    # Area fill under chart — manual trapezoid in dark blue alpha
    peak = pt(*points_norm[-1])
    base_right = pt(points_norm[-1][0], 0.88)
    base_left  = pt(points_norm[0][0], 0.88)
    poly = [pt(nx, ny) for nx, ny in points_norm] + [base_right, base_left]
    # Draw as multiple semi-transparent layers for a soft fill
    fill_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fill_img)
    fd.polygon(poly, fill=BLUE + (35,))
    img = Image.alpha_composite(img, fill_img)
    d = ImageDraw.Draw(img)

    # Chart line — graduated color from dim to bright along the path
    pixel_pts = [pt(nx, ny) for nx, ny in points_norm]
    n = len(pixel_pts) - 1
    lw = max(1, int(size * 0.055))
    for i in range(n):
        t = i / n
        color = lerp_color((40, 80, 160), BLUE, t) + (255,)
        d.line([pixel_pts[i], pixel_pts[i + 1]], fill=color, width=lw)

    # Peak dot (green)
    px, py = pixel_pts[-1]
    dot_r = max(1.5, size * 0.075)
    d.ellipse(
        [px - dot_r, py - dot_r, px + dot_r, py + dot_r],
        fill=GREEN + (255,),
    )

    # Glow ring around peak dot (only at 32px+)
    if size >= 32:
        ring_r = dot_r + max(1, int(size * 0.05))
        d.ellipse(
            [px - ring_r, py - ring_r, px + ring_r, py + ring_r],
            outline=GREEN + (80,),
            width=1,
        )

    return img


def main():
    out_path = Path(__file__).parent.parent / "static" / "favicon.ico"
    sizes = [16, 32, 48]

    frames = [draw_icon(s) for s in sizes]

    # Pillow's ICO writer takes a single source image + a `sizes` list;
    # it resamples to each size internally. We use our largest frame as
    # the source so the hand-crafted detail is preserved at 48px and
    # down-sampled cleanly to 32 and 16.
    largest = frames[-1]  # 48px
    largest.save(
        out_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
    )
    print(f"Written {out_path}  ({', '.join(str(s)+'px' for s in sizes)})")

    # Also save a 512px PNG for use as an app icon / PWA icon
    png_path = Path(__file__).parent.parent / "static" / "icon-512.png"
    draw_icon(512).save(png_path, format="PNG")
    print(f"Written {png_path}  (512px PNG)")


if __name__ == "__main__":
    main()
