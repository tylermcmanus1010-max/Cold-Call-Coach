# Cold Call Coach

Find a local business with a bad website. Rebuild it. Send it to the owner with a price.
Repeat.

No dependencies, no build step, no accounts. Node 18+ and a text editor.

---

## The loop

```bash
./cc new joes-auto        # 1. scaffold the folder
                          # 2. fill in business.json  (~10 min, see below)
./cc build joes-auto      # 3. get index.html + pitch.md
                          # 4. send the email in pitch.md, attach index.html
./cc sent joes-auto       # 5. mark it sent
./cc list                 #    see the whole pipeline
```

That's the whole thing. Everything below is detail on the ten minutes in step 2.

---

## 1. Find one

You're looking for a business that clearly makes money and clearly has no one
looking after its website. The tells, in order of how much they're worth to you:

- The site isn't mobile-friendly (pinch-to-zoom on your phone = they're losing most of their traffic)
- `http://` with no `s`
- A Facebook page instead of a website
- Copyright year of 2016 or a "Powered by" footer from a dead website builder
- 4.5★ with 200+ reviews but a site that looks like nobody's touched it

Where to look: Google Maps for a trade + neighborhood ("plumber North Park",
"auto repair Chula Vista"), then open each site **on your phone**. Yelp's category
pages work too. Businesses with lots of good reviews and a bad site are the best
targets — they already have demand, they're just leaking it.

Skip anything with a booking widget, a chat bubble, or a recent blog. Someone's
already being paid for that site and you're walking into a fight.

## 2. Fill in `business.json`

Open `clients/<slug>/business.json` and copy from their existing site, their
Google Business listing and their Yelp page. Real details only — the whole pitch
is that you did the work before asking for anything.

Every section is optional. Delete what you don't have and the page adapts —
no empty blocks, no lorem ipsum. What matters most:

| Field | Why |
|---|---|
| `headline` | The one line that goes at the top. Say what they do and where. |
| `services[].price` | "from $129" beats "call for pricing" every time. Their competitors hide it. |
| `reviews` | Copy their three best real reviews off Google/Yelp, with the reviewer's name as shown. |
| `highlights` | Years in business, review count, "same day" — the four boxes under the hero. |
| `phone` | Everything on the page points at it. |
| `theme.accent` | One hex color. Pull it from their sign, truck, or logo. |

Then the important part — **`audit`**. Go through their current site and set a
check to `true` for anything it already does right. Everything left `false`
becomes a bullet in the email. Be honest here; if you claim their site is broken
in a way it isn't, you lose the call in the first thirty seconds.

The twelve checks are in `tools/checks.js` — mobile, HTTPS, speed, tap-to-call,
hours, address, services/pricing, reviews, CTA, schema markup, meta tags, link previews.

## 3. Build and check it

```bash
./cc build joes-auto
```

Produces two files in the client folder:

- **`index.html`** — the whole site in one file. No external requests, so it works
  from a double-click, as an email attachment, off a USB stick, or on any host.
  ~15KB, loads instantly.
- **`pitch.md`** — the audit table, the email to send, the price, the day-3
  follow-up text, and the answer to "what's the catch".

**Open it on your actual phone before you send it.** That's the demo.

## 4. Send it

Attach `index.html`, paste the email from `pitch.md`. Subject line is already
written. Don't attach a proposal, don't attach a deck — the page is the pitch.

If you'd rather send a link than an attachment, drop `index.html` on any static
host (Netlify drop, GitHub Pages, Cloudflare Pages — all free), then put the URL
in `liveUrl` and rebuild; the email will reference it.

## 5. Track it

```bash
./cc sent joes-auto                  # stamps today's date
./cc status joes-auto replied        # new | sent | replied | won | dead
./cc list
```

```
BUSINESS                  STATUS    GAPS  QUOTE     SENT
example-bayview-plumbing  new         10  $750
```

`GAPS` is how many of the twelve checks their current site fails — it's also
roughly how strong your pitch is. Under 4, move on.

---

## Pricing

All of it lives in `config/pricing.json` — edit once, applies to every pitch.
Ships with $750 one-page, $1,500 with booking, $60/mo hosting and updates, and a
"don't like it, don't pay" guarantee. Set `"tier": "plus"` in a client's
`business.json` to quote the higher one.

Change the `from` block to your name, email and phone before you send anything.

## Layout

```
cc                       the CLI
config/pricing.json      your prices, your name, your guarantee
tools/render.js          business.json -> index.html
tools/pitch.js           business.json -> pitch.md
tools/checks.js          the 12 checks and how each one is worded in the email
tools/business.template.json
clients/<slug>/
  business.json          the only file you edit
  index.html             generated — send this
  pitch.md               generated — send the email in this
```

`clients/example-bayview-plumbing/` is a made-up business showing what a filled-in
file produces. Look at it once, then delete it.

## Changing the design

It's one file: `tools/render.js`. The CSS is at the top in a `<style>` block —
colors are CSS variables driven by `theme` in `business.json`, so most changes
are one hex value per client, not a code edit. `./cc build` with no slug rebuilds
every client at once, so a template change ships to all of them.
