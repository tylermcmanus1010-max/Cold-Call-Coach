# Cold Call Coach

Find local businesses with bad websites. Rebuild them. Send each owner the page
with a price attached. Repeat.

No dependencies, no build step, no accounts. Node 18+ and a text editor.

---

## The loop

```bash
./cc scout --make 10       # 1. pull every local business, audit every website,
                           #    rank them, scaffold the best 10 as clients
                           # 2. write headline + services + reviews (~5 min each)
./cc build joes-auto       # 3. get index.html + pitch.md
                           # 4. send the email in pitch.md, attach index.html
./cc sent joes-auto        # 5. mark it sent
./cc list                  #    see the whole pipeline
```

Step 1 is the one that used to eat your day. It's now one command.

---

## 1. `./cc scout` — build the lead list

Pulls every local business in the area, fetches each one's website, runs 12 checks
on it automatically, and ranks them by how much the bad site is costing them.

```bash
./cc scout                 # default: OpenStreetMap, free, no API key
./cc scout --limit 100     # audit the first 100 only (do this first)
./cc scout --make 10       # also scaffold the top 10 into clients/
```

```
   #  BUSINESS                 GAPS  ★ / REVIEWS   CURRENT SITE
  ─────────────────────────────────────────────────────────────────
   1  Offline Roofing Co         12  4.7 / 312     NO WEBSITE
   2  Dead Domain Landscaping    12  4.4 / 88      parked or placeholder page
   3  Joe's Auto Repair          10  4.9 / 204     © 2016, WordPress
```

Full results land in `leads/leads.csv` — open it in a spreadsheet and work down
the list. `leads/leads.json` has the raw audit for every business.

Ranking favors the leads worth your time: no website at all, a dead or parked
domain, no mobile support, an abandoned copyright year — weighted up by review
count, because a shop with 400 reviews and no mobile site is worth ten with 20.

### Sources

| | |
|---|---|
| `--source osm` | **Default.** OpenStreetMap via Overpass. Free, no key, no signup. Gives name, phone, address, category, and often the website. |
| `--source places` | Google Places. Adds **star rating and review count**, which is the filter you actually want. Needs `GOOGLE_MAPS_API_KEY` set. Costs a few dollars per full run and Google gives new accounts a monthly credit that covers it. |
| `--source file --file leads/urls.txt` | A list you gathered yourself. One per line, `Business Name,https://theirsite.com` or just the URL. |

Start with the default. Add a Places key when you want to filter by review count —
that's the single biggest quality upgrade to the list, because reviews prove they
already have demand they're leaking.

**One honest caveat on OSM:** a missing website in OpenStreetMap can mean "no
website" or just "nobody mapped it yet." Those rows are marked
`no website listed - verify` — spend the 30 seconds to check before you call.
Google Places doesn't have this problem.

### Running it from a phone

`Actions` tab → `Scout leads` → `Run workflow`. It runs on GitHub's servers, so
you need no terminal and no laptop. The ranked list appears in the run summary
(readable on a phone), the full CSV is attached to the run as a download, and
`make` will scaffold the top N as clients and commit them back.

The workflow file has to be on the default branch before the Run workflow button
appears — that's a GitHub rule, not a setting.

For `--source places` from Actions, add your key as a repository secret named
`GOOGLE_MAPS_API_KEY` (Settings → Secrets and variables → Actions).

### Retargeting

Everything about *where* and *what* lives in `config/scout.json` — the bounding
box, the neighborhood centers, which trades to include, and the filters
(`minReviews`, `minRating`, `minGaps`). Change the bbox and you're prospecting a
different city.

## 2. `./cc audit <url>` — check one site

```bash
./cc audit joesautorepair.com
```

Prints the 12 checks with pass/fail and tells you whether it's worth a rebuild.
Use it when someone gives you a referral and you want to know in 5 seconds
whether there's a job in it.

The checks: mobile, HTTPS, speed, tap-to-call, hours, address, services/pricing,
reviews, call-to-action, schema markup, meta tags, link previews. They live in
`tools/checks.js` along with the exact wording each one gets in the pitch email.

## 3. Fill in the sales copy

Scout pre-fills `business.json` with everything it could find — name, phone,
address, category, current site, and the full audit. What it deliberately leaves
blank is the part that sells:

| Field | Why |
|---|---|
| `headline` | The one line at the top. Say what they do and where. |
| `services[].price` | "from $129" beats "call for pricing" every time. Their competitors hide it. |
| `reviews` | Copy their three best real reviews off Google/Yelp, with the reviewer's name as shown. |
| `highlights` | Years in business, review count, "same day" — the four boxes under the hero. |
| `theme.accent` | One hex color. Pull it from their sign, truck, or logo. |

`./cc build` refuses to run until you've written a headline and tagline. That's on
purpose.

Every other section is optional — delete what you don't have and the page adapts.
No empty blocks, no lorem ipsum.

## 4. Build and check it

```bash
./cc build joes-auto
```

- **`index.html`** — the whole site in one file. No external requests, so it works
  from a double-click, as an email attachment, off a USB stick, or on any host.
  ~15KB, loads instantly.
- **`pitch.md`** — the audit table, the email to send, the price, the day-3
  follow-up text, and the answer to "what's the catch".

**Open it on your actual phone before you send it.** That's the demo.

## 5. Send it

Attach `index.html`, paste the email from `pitch.md`. Subject line is already
written. Don't attach a proposal, don't attach a deck — the page is the pitch.

To send a link instead, drop `index.html` on any static host (Netlify drop, GitHub
Pages, Cloudflare Pages — all free), put the URL in `liveUrl`, and rebuild.

## 6. Track it

```bash
./cc sent joes-auto                  # stamps today's date
./cc status joes-auto replied        # new | sent | replied | won | dead
./cc list
```

---

## When they say yes

`DELIVERY.md` covers the other half: putting the page live on free hosting,
pointing their domain **without breaking their email** (the one mistake that
ends a job on day one), getting paid, and what the monthly fee actually covers.

## Pricing

All of it lives in `config/pricing.json` — edit once, applies to every pitch.
Ships with $750 one-page, $1,500 with booking, $60/mo hosting and updates, and a
"don't like it, don't pay" guarantee. Set `"tier": "plus"` in a client's
`business.json` to quote the higher one.

**Change the `from` block to your name, email and phone before you send anything.**

## Layout

```
cc                       the CLI
config/scout.json        where to prospect, which trades, which filters
config/pricing.json      your prices, your name, your guarantee
tools/scout.js           pull businesses -> audit each -> rank -> leads.csv
tools/audit.js           fetch a site and score it against the 12 checks
tools/checks.js          the 12 checks and how each is worded in the email
tools/render.js          business.json -> index.html
tools/pitch.js           business.json -> pitch.md
leads/leads.csv          generated — your call list
clients/<slug>/
  business.json          the only file you edit
  index.html             generated — send this
  pitch.md               generated — send the email in this
```

`clients/example-bayview-plumbing/` is a made-up business showing what a filled-in
file produces. Look at it once, then delete it.

## Changing the design

It's one file: `tools/render.js`. The CSS is at the top in a `<style>` block —
colors are CSS variables driven by `theme` in `business.json`, so most changes are
one hex value per client, not a code edit. `./cc build` with no slug rebuilds every
client, so a template change ships to all of them at once.
