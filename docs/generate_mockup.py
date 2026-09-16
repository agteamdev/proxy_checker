"""
One-off script that generates a mockup screenshot resembling the app's
layout, used as a placeholder in the README until a real screenshot is
captured (see the "Screenshot" section of README.md).
Requires Pillow: pip install pillow
"""

from PIL import Image, ImageDraw, ImageFont

W, H = 1020, 560
BG = (240, 240, 240)
PANEL_BG = (255, 255, 255)
BORDER = (190, 190, 190)
TEXT = (30, 30, 30)
MUTED = (110, 110, 110)
ACCENT = (46, 125, 200)
HEADER_BG = (235, 238, 242)

FLAGS = [
    ((196, 30, 58), (255, 255, 255)),   # red/white stripes look
    ((0, 82, 180), (255, 206, 0)),      # blue/yellow
    ((0, 122, 61), (255, 255, 255)),    # green/white
    ((206, 17, 38), (255, 255, 255)),   # red/white
]

ROWS = [
    ("US", "185.23.14.9", "1080", "SOCKS5", "Elite", "142"),
    ("DE", "91.203.17.201", "4145", "SOCKS4", "Anonymous", "268"),
    ("FR", "51.68.94.12", "1080", "SOCKS5", "Elite", "199"),
    ("NL", "185.220.101.7", "9050", "SOCKS5", "Anonymous", "310"),
    ("BR", "177.54.16.88", "4153", "SOCKS4", "Transparent", "455"),
    ("JP", "133.18.201.4", "1080", "SOCKS5", "Elite", "221"),
]


def font(size, bold=False):
    names = ["DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except Exception:
            continue
    return ImageFont.load_default()


def draw_flag(draw, x, y, w, h, colors):
    c1, c2 = colors
    draw.rectangle([x, y, x + w // 2, y + h], fill=c1)
    draw.rectangle([x + w // 2, y, x + w, y + h], fill=c2)
    draw.rectangle([x, y, x + w, y + h], outline=(180, 180, 180))


def main():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    f_title = font(13, bold=True)
    f_label = font(12)
    f_small = font(11)
    f_header = font(12, bold=True)

    left_w = 300
    pad = 14

    # left panel
    draw.rectangle([pad, pad, left_w, H - pad], fill=PANEL_BG, outline=BORDER)
    draw.rectangle([pad + 10, pad + 10, left_w - 10, pad + 90], outline=BORDER)
    draw.text((pad + 18, pad + 16), "Settings", font=f_title, fill=TEXT)
    draw.text((pad + 18, pad + 42), "Threads:", font=f_label, fill=TEXT)
    draw.rectangle([pad + 90, pad + 38, pad + 140, pad + 58], outline=BORDER, fill=(250, 250, 250))
    draw.text((pad + 98, pad + 42), "100", font=f_label, fill=TEXT)
    draw.text((pad + 150, pad + 42), "Timeout (s):", font=f_label, fill=TEXT)
    draw.rectangle([pad + 236, pad + 38, pad + 276, pad + 58], outline=BORDER, fill=(250, 250, 250))
    draw.text((pad + 244, pad + 42), "8", font=f_label, fill=TEXT)

    btn_y = pad + 100
    draw.rectangle([pad + 10, btn_y, pad + 90, btn_y + 28], fill=(225, 225, 225), outline=BORDER)
    draw.text((pad + 30, btn_y + 6), "Start", font=f_label, fill=TEXT)
    draw.rectangle([pad + 98, btn_y, pad + 178, btn_y + 28], fill=(240, 240, 240), outline=BORDER)
    draw.text((pad + 118, btn_y + 6), "Stop", font=f_label, fill=MUTED)

    bar_y = btn_y + 40
    draw.rectangle([pad + 10, bar_y, left_w - 10, bar_y + 16], outline=BORDER, fill=(235, 235, 235))
    draw.rectangle([pad + 10, bar_y, pad + 190, bar_y + 16], fill=ACCENT)

    draw.text((pad + 10, bar_y + 24), "Checked 6532/8204", font=f_small, fill=MUTED)

    log_y = bar_y + 50
    draw.rectangle([pad + 10, log_y, left_w - 10, H - pad - 14], outline=BORDER)
    draw.text((pad + 16, log_y + 6), "Log", font=f_title, fill=TEXT)
    log_lines = [
        "Detecting your public IP...",
        "Downloading proxy lists...",
        "Checking 8204 proxies with 100 threads...",
        "Resolving proxy countries...",
        "Finished: 47 live proxies saved.",
    ]
    ly = log_y + 30
    for line in log_lines:
        draw.text((pad + 16, ly), line, font=f_small, fill=MUTED)
        ly += 18

    # right panel
    rx = left_w + pad
    draw.rectangle([rx, pad, W - pad, H - pad], fill=PANEL_BG, outline=BORDER)
    draw.text((rx + 14, pad + 10), "Live proxies", font=f_title, fill=TEXT)
    draw.text((W - pad - 70, pad + 10), "47 found", font=f_small, fill=MUTED)

    fy = pad + 36
    draw.text((rx + 14, fy), "Search IP:", font=f_small, fill=TEXT)
    draw.rectangle([rx + 78, fy - 3, rx + 190, fy + 17], outline=BORDER)
    draw.text((rx + 210, fy), "Protocol: All", font=f_small, fill=TEXT)
    draw.rectangle([rx + 280, fy - 3, rx + 340, fy + 17], outline=BORDER)
    draw.text((rx + 360, fy), "Anonymity: All", font=f_small, fill=TEXT)
    draw.rectangle([rx + 440, fy - 3, rx + 500, fy + 17], outline=BORDER)

    ty = fy + 30
    cols = [("#", 40), ("Country", 80), ("IP", 150), ("Port", 70), ("Protocol", 90), ("Anonymity", 110), ("Latency (ms)", 120)]
    cx = rx + 10
    draw.rectangle([rx + 4, ty, W - pad - 4, ty + 26], fill=HEADER_BG, outline=BORDER)
    for label, w in cols:
        draw.text((cx + 6, ty + 6), label, font=f_header, fill=TEXT)
        cx += w

    ry = ty + 26
    row_h = 30
    for i, (cc, ip, port, proto, anon, lat) in enumerate(ROWS):
        if i % 2 == 0:
            draw.rectangle([rx + 4, ry, W - pad - 4, ry + row_h], fill=(248, 249, 250))
        cx = rx + 10
        draw.text((cx + 6, ry + 8), str(i + 1), font=f_small, fill=TEXT)
        cx += 40
        draw_flag(draw, cx + 6, ry + 8, 22, 14, FLAGS[i % len(FLAGS)])
        cx += 80
        draw.text((cx + 6, ry + 8), ip, font=f_small, fill=TEXT)
        cx += 150
        draw.text((cx + 6, ry + 8), port, font=f_small, fill=TEXT)
        cx += 70
        draw.text((cx + 6, ry + 8), proto, font=f_small, fill=TEXT)
        cx += 90
        color = {"Elite": (16, 122, 91), "Anonymous": (180, 130, 20), "Transparent": (180, 40, 40)}[anon]
        draw.text((cx + 6, ry + 8), anon, font=f_small, fill=color)
        cx += 110
        draw.text((cx + 6, ry + 8), lat, font=f_small, fill=TEXT)
        ry += row_h
        draw.line([rx + 4, ry, W - pad - 4, ry], fill=BORDER)

    exp_y = H - pad - 40
    draw.rectangle([rx + 10, exp_y, rx + (W - pad - rx) // 2 - 5, exp_y + 26], outline=BORDER, fill=(240, 240, 240))
    draw.text((rx + 30, exp_y + 6), "Export CSV", font=f_small, fill=TEXT)
    draw.rectangle([rx + (W - pad - rx) // 2 + 5, exp_y, W - pad - 10, exp_y + 26], outline=BORDER, fill=(240, 240, 240))
    draw.text((rx + (W - pad - rx) // 2 + 25, exp_y + 6), "Export TXT", font=f_small, fill=TEXT)

    img.save("docs/screenshot.png")
    print("Wrote docs/screenshot.png")


if __name__ == "__main__":
    main()
