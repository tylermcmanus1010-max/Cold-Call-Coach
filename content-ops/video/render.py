#!/usr/bin/env python3
"""
Cold Open video renderer. Scene JSON -> finished MP4.

    python3 content-ops/video/render.py content-ops/video/scenes/short-01.json

Vertical 1080x1920 @ 30fps, brand-locked, captions burned in.
A voiceover track drops in via "audio" in the scene file; without one the
render is silent and caption-led, which is how most short-form is watched.
"""
import argparse
import json
import math
import os
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "assets", "fonts")
OUT = os.path.join(HERE, "out")

W, H, FPS = 1080, 1920, 30
BG, TEXT, ACCENT, MUTED = (11, 11, 12), (250, 250, 250), (255, 59, 48), (138, 138, 142)
SAFE = 110                      # side margin; keeps text clear of platform UI
TOP_SAFE, BOT_SAFE = 300, 480   # platform chrome eats these

_font_cache = {}


def font(name, size):
    key = (name, int(size))
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(os.path.join(FONTS, name), int(size))
    return _font_cache[key]


ARCH = "ArchivoBlack.ttf"
INTS = "Inter-SemiBold.ttf"
MONO = "JetBrainsMono-Bold.ttf"


# ---------- easing ----------
def ease_out(t):
    return 1 - pow(1 - t, 3)


def ease_in_out(t):
    return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2


def clamp01(x):
    return max(0.0, min(1.0, x))


def norm(word):
    """Strip punctuation and case so highlight terms match real text."""
    return word.strip('".,!?\u2014\u2019\'()').lower()


# ---------- text layout ----------
def wrap(text, f, max_w):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        trial = (cur + " " + w_).strip()
        if f.getlength(trial) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def fit_lines(text, fname, max_w, max_h, start, floor=44, lh=1.14):
    """Largest size where the wrapped block fits the box."""
    size = start
    while size > floor:
        f = font(fname, size)
        lines = wrap(text, f, max_w)
        if len(lines) * size * lh <= max_h:
            return f, lines
        size -= 4
    f = font(fname, floor)
    return f, wrap(text, f, max_w)


def measure(text, f, tracking=0):
    """Width of text including per-character tracking."""
    return f.getlength(text) + tracking * (len(text) - 1) if text else 0


def draw_tracked(d, x, y, text, f, fill, tracking=0):
    """Letter-spaced label text drawn from a top-left origin."""
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += f.getlength(ch) + tracking


def draw_block(d, lines, f, cy, fill, alpha=1.0, dy=0, lh=1.14, highlight=None):
    """Centred multi-line block. `highlight` recolours matching words."""
    line_h = f.size * lh
    total = len(lines) * line_h
    y = cy - total / 2 + dy
    col = tuple(int(c * alpha + BG[i] * (1 - alpha)) for i, c in enumerate(fill))
    hcol = tuple(int(c * alpha + BG[i] * (1 - alpha)) for i, c in enumerate(ACCENT))
    for ln in lines:
        if highlight:
            # colour per word so a keyword can pop without breaking centring
            total_w = f.getlength(ln)
            x = (W - total_w) / 2
            for word in ln.split(" "):
                c = hcol if norm(word) in highlight else col
                d.text((x, y), word, font=f, fill=c)
                x += f.getlength(word + " ")
        else:
            d.text(((W - f.getlength(ln)) / 2, y), ln, font=f, fill=col)
        y += line_h
    return total


# ---------- scene renderers ----------
def s_title(d, sc, t):
    """Word-by-word reveal. Used for hooks."""
    f, lines = fit_lines(sc["text"], ARCH, W - SAFE * 2, H - TOP_SAFE - BOT_SAFE, 128)
    words = sc["text"].split()
    n_shown = clamp01(t / max(sc.get("reveal", 0.45), .01)) * len(words)
    hl = {norm(w) for w in sc.get("highlight", [])}
    line_h = f.size * 1.14
    y = H / 2 - (len(lines) * line_h) / 2
    idx = 0
    for ln in lines:
        x = (W - f.getlength(ln)) / 2
        for word in ln.split(" "):
            vis = clamp01(n_shown - idx)
            if vis > 0:
                a = ease_out(vis)
                base = ACCENT if norm(word) in hl else TEXT
                col = tuple(int(c * a + BG[i] * (1 - a)) for i, c in enumerate(base))
                d.text((x, y + (1 - a) * 22), word, font=f, fill=col)
            x += f.getlength(word + " ")
            idx += 1
        y += line_h


def s_line(d, sc, t):
    """Single statement, fades and rises."""
    f, lines = fit_lines(sc["text"], INTS, W - SAFE * 2, H - TOP_SAFE - BOT_SAFE, 84)
    a = ease_out(clamp01(t / 0.22))
    out = ease_out(clamp01((t - 0.88) / 0.12))
    draw_block(d, lines, f, H / 2, TEXT, alpha=a * (1 - out * .9),
               dy=(1 - a) * 40, highlight={norm(w) for w in sc.get("highlight", [])})


def s_script(d, sc, t):
    """The exact-words block: red rule, quoted, the payoff frame."""
    label = sc.get("label", "SAY THIS")
    fl = font(INTS, 44)
    f, lines = fit_lines(sc["text"], INTS, W - SAFE * 2 - 60, 900, 78)
    a = ease_out(clamp01(t / 0.25))
    line_h = f.size * 1.2
    block_h = len(lines) * line_h
    top = H / 2 - block_h / 2
    # rule grows downward
    rh = block_h * ease_out(clamp01(t / 0.35))
    d.rounded_rectangle([SAFE, top, SAFE + 9, top + rh], radius=5, fill=ACCENT)
    lw = fl.getlength(label)
    la = ease_out(clamp01((t - .1) / .2))
    d.text((SAFE + 34, top - 74), label, font=fl,
           fill=tuple(int(c * la + BG[i] * (1 - la)) for i, c in enumerate(MUTED)))
    y = top
    for i, ln in enumerate(lines):
        va = ease_out(clamp01((t - .06 - i * .035) / .22))
        col = tuple(int(c * va + BG[j] * (1 - va)) for j, c in enumerate(TEXT))
        d.text((SAFE + 34, y + (1 - va) * 16), ln, font=f, fill=col)
        y += line_h


def s_counter(d, sc, t):
    """Animated number. For data reveals."""
    target = sc["value"]
    prog = ease_in_out(clamp01(t / 0.55))
    val = int(target * prog)
    fbig = font(MONO, 300)
    txt = f"{val:,}"
    d.text((W / 2, H / 2 - 40), txt, font=fbig, fill=TEXT, anchor="ms")
    fl = font(ARCH, 62)
    la = ease_out(clamp01((t - .5) / .3))
    lab = sc.get("label", "")
    d.text((W / 2, H / 2 + 130), lab, font=fl, anchor="ms",
           fill=tuple(int(c * la + BG[i] * (1 - la)) for i, c in enumerate(ACCENT)))


def s_waveform(d, sc, t):
    """Animated waveform — stands in for call audio moments."""
    bars = 46
    bw, gap = 12, 12
    total = bars * bw + (bars - 1) * gap
    x0 = (W - total) / 2
    cy = H / 2
    for i in range(bars):
        phase = t * 9 + i * 0.42
        amp = (math.sin(phase) * .5 + .5) * (math.sin(i * .31 + t * 3) * .35 + .65)
        h = 26 + amp * 300 * ease_out(clamp01(t / .2))
        col = ACCENT if abs(i - bars / 2) < 5 else (70, 70, 76)
        d.rounded_rectangle([x0 + i * (bw + gap), cy - h / 2,
                             x0 + i * (bw + gap) + bw, cy + h / 2], radius=bw / 2, fill=col)
    cap = sc.get("caption")
    if cap:
        f, lines = fit_lines(cap, INTS, W - SAFE * 2, 400, 64)
        draw_block(d, lines, f, cy + 380, MUTED, alpha=ease_out(clamp01(t / .3)))




def _wrapped(d, text, fname, size, box_w, x, y, fill, lh=1.28, alpha=1.0):
    """Draw wrapped text from a top-left origin. Returns height consumed."""
    f = font(fname, size)
    lines = wrap(text, f, box_w)
    col = tuple(int(c * alpha + BG[i] * (1 - alpha)) for i, c in enumerate(fill))
    for ln in lines:
        d.text((x, y), ln, font=f, fill=col)
        y += size * lh
    return len(lines) * size * lh


def s_split(d, sc, t):
    """Stacked comparison. Wrong on top, struck through; right below in white."""
    lt = sc.get("top_label", "MOST REPS")
    lb = sc.get("bottom_label", "INSTEAD")
    box = W - SAFE * 2
    fl = font(INTS, 42)
    LABEL_GAP, HALF_GAP = 34, 120

    ft, lines_t = fit_lines(sc["top"], INTS, box, 420, 76)
    fb, lines_b = fit_lines(sc["bottom"], INTS, box, 460, 80)
    ht = len(lines_t) * ft.size * 1.22
    hb = len(lines_b) * fb.size * 1.22

    # Centre the whole comparison, not each half independently.
    total = LABEL_GAP + ht + HALF_GAP + LABEL_GAP + hb
    y = H / 2 - total / 2 + LABEL_GAP

    a1 = ease_out(clamp01(t / .22))
    draw_tracked(d, SAFE, y - LABEL_GAP, lt, fl,
                 tuple(int(c * a1 + BG[i] * (1 - a1)) for i, c in enumerate(MUTED)), 5)
    top_y = y
    for ln in lines_t:
        d.text((SAFE, y + (1 - a1) * 20), ln, font=ft,
               fill=tuple(int(c * a1 * .62 + BG[i] * (1 - a1 * .62))
                          for i, c in enumerate(TEXT)))
        y += ft.size * 1.22

    sw = ease_out(clamp01((t - .3) / .3))
    if sw > 0:
        sy = top_y + ht / 2
        d.rounded_rectangle([SAFE, sy - 3, SAFE + box * sw, sy + 3], radius=3, fill=ACCENT)

    a2 = ease_out(clamp01((t - .42) / .26))
    if a2 > 0:
        y += HALF_GAP
        draw_tracked(d, SAFE, y - LABEL_GAP, lb, fl,
                     tuple(int(c * a2 + BG[i] * (1 - a2)) for i, c in enumerate(ACCENT)), 5)
        for ln in lines_b:
            d.text((SAFE, y + (1 - a2) * 22), ln, font=fb,
                   fill=tuple(int(c * a2 + BG[i] * (1 - a2)) for i, c in enumerate(TEXT)))
            y += fb.size * 1.22


def s_timer(d, sc, t):
    """Counts DOWN with a draining ring. For 'you have N seconds' beats."""
    total = sc.get("seconds", 8)
    remaining = max(0, total * (1 - t))
    shown = int(math.ceil(remaining - 1e-6)) if remaining > 0 else 0
    cx, cy, r = W / 2, H / 2, 300
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(38, 38, 42), width=16)
    sweep = 360 * (remaining / total)
    if sweep > 0.5:
        d.arc([cx - r, cy - r, cx + r, cy + r], start=-90, end=-90 + sweep,
              fill=ACCENT, width=16)
    fbig = font(MONO, 260)
    d.text((cx, cy + 20), str(shown), font=fbig, fill=TEXT, anchor="mm")
    lab = sc.get("label", "SECONDS")
    fl = font(ARCH, 54)
    lw = measure(lab, fl, 8)
    draw_tracked(d, cx - lw / 2, cy + r + 120, lab, fl, MUTED, 8)


def s_chat(d, sc, t):
    """Message thread. Left bubbles are them, right bubbles are you."""
    msgs = sc["messages"]           # [{"from":"them"|"you","text":...}]
    box_max = W - SAFE * 2 - 150
    fb = font(INTS, 52)
    pad, gap, radius = 34, 26, 30

    laid = []
    total_h = 0
    for m in msgs:
        lines = wrap(m["text"], fb, box_max)
        wdt = max(fb.getlength(l) for l in lines) + pad * 2
        hgt = len(lines) * fb.size * 1.26 + pad * 2
        laid.append((m, lines, wdt, hgt))
        total_h += hgt + gap

    y = H / 2 - (total_h - gap) / 2
    for i, (m, lines, wdt, hgt) in enumerate(laid):
        a = ease_out(clamp01((t - i * .16) / .22))
        if a <= 0:
            break
        mine = m["from"] == "you"
        x = (W - SAFE - wdt) if mine else SAFE
        fill = ACCENT if mine else (32, 32, 36)
        fill = tuple(int(c * a + BG[j] * (1 - a)) for j, c in enumerate(fill))
        oy = (1 - a) * 26
        d.rounded_rectangle([x, y + oy, x + wdt, y + hgt + oy], radius=radius, fill=fill)
        ty = y + pad + oy
        for ln in lines:
            d.text((x + pad, ty), ln, font=fb,
                   fill=tuple(int(c * a + BG[j] * (1 - a)) for j, c in enumerate(TEXT)))
            ty += fb.size * 1.26
        y += hgt + gap


def s_ranked(d, sc, t):
    """Numbered list building in, with one entry called out in red."""
    items = sc["items"]
    hi = sc.get("highlight_index", -1)
    fn = font(MONO, 58)
    ft = font(INTS, 60)
    row_h = 150
    y = H / 2 - (len(items) * row_h) / 2
    title = sc.get("label")
    if title:
        fl = font(ARCH, 52)
        lw = measure(title, fl, 6)
        la = ease_out(clamp01(t / .2))
        draw_tracked(d, (W - lw) / 2, y - 90, title, fl,
                     tuple(int(c * la + BG[i] * (1 - la)) for i, c in enumerate(MUTED)), 6)
    for i, item in enumerate(items):
        a = ease_out(clamp01((t - .12 - i * .13) / .24))
        if a <= 0:
            break
        on = (i == hi)
        col = ACCENT if on else TEXT
        num = tuple(int(c * a + BG[j] * (1 - a)) for j, c in enumerate(ACCENT if on else MUTED))
        d.text((SAFE, y + (1 - a) * 18), f"{i + 1}", font=fn, fill=num)
        f2, lines = fit_lines(item, INTS, W - SAFE * 2 - 110, row_h, 60)
        yy = y + (1 - a) * 18
        for ln in lines:
            d.text((SAFE + 100, yy), ln, font=f2,
                   fill=tuple(int(c * a + BG[j] * (1 - a)) for j, c in enumerate(col)))
            yy += f2.size * 1.16
        y += row_h


def s_transcript(d, sc, t):
    """Call transcript with one line flagged and annotated."""
    lines_in = sc["lines"]          # [{"who":"REP"|"THEM","text":...}]
    flag = sc.get("flag_index", -1)
    note = sc.get("note")
    fw = font(MONO, 34)
    ft = font(INTS, 52)
    box = W - SAFE * 2 - 130
    y = TOP_SAFE + 120

    for i, ln in enumerate(lines_in):
        a = ease_out(clamp01((t - i * .12) / .2))
        if a <= 0:
            break
        flagged = (i == flag) and t > .45
        who = ln["who"]
        d.text((SAFE, y), who, font=fw,
               fill=tuple(int(c * a + BG[j] * (1 - a)) for j, c in enumerate(
                   ACCENT if flagged else MUTED)))
        col = TEXT if not flagged else ACCENT
        h = _wrapped(d, ln["text"], INTS, 52, box, SAFE + 130, y - 6, col, alpha=a)
        if flagged:
            d.rounded_rectangle([SAFE - 26, y - 18, SAFE - 20, y + h - 4],
                                radius=3, fill=ACCENT)
        y += h + 44

    if note and t > .62:
        a = ease_out(clamp01((t - .62) / .24))
        fn = font(INTS, 46)
        ny = y + 40
        d.rounded_rectangle([SAFE, ny, W - SAFE, ny + 8], radius=4,
                            fill=tuple(int(c * a + BG[j] * (1 - a)) for j, c in enumerate((38, 38, 42))))
        _wrapped(d, note, INTS, 46, W - SAFE * 2, SAFE, ny + 44, MUTED, alpha=a)

RENDERERS = {"title": s_title, "line": s_line, "script": s_script,
             "counter": s_counter, "waveform": s_waveform,
             "split": s_split, "timer": s_timer, "chat": s_chat,
             "ranked": s_ranked, "transcript": s_transcript}


def brand_mark(d, t_global):
    fm = font(ARCH, 34)
    d.ellipse([SAFE, 168, SAFE + 30, 198], fill=ACCENT)
    x = SAFE + 48
    for ch in "COLD OPEN":
        d.text((x, 196), ch, font=fm, fill=MUTED, anchor="ls")
        x += fm.getlength(ch) + 5


def render(spec_path, keep_frames=False):
    spec = json.load(open(spec_path))
    name = spec.get("name", os.path.splitext(os.path.basename(spec_path))[0])
    frames_dir = os.path.join(OUT, f"_frames_{name}")
    os.makedirs(frames_dir, exist_ok=True)
    for f in os.listdir(frames_dir):
        os.remove(os.path.join(frames_dir, f))

    n = 0
    for sc in spec["scenes"]:
        dur = sc.get("duration", 3.0)
        total = int(dur * FPS)
        fn = RENDERERS.get(sc["type"])
        if fn is None:
            sys.exit(f"unknown scene type: {sc['type']}")
        for i in range(total):
            t = i / max(total - 1, 1)
            img = Image.new("RGB", (W, H), BG)
            d = ImageDraw.Draw(img)
            fn(d, sc, t)
            brand_mark(d, n / FPS)
            img.save(os.path.join(frames_dir, f"{n:05d}.png"))
            n += 1

    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    out_path = os.path.join(OUT, f"{name}.mp4")
    cmd = [ff, "-y", "-loglevel", "error", "-framerate", str(FPS),
           "-i", os.path.join(frames_dir, "%05d.png")]
    audio = spec.get("audio")
    if audio and os.path.exists(audio):
        cmd += ["-i", audio, "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
            "-preset", "medium", out_path]
    subprocess.run(cmd, check=True)

    if not keep_frames:
        for f in os.listdir(frames_dir):
            os.remove(os.path.join(frames_dir, f))
        os.rmdir(frames_dir)

    dur = n / FPS
    size = os.path.getsize(out_path) / 1024 / 1024
    print(f"{out_path}\n  {n} frames  {dur:.1f}s  {size:.1f} MB  {W}x{H}@{FPS}")
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--keep-frames", action="store_true")
    a = ap.parse_args()
    render(a.spec, a.keep_frames)
