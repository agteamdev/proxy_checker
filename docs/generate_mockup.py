"""
One-off script that generates a mockup screenshot resembling the app's new
dark-theme layout, used as a placeholder in the README until a real
screenshot is captured.
Requires Pillow: pip install pillow
"""

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 600

BG = (11, 15, 23)
PANEL = (14, 20, 32)
CARD = (18, 24, 38)
CARD_ALT = (15, 21, 33)
BORDER = (31, 41, 55)
TEXT = (229, 231, 235)
MUTED = (139, 147, 167)
ACCENT = (34, 197, 94)
WARNING = (245, 158, 11)
DANGER = (239, 68, 68)
INPUT_BG = (12, 17, 28)
ROW_ALT = (15, 21, 33)

ANON_COLOR = {"Elite": ACCENT, "Anonymous": WARNING, "Transparent": DANGER}

FLAGS = [
    ((196, 30, 58), (255, 255, 255)),
    ((0, 82, 180), (255, 206, 0)),
    ((0, 122, 61), (255, 255, 255)),
    ((206, 17, 38), (255, 255, 255)),
]

ROWS = [
    (1, "US", "185.23.14.9", "1080", "SOCKS5", "Elite", "142"),
    (2, "DE", "91.203.17.201", "4145", "SOCKS4", "Anonymous", "268"),
    (3, "FR", "51.68.94.12", "1080", "SOCKS5", "Elite", "199"),
    (4, "NL", "185.220.101.7", "9050", "SOCKS5", "Anonymous", "310"),
    (5, "BR", "177.54.16.88", "4153", "SOCKS4", "Transparent", "455"),
    (6, "JP", "133.18.201.4", "1080", "SOCKS5", "Elite", "221"),
]


def font(size, bold=False):
    for n in ["DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(n, size)
        except Exception:
            continue
    return ImageFont.load_default()


def rounded(draw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def draw_flag(draw, x, y, w, h, colors):
    c1, c2 = colors
    draw.rectangle([x, y, x + w // 2, y + h], fill=c1)
    draw.rectangle([x + w // 2, y, x + w, y + h], fill=c2)


def checkbox(draw, x, y, size=12, checked=False):
    draw.rounded_rectangle([x, y, x + size, y + size], radius=3, outline=MUTED, width=1)
    if checked:
        draw.rounded_rectangle([x + 2, y + 2, x + size - 2, y + size - 2], radius=2, fill=ACCENT)


def main():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    f_title = font(15, bold=True)
    f_sub = font(10)
    f_label = font(11)
    f_small = font(10)
    f_header = font(10, bold=True)

    # -- header bar --------------------------------------------------------
    draw.rectangle([0, 0, W, 58], fill=PANEL)
    draw.rounded_rectangle([16, 12, 50, 46], radius=8, fill=(15, 23, 42))
    draw.polygon([(33, 16), (44, 21), (44, 32), (33, 42), (22, 32), (22, 21)], fill=ACCENT)
    draw.text((26, 22), "\u2713", font=font(12, bold=True), fill=(255, 255, 255))
    draw.text((60, 14), "Proxy Checker", font=f_title, fill=TEXT)
    draw.text((60, 33), "Fast \u00b7 Reliable \u00b7 Simple", font=f_sub, fill=MUTED)
    draw.ellipse([W - 110, 22, W - 100, 32], fill=ACCENT)
    draw.text((W - 92, 20), "Ready", font=f_label, fill=TEXT)
    draw.line([0, 58, W, 58], fill=BORDER)

    pad = 14
    top = 58 + pad
    left_w = 316

    # -- left panel: settings ------------------------------------------------
    rounded(draw, [pad, top, left_w, top + 150], 8, fill=CARD, outline=BORDER)
    draw.text((pad + 14, top + 12), "\u2699  Settings", font=font(12, bold=True), fill=TEXT)
    draw.text((pad + 14, top + 42), "Threads:", font=f_label, fill=MUTED)
    rounded(draw, [pad + 90, top + 38, pad + 150, top + 60], 4, fill=INPUT_BG, outline=BORDER)
    draw.text((pad + 100, top + 43), "100", font=f_label, fill=TEXT)
    draw.text((pad + 165, top + 42), "Timeout (s):", font=f_label, fill=MUTED)
    rounded(draw, [pad + 250, top + 38, pad + 296, top + 60], 4, fill=INPUT_BG, outline=BORDER)
    draw.text((pad + 260, top + 43), "8", font=f_label, fill=TEXT)

    draw.text((pad + 14, top + 76), "Protocols:", font=f_label, fill=MUTED)
    px = pad + 90
    for name in ["HTTP", "SOCKS4", "SOCKS5"]:
        checkbox(draw, px, top + 78, 12, checked=True)
        draw.text((px + 18, top + 76), name, font=f_small, fill=TEXT)
        px += 66

    draw.text((pad + 14, top + 108), "Proxies needed:", font=f_label, fill=MUTED)
    rounded(draw, [pad + 118, top + 104, pad + 168, top + 126], 4, fill=INPUT_BG, outline=BORDER)
    draw.text((pad + 128, top + 109), "0", font=f_label, fill=TEXT)
    draw.text((pad + 176, top + 110), "(0 = unlimited)", font=f_small, fill=MUTED)

    btn_y = top + 162
    rounded(draw, [pad, btn_y, pad + 145, btn_y + 32], 6, fill=ACCENT)
    draw.text((pad + 48, btn_y + 9), "\u25B8 Start", font=f_label, fill=(5, 46, 22))
    rounded(draw, [pad + 155, btn_y, pad + 300, btn_y + 32], 6, fill=INPUT_BG, outline=BORDER)
    draw.text((pad + 195, btn_y + 9), "\u25A0 Stop", font=f_label, fill=MUTED)

    bar_y = btn_y + 44
    rounded(draw, [pad, bar_y, left_w - pad + pad - 14 + 300, bar_y + 8], 4, fill=INPUT_BG)
    rounded(draw, [pad, bar_y, pad + 210, bar_y + 8], 4, fill=ACCENT)
    draw.text((pad, bar_y + 16), "Checked 6532/8204", font=f_small, fill=MUTED)

    log_y = bar_y + 44
    rounded(draw, [pad, log_y, left_w, H - pad], 8, fill=CARD, outline=BORDER)
    draw.text((pad + 14, log_y + 10), "\u2637  Log", font=font(12, bold=True), fill=TEXT)
    log_lines = [
        ("Detecting your public IP...", MUTED),
        ("Downloading proxy lists...", MUTED),
        ("Checking 8204 proxies with 100 threads...", ACCENT),
        ("Resolving proxy countries...", MUTED),
        ("Finished: 47 live proxies found.", ACCENT),
    ]
    ly = log_y + 38
    for line, color in log_lines:
        draw.text((pad + 14, ly), line, font=f_small, fill=color)
        ly += 18

    # -- right panel: results -------------------------------------------------
    rx = left_w + pad * 2
    rounded(draw, [rx, top, W - pad, H - pad], 8, fill=CARD, outline=BORDER)
    draw.text((rx + 14, top + 12), "\u25A3  Live proxies", font=font(12, bold=True), fill=TEXT)
    draw.text((W - pad - 70, top + 14), "47 found", font=f_small, fill=MUTED)

    fy = top + 42
    draw.text((rx + 14, fy), "Search IP:", font=f_small, fill=MUTED)
    rounded(draw, [rx + 78, fy - 4, rx + 200, fy + 18], 4, fill=INPUT_BG, outline=BORDER)
    draw.text((rx + 220, fy), "Protocol: All", font=f_small, fill=MUTED)
    rounded(draw, [rx + 300, fy - 4, rx + 370, fy + 18], 4, fill=INPUT_BG, outline=BORDER)
    draw.text((rx + 390, fy), "Anonymity: All", font=f_small, fill=MUTED)
    rounded(draw, [rx + 470, fy - 4, rx + 540, fy + 18], 4, fill=INPUT_BG, outline=BORDER)

    ty = fy + 32
    cols = [("", 34), ("#", 34), ("", 28), ("Country", 64), ("IP", 140), ("Port", 60),
            ("Protocol", 78), ("Anonymity", 100), ("Latency (ms)", 110)]
    draw.rectangle([rx + 4, ty, W - pad - 4, ty + 26], fill=CARD_ALT)
    cx = rx + 10
    for i, (label, w) in enumerate(cols):
        if i == 0:
            checkbox(draw, cx + 8, ty + 7, 12, checked=False)
        elif label:
            draw.text((cx + 4, ty + 7), label, font=f_header, fill=MUTED)
        cx += w
    draw.line([rx + 4, ty + 26, W - pad - 4, ty + 26], fill=BORDER)

    ry = ty + 26
    row_h = 32
    for i, (num, cc, ip, port, proto, anon, lat) in enumerate(ROWS):
        rowbg = CARD if i % 2 == 0 else ROW_ALT
        draw.rectangle([rx + 4, ry, W - pad - 4, ry + row_h], fill=rowbg)
        cx = rx + 10
        checkbox(draw, cx + 8, ry + 10, 12, checked=(i == 1))
        cx += 34
        draw.text((cx + 6, ry + 9), str(num), font=f_small, fill=MUTED)
        cx += 34
        draw_flag(draw, cx + 4, ry + 9, 20, 13, FLAGS[i % len(FLAGS)])
        cx += 28
        draw.text((cx + 10, ry + 9), cc, font=f_small, fill=TEXT)
        cx += 64
        draw.text((cx + 6, ry + 9), ip, font=f_small, fill=TEXT)
        cx += 140
        draw.text((cx + 6, ry + 9), port, font=f_small, fill=TEXT)
        cx += 60
        draw.text((cx + 6, ry + 9), proto, font=f_small, fill=TEXT)
        cx += 78
        draw.text((cx + 6, ry + 9), anon, font=font(10, bold=True), fill=ANON_COLOR[anon])
        cx += 100
        draw.text((cx + 6, ry + 9), lat, font=f_small, fill=TEXT)
        ry += row_h
        draw.line([rx + 4, ry, W - pad - 4, ry], fill=BORDER)

    exp_y = H - pad - 38
    mid = rx + (W - pad - rx) // 2
    rounded(draw, [rx + 10, exp_y, mid - 5, exp_y + 26], 6, fill=INPUT_BG, outline=BORDER)
    draw.text((rx + 40, exp_y + 6), "\u2B07 Export CSV", font=f_small, fill=TEXT)
    rounded(draw, [mid + 5, exp_y, W - pad - 10, exp_y + 26], 6, fill=INPUT_BG, outline=BORDER)
    draw.text((mid + 40, exp_y + 6), "\u2B07 Export TXT", font=f_small, fill=TEXT)

    img.save("docs/screenshot.png")
    print("Wrote docs/screenshot.png")


if __name__ == "__main__":
    main()
