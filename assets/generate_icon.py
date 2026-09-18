"""
One-off script that generates the Proxy Checker app icon.
Not part of the shipped application - run once to (re)produce assets/icon.png
and assets/icon.ico. Requires Pillow: pip install pillow
"""

from PIL import Image, ImageDraw

SIZE = 512


def make_icon() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # -- flat dark rounded-square background (matches the app's dark theme) --
    bg_color = (15, 23, 42)       # slate-900
    radius = 108
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=radius, fill=255)
    flat_bg = Image.new("RGBA", (SIZE, SIZE), bg_color + (255,))
    img.paste(flat_bg, (0, 0), mask)
    draw = ImageDraw.Draw(img)

    # -- shield shape, green outline + fill (accent color) -------------------
    accent = (34, 197, 94)   # emerald-500
    cx, cy = SIZE // 2, SIZE // 2 + 4
    w, h = 138, 172
    shield = [
        (cx - w, cy - h + 42),
        (cx, cy - h),
        (cx + w, cy - h + 42),
        (cx + w, cy + 14),
        (cx, cy + h),
        (cx - w, cy + 14),
    ]
    draw.polygon(shield, fill=accent)
    draw.line(shield + [shield[0]], fill=(74, 222, 128), width=8, joint="curve")  # lighter green edge

    # -- white checkmark inside the shield -------------------------------------
    check_color = (255, 255, 255)
    p1 = (cx - 58, cy)
    p2 = (cx - 12, cy + 48)
    p3 = (cx + 70, cy - 58)
    width = 28
    draw.line([p1, p2], fill=check_color, width=width)
    draw.line([p2, p3], fill=check_color, width=width)
    for p in (p1, p2, p3):
        draw.ellipse([p[0] - width / 2, p[1] - width / 2, p[0] + width / 2, p[1] + width / 2], fill=check_color)

    return img


if __name__ == "__main__":
    icon = make_icon()
    icon.save("assets/icon.png")

    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icon.save("assets/icon.ico", sizes=ico_sizes)

    print("Wrote assets/icon.png and assets/icon.ico")
