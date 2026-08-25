#!/usr/bin/env python3
"""
Typeset OBJECTION-PACK.md as a branded PDF.

    pip install playwright markdown && python3 content-ops/lead-magnet/build_pdf.py
"""
import base64
import os
import re
import markdown
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "assets", "fonts")
SRC = os.path.join(HERE, "OBJECTION-PACK.md")
OUT = os.path.join(HERE, "The-Objection-Pack.pdf")
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


def font_face(family, filename, weight=400):
    with open(os.path.join(FONTS, filename), "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode()
    return (f"@font-face{{font-family:'{family}';font-weight:{weight};"
            f"src:url(data:font/ttf;base64,{b64}) format('truetype');}}")


def build_html():
    raw = open(SRC).read()
    # Drop the title block; the cover page carries it instead.
    body_md = re.sub(r"^# The Objection Pack.*?\n---\n", "", raw, flags=re.S).strip()
    html_body = markdown.markdown(body_md, extensions=["extra", "sane_lists"])
    # Blockquotes are the scripts - give them the red rule treatment.
    html_body = html_body.replace("<blockquote>", '<blockquote class="script">')

    faces = "".join([
        font_face("Archivo", "ArchivoBlack.ttf"),
        font_face("InterS", "Inter-SemiBold.ttf", 600),
        font_face("InterR", "Inter-Regular.ttf"),
    ])

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
{faces}
@page {{ size: Letter; margin: 0.85in 0.9in; }}
* {{ box-sizing: border-box; }}
body {{ font-family: InterR, Georgia, serif; color: #17171A; font-size: 10.5pt;
       line-height: 1.62; margin: 0; }}

.cover {{ page-break-after: always; background: #0B0B0C; color: #FAFAFA;
          height: 9.3in; margin: -0.85in -0.9in 0; padding: 1.4in 1.1in;
          display: flex; flex-direction: column; justify-content: space-between; }}
.cover .mark {{ font-family: Archivo; font-size: 15pt; letter-spacing: .16em;
                display: flex; align-items: center; gap: .5em; }}
.dot {{ width: .62em; height: .62em; border-radius: 50%; background: #FF3B30;
        display: inline-block; }}
.cover h1 {{ font-family: Archivo; font-size: 56pt; line-height: .97; margin: 0;
             letter-spacing: -.01em; }}
.cover h1 em {{ color: #FF3B30; font-style: normal; }}
.cover .sub {{ font-family: InterS; font-size: 13.5pt; color: #8A8A8E;
               margin-top: .85em; max-width: 24ch; line-height: 1.42; }}
.cover .foot {{ font-family: InterS; font-size: 10pt; color: #8A8A8E;
                letter-spacing: .05em; }}

h2 {{ font-family: Archivo; font-size: 18.5pt; line-height: 1.15;
      margin: 0 0 .12in; page-break-before: always; page-break-after: avoid;
      letter-spacing: -.005em; }}
h2#how-to-use-this {{ page-break-before: avoid; }}

p {{ margin: 0 0 .62em; }}
strong {{ font-family: InterS; font-weight: 600; }}
em {{ color: #55555C; font-style: italic; }}

blockquote.script {{ margin: .95em 0; padding: .8em 1em .8em 1.05em;
   border-left: 3px solid #FF3B30; background: #F5F5F6;
   border-radius: 0 5px 5px 0; page-break-inside: avoid; }}
blockquote.script p {{ font-family: InterS; font-size: 11.5pt; line-height: 1.5;
   margin: 0; color: #0B0B0C; font-style: normal; }}

hr {{ border: 0; height: 0; margin: 0; }}
ol {{ padding-left: 1.15em; }}
ol li {{ margin-bottom: .5em; }}
</style></head><body>
<div class="cover">
  <div class="mark"><span class="dot"></span>COLD OPEN</div>
  <div>
    <h1>THE<br>OBJECTION<br><em>PACK</em></h1>
    <div class="sub">12 cold call objections and the exact words that beat them.</div>
  </div>
  <div class="foot">MECHANICS, NOT MOTIVATION</div>
</div>
{html_body}
</body></html>"""


def main():
    tmp = os.path.join(HERE, "_build.html")
    open(tmp, "w").write(build_html())
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME)
        pg = b.new_page()
        pg.goto("file://" + tmp)
        pg.emulate_media(media="print")
        pg.pdf(path=OUT, format="Letter", print_background=True)
        b.close()
    os.remove(tmp)
    print(f"{OUT}  {os.path.getsize(OUT)//1024} KB")


if __name__ == "__main__":
    main()
