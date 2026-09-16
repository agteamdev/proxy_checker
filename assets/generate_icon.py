"""
One-off script that generates the Proxy Checker app icon.
Not part of the shipped application - run once to (re)produce assets/icon.png
and assets/icon.ico. Requires Pillow: pip install pillow
"""

import math
from PIL import Image, ImageDraw

SIZE = 512


def make_icon() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # -- rounded-square background with a vertical gradient ----------------
    top_color = (22, 51, 89)     # dark navy blue
    bottom_color = (16, 185, 129)  # teal/green
    radius = 96
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=radius, fill=255)

    gradient = Image.new("RGB", (SIZE, SIZE))
    for y in range(SIZE):
        t = y / (SIZE - 1)
        color = tuple(int(top_color[i] + (bottom_color[i] - top_color[i]) * t) for i in range(3))
        for x in range(SIZE):
            gradient.putpixel((x, y), color)
    img.paste(gradient, (0, 0), mask)
    draw = ImageDraw.Draw(img)

    # -- faint network dots/lines in the corners (proxy/network motif) -----
    node_color = (255, 255, 255, 40)
    nodes = [(90, 90), (150, 60), (60, 150)]
    for a, b in [(nodes[0], nodes[1]), (nodes[0], nodes[2])]:
        draw.line([a, b], fill=node_color, width=4)
    for n in nodes:
        draw.ellipse([n[0] - 7, n[1] - 7, n[0] + 7, n[1] + 7], fill=node_color)

    nodes2 = [(SIZE - 90, SIZE - 90), (SIZE - 150, SIZE - 60), (SIZE - 60, SIZE - 150)]
    for a, b in [(nodes2[0], nodes2[1]), (nodes2[0], nodes2[2])]:
        draw.line([a, b], fill=node_color, width=4)
    for n in nodes2:
        draw.ellipse([n[0] - 7, n[1] - 7, n[0] + 7, n[1] + 7], fill=node_color)

    # -- shield shape --------------------------------------------------------
    cx, cy = SIZE // 2, SIZE // 2 + 6
    w, h = 132, 168
    shield = [
        (cx - w, cy - h + 40),
        (cx, cy - h),
        (cx + w, cy - h + 40),
        (cx + w, cy + 10),
        (cx, cy + h),
        (cx - w, cy + 10),
    ]
    draw.polygon(shield, fill=(255, 255, 255, 235))
    draw.line(shield + [shield[0]], fill=(255, 255, 255, 255), width=6, joint="curve")

    # -- checkmark inside the shield -----------------------------------------
    check_color = (16, 122, 91)
    p1 = (cx - 60, cy)
    p2 = (cx - 14, cy + 46)
    p3 = (cx + 68, cy - 56)
    width = 26
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
