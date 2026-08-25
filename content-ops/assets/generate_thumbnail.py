#!/usr/bin/env python3
"""
Branded YouTube thumbnails. 1280x720, designed to survive 210x118.

  python3 content-ops/assets/generate_thumbnail.py \
      --top "50 COLD CALLS" --bottom "ONE PATTERN" --out t01.png

  --accent bottom|top|none   which line gets brand red (default: bottom)
"""
import argparse
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
OUT_DIR = os.path.join(HERE, "thumbnails")

W, H = 1280, 720
BG, TEXT, ACCENT, MUTED = (11, 11, 12), (250, 250, 250), (255, 59, 48), (138, 138, 142)
MARGIN = 88


def fit(text, max_w, start=190, floor=54):
    """Largest Archivo Black size where `text` fits max_w."""
    size = start
    while size > floor:
        f = ImageFont.truetype(os.path.join(FONTS, "ArchivoBlack.ttf"), size)
        if f.getlength(text) <= max_w:
            return f
        size -= 3
    return ImageFont.truetype(os.path.join(FONTS, "ArchivoBlack.ttf"), floor)


def cap(f):
    b = f.getbbox("H")
    return b[3] - b[1]


def build(top, bottom, accent, out):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    avail = W - MARGIN * 2

    lines = [l for l in (top, bottom) if l]
    fonts = [fit(l, avail) for l in lines]
    caps = [cap(f) for f in fonts]
    gap = 34
    block = sum(caps) + gap * (len(caps) - 1)
    y = (H - block) / 2 + caps[0]

    for i, (line, f, c) in enumerate(zip(lines, fonts, caps)):
        is_accent = (accent == "top" and i == 0) or (accent == "bottom" and i == len(lines) - 1)
        colour = ACCENT if is_accent else TEXT
        d.text(((W - f.getlength(line)) / 2, y), line, font=f, fill=colour, anchor="ls")
        if i + 1 < len(lines):
            y += gap + caps[i + 1]

    # Brand mark, bottom-left. Small enough not to compete with the text.
    fm = ImageFont.truetype(os.path.join(FONTS, "ArchivoBlack.ttf"), 30)
    dot_r = 13
    by = H - 62
    d.ellipse([MARGIN, by - dot_r, MARGIN + dot_r * 2, by + dot_r], fill=ACCENT)
    x = MARGIN + dot_r * 2 + 18
    for ch in "COLD OPEN":
        d.text((x, by + cap(fm) / 2), ch, font=fm, fill=MUTED, anchor="ls")
        x += fm.getlength(ch) + 4

    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, out)
    img.save(path)

    # Proof it survives the size it is actually browsed at.
    img.resize((210, 118), Image.LANCZOS).save(path.replace(".png", "-210px.png"))
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", required=True)
    ap.add_argument("--bottom", default="")
    ap.add_argument("--accent", choices=["top", "bottom", "none"], default="bottom")
    ap.add_argument("--out", default="thumbnail.png")
    a = ap.parse_args()
    p = build(a.top.upper(), a.bottom.upper(), a.accent, a.out)
    print(f"{p}\n{p.replace('.png','-210px.png')}  (browse-size proof)")


if __name__ == "__main__":
    main()
