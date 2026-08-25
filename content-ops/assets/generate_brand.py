#!/usr/bin/env python3
"""
Generate the Cold Open brand assets.

    python3 content-ops/assets/generate_brand.py            # all static assets
    python3 content-ops/assets/generate_brand.py --day 7 --calls 23   # + scoreboard

Outputs to content-ops/assets/brand/.
"""
import argparse
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
OUT = os.path.join(HERE, "brand")

BG      = (11, 11, 12)
TEXT    = (250, 250, 250)
ACCENT  = (255, 59, 48)
MUTED   = (138, 138, 142)

WORDMARK = "COLD OPEN"
TAGLINE  = "the first 8 seconds decide the call"


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def measure(text, f, tracking=0):
    """Width of text including per-character tracking."""
    if not text:
        return 0
    return f.getlength(text) + tracking * (len(text) - 1)


def cap_height(f):
    b = f.getbbox("H")
    return b[3] - b[1]


def draw_tracked(d, x, baseline, text, f, fill, tracking=0):
    """Draw letter-spaced text sitting on `baseline`."""
    for ch in text:
        d.text((x, baseline), ch, font=f, fill=fill, anchor="ls")
        x += f.getlength(ch) + tracking


def lockup(d, cx, cy, mark_size, tag_size, dot_r, gap, tracking, tag_tracking, with_tag=True):
    """Centered red dot + wordmark, tagline underneath. cy is the wordmark's vertical center."""
    fm = font("ArchivoBlack.ttf", mark_size)
    ch = cap_height(fm)
    baseline = cy + ch / 2                     # cap block centred on cy
    word_w = measure(WORDMARK, fm, tracking)
    x = cx - (dot_r * 2 + gap + word_w) / 2

    d.ellipse([x, cy - dot_r, x + dot_r * 2, cy + dot_r], fill=ACCENT)
    draw_tracked(d, x + dot_r * 2 + gap, baseline, WORDMARK, fm, TEXT, tracking)

    if with_tag:
        ft = font("Inter-SemiBold.ttf", tag_size)
        tag_w = measure(TAGLINE, ft, tag_tracking)
        draw_tracked(d, cx - tag_w / 2, baseline + mark_size * 0.55, TAGLINE, ft, MUTED, tag_tracking)


def avatar(size=1024):
    img = Image.new("RGB", (size, size), BG)
    d = ImageDraw.Draw(img)
    r = size * 0.34                      # dot is 68% of the frame — holds at 24px
    c = size / 2
    d.ellipse([c - r, c - r, c + r, c + r], fill=ACCENT)
    img.save(os.path.join(OUT, f"avatar-{size}.png"))
    return img


def banner(name, w, h, mark_size, tag_size, cy_ratio=0.5, safe=None):
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    lockup(
        d, w / 2, h * cy_ratio,
        mark_size=mark_size,
        tag_size=tag_size,
        dot_r=mark_size * 0.27,
        gap=mark_size * 0.34,
        tracking=mark_size * 0.02,
        tag_tracking=tag_size * 0.06,
    )
    img.save(os.path.join(OUT, name))


def scoreboard(day, calls, total_calls=100, total_days=30):
    W, H = 1080, 1920
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # Header lockup, small, top-left
    fh = font("ArchivoBlack.ttf", 40)
    d.ellipse([80, 96, 116, 132], fill=ACCENT)
    draw_tracked(d, 134, 96 + cap_height(fh), WORDMARK, fh, TEXT, 5)

    # The number
    fbig = font("JetBrainsMono-Bold.ttf", 400)
    fsml = font("JetBrainsMono-Bold.ttf", 150)
    num = str(calls)
    den = f"/{total_calls}"
    nw, dw = fbig.getlength(num), fsml.getlength(den)
    x = (W - (nw + dw)) / 2

    # Centre the whole stack (number + label + bar + day line) on the frame.
    num_cap = cap_height(fbig)
    stack_h = num_cap + 400
    baseline = (H - stack_h) / 2 + num_cap

    d.text((x, baseline), num, font=fbig, fill=TEXT, anchor="ls")
    d.text((x + nw, baseline), den, font=fsml, fill=MUTED, anchor="ls")

    # Label
    fl = font("ArchivoBlack.ttf", 62)
    label = "COLD CALLS"
    lw = measure(label, fl, 10)
    draw_tracked(d, (W - lw) / 2, baseline + 150, label, fl, TEXT, 10)

    # Progress bar
    bx, bw, by, bh = 140, W - 280, baseline + 255, 14
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=bh / 2, fill=(38, 38, 40))
    filled = max(bh, bw * min(calls / total_calls, 1.0))
    d.rounded_rectangle([bx, by, bx + filled, by + bh], radius=bh / 2, fill=ACCENT)

    # Day counter
    fd = font("Inter-SemiBold.ttf", 46)
    day_txt = f"DAY {day} OF {total_days}"
    dwid = measure(day_txt, fd, 6)
    draw_tracked(d, (W - dwid) / 2, by + 100, day_txt, fd, MUTED, 6)

    out = os.path.join(OUT, f"scoreboard-day{day:02d}.png")
    img.save(out)
    return out


def legibility_sheet():
    """Proof the avatar still reads at real display sizes."""
    av = Image.open(os.path.join(OUT, "avatar-1024.png"))
    sizes = [200, 112, 64, 40, 24]
    pad, gap = 40, 30
    W = pad * 2 + sum(sizes) + gap * (len(sizes) - 1)
    H = pad * 2 + max(sizes) + 50
    sheet = Image.new("RGB", (W, H), (24, 24, 26))
    d = ImageDraw.Draw(sheet)
    f = font("Inter-Regular.ttf", 18)
    x = pad
    for s in sizes:
        thumb = av.resize((s, s), Image.LANCZOS)
        mask = Image.new("L", (s, s), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, s, s], fill=255)   # platforms crop to a circle
        y = pad + (max(sizes) - s)
        sheet.paste(thumb, (x, y), mask)
        lbl = f"{s}px"
        d.text((x + (s - f.getlength(lbl)) / 2, pad + max(sizes) + 16), lbl, font=f, fill=MUTED)  # noqa
        x += s + gap
    sheet.save(os.path.join(OUT, "avatar-legibility.png"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", type=int, default=1)
    ap.add_argument("--calls", type=int, default=0)
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)

    avatar(1024)
    avatar(400)
    # X: avatar overlaps bottom-left, so the lockup sits above center
    banner("banner-x-1500x500.png", 1500, 500, mark_size=110, tag_size=34, cy_ratio=0.42)
    # YouTube: everything critical must live in the centered 1235x338 TV-safe area
    banner("banner-youtube-2560x1440.png", 2560, 1440, mark_size=150, tag_size=44)
    banner("banner-facebook-1640x664.png", 1640, 664, mark_size=130, tag_size=38, cy_ratio=0.44)
    legibility_sheet()
    sb = scoreboard(args.day, args.calls)

    for f in sorted(os.listdir(OUT)):
        p = os.path.join(OUT, f)
        print(f"  {f:38s} {Image.open(p).size[0]:>5}x{Image.open(p).size[1]:<5} {os.path.getsize(p)//1024:>4} KB")
    print(f"\nScoreboard: {os.path.basename(sb)}  (regenerate daily with --day N --calls N)")


if __name__ == "__main__":
    main()
