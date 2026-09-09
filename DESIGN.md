# The design bar

**Reference: https://www.aashishthakuri.com** — captured 2026-09-08 in
`design/reference/`. Every page we ship is judged against it. Not copied from
it; judged against it. The question is always the same: *put our page next to
those captures — does it look like it belongs, or like a template?*

The captures are ours because the site will change or vanish and the bar
should not.

---

## What it does

Look at `design/reference/` in order. Eight frames, phone width unless noted.

| | What is happening |
|---|---|
| `01-hero-phone` | Near-black ground with visible **grain** and a faint grid. The headline is the accent colour, enormous, stacked, tightly tracked. Real objects as cut-outs with a paper edge. A tiny mono label pinned like a tag. |
| `02-about-paper` | Switches to **paper** — off-white, still grainy, still gridded. A solid-fill **sticker label** with a hard offset shadow, tilted two degrees. Serif display heading with one word in the second accent. Serif body at a reading size. |
| `03-experience-skills` | An illustration as a cut-out with a solid blue offset shadow. **Huge** section headings — the word "Experience" is wider than the column. Timeline: coloured dates left, bold titles right. |
| `04-polaroids` | Photos in a **polaroid frame with a piece of tape** at the top, rotated a degree or two, with a handwritten-feeling caption. |
| `05-section-break` | Back to dark. A full-bleed halftone portrait behind a four-word statement, one word in blue. |
| `06-project-list` | Numbered rows — `02` left, `SPEECH / MODEL` right, on the same line, both in wide-tracked mono. Title below, huge. Corner-bracket frames, not rounded cards. |
| `07-contact-footer` | The contact block is a **paper card sitting on the dark ground**. Under it a spec table: `RESPONSE / 24–48 HOURS`, `WORK MODE / REMOTE`. Then numbered links with an arrow-out glyph. |
| `08-hero-desktop` | Same hero at 1440. The objects spread out; the headline stays the size of a hand. Nothing stretches to fill. |

## The DNA, and what each strand means for us

Eight things, present in every frame. These are the standard. The specific
guitars, ASCII thumbnails and audio player are not.

**1. Texture on every ground.** Grain over black, grain over paper, a faint
grid under both. Nothing is a flat hex fill.
*Us:* an inline SVG `feTurbulence` noise as a data-URI background layer, plus
a CSS-gradient grid. Zero external requests; the constraint holds.

**2. Two grounds, not one.** Dark ink and warm paper alternate. The page has
acts.
*Us:* every voice gets an ink band and a paper band. Trade and fitness already
open on a solid accent — push that to ink. Care and beauty stay paper-first
and close on ink. The contact block is *always* the paper-card-on-ink from
frame 07 — that is where the ask is made, and it is the most confident moment
on the reference.

**3. Three scales of type, far apart.** Display type the width of the column.
Body at a reading size. Labels tiny, mono, uppercase, tracked `.1em`–`.14em`.
*Us:* we have all three in system fonts — the display stacks in `VOICES`,
`ui-monospace/SFMono-Regular/Menlo` for labels. The gap between them is what
is missing: our eyebrow is 11.5px and our h1 tops out at 66px. The reference
runs closer to 9px against 90px. Widen the gap before touching anything else.

**4. The headline wears the accent.** "Ideas Into Systems" *is* the red. The
accent is not saved for buttons.
*Us:* h1 in `var(--accent)` on paper grounds; paper-coloured on ink grounds.
One accent, used with nerve, beats an accent used carefully.

**5. Physical objects.** Stickers with hard offset shadows. Tape. Polaroid
frames. Cut-outs with a paper edge. Rotation of one to three degrees on
anything that is "stuck on".
*Us:* their photos are the objects. The hero photo as a cut-out with an
offset solid shadow; the gallery as polaroids with tape; the eyebrow as a
sticker label. This is what a roofer's page has instead of a guitar.

**6. Numbered, paired labels.** `02` left, `SPEECH / MODEL` right, same
baseline. Sections count. Lists count.
*Us:* the service menu rows, the trust boxes, the review list — number them.
Category left, detail right.

**7. Corner brackets, not rounded cards.** Frames are drawn as four corner
marks or a single hairline. Rounded corners appear on exactly three things:
photos in a polaroid, the audio pill, and nothing else.
*Us:* `--radius` on everything is the tell of a template. Corners on buttons
and photos only; sections and cards get brackets or a hairline.

**8. Whitespace as a decision.** A section heading gets the whole fold to
itself. Then dense content. The rhythm is *huge → empty → dense*.
*Us:* section padding scales with the display size, not a fixed 64px.

## What does not transfer

- The objects themselves. A dentist in Sabre Springs does not get scattered
  headphones. She gets her own front door, treated like frame 04.
- ASCII-art thumbnails, the audio player, "TAP TO REVEAL". Portfolio theatre.
- Dark ground as the *default*. Right for trade, fitness, a barber. Wrong as
  the opening for a paediatric dentist. The *alternation* is the rule; which
  ground opens is the voice's call.
- The display typeface. Theirs is a licensed geometric; we ship system fonts
  only and will not add a request for one. Scale, texture and physicality
  carry more than the face does — but be honest that this is a ceiling.

## The constraints do not move

From `.claude/agents/designer.md`, restated because a reference this strong
tempts you to break them:

1. **Self-contained.** No web fonts, no CDN, no request of any kind. Grain is
   an inline SVG. Photos are data URIs.
2. **Phone first.** Judged at 390px, survives 320px, never scrolls sideways.
3. **Works with JavaScript off.** Nothing important hidden behind a reveal.
4. **Reduced motion removes motion, not content.**
5. **Nothing invented about the business.** Design is yours to invent —
   layouts, textures, labels, rhythm, decorative captions, the lot; be bold.
   *Facts* are not: reviews, hours, prices, services, licences, years, a
   caption that makes a claim. A polaroid of *their* shop, or no polaroid —
   and a heading is a claim about the photo under it: "Recent work" over a
   picture of the wall is an invented fact. Every photo is looked at and
   tagged (`kind`) before it can sit under that heading.

## How to check

```bash
./cc shot <slug>                 # phone folds + full page + desktop, into shots/<slug>/
./cc shot https://any.site       # the same for anything, the reference included
```

Then open `shots/<slug>/phone-01.png` next to `design/reference/01-hero-phone.png`
and answer honestly. A page is at the bar when the answer is yes at 390px
with the sound off, not when its CSS reads well.
