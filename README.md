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

## 3. Research first — `./cc research`

```bash
./cc research pearl-cosmetic-dds --apply     # one client
./cc research --all --apply                  # every open client
./cc research --all --apply --no-crawl       # fast pass: verdicts + Google, no nine-page read
```

**Do this before you write a word of copy.** Every page built from guesses is a
page of guesses — and the three gaps every pitch flags (hours, services,
reviews) are the three things most small-business sites never put in
scrapeable text. So this asks four sources, and each is allowed to fail
without taking the others down:

| | |
|---|---|
| **siteKind** | What is actually at their URL, decided *before* anything is scraped: `own`, `parked`, `dead`, `challenge`, `platform`, `notTheirs`, `unreachable`, `none`. A parked page's description is the parking company's. A bot-challenge page's faults are the CAPTCHA's. `dead` means the domain is gone or the page 404s on the server's word; a failed connection is `unreachable` — our network as often as theirs — and is retried next run. Nothing downstream reads a page this says not to. |
| **JSON-LD** | The site's own schema.org block — hours, price range, socials — structured, for free. |
| **Google** | Place Details: real hours, up to five reviews with names, owner-uploaded photos, the business's own description. Needs `GOOGLE_MAPS_API_KEY`. Skipped, loudly, without it. |
| **crawl** | The nine-page read of their own site: `quotes`, `hours`, `people`, `prices`, `emails`, `phones`, `social`, `headings` — where their real service list lives. |

All of it lands raw in `clients/<slug>/harvest.json`. **`--apply` writes only
the structured, attributed parts into `business.json`**, and only where the
field is empty or a placeholder: `siteKind`, the Google place (id, rating,
count, maps link), hours, up to three four-or-five-star Google reviews with
names, and photos through the same dedup and embed as `./cc photo`, untagged
until someone looks. Services and the headline are never written — those
need a person to read the harvest. Nothing is invented; everything written
names its source.

**The campaign will not send a page that has not been through this.** No
`siteKind`, no real hours, or no real reviews means "research it", not "send
anyway" — the ten sent on 8 Sep all lacked reviews, and that is the bar the
README has always stated.

Egress is blocked on most machines, so run it where it works: Actions tab →
**Research a business** → Run workflow (blank slug = every open client). Add
your Google key as the repository secret `GOOGLE_MAPS_API_KEY` to fill the
hours and reviews; without it you still get `siteKind`, the site's own
structured data, and the crawl.

`./cc harvest <slug>` is still there — it is the crawl on its own.

## 4. Fill in the sales copy

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

`./cc build` needs a `name`. If there's no `tagline` it derives a plain one from
category and city so a vetted lead is never uncallable over one missing line —
but it tells you which pages got the placeholder, and those are worth a real
line before you send them.

Every other section is optional — delete what you don't have and the page adapts.
No empty blocks, no lorem ipsum.

### The service menu is the whole page

Every service becomes a row people can tap. Selected rows add up in a bar at the
bottom — count, total, and how long the visit runs — and the button texts or
emails that selection to the business as a booking request. That is what Vagaro,
Booksy and Bukkii sell for a monthly fee, and it is the reason their sites beat a
grid of cards.

```json
"services": [
  { "group": "Drains & sewer", "name": "Drain cleaning", "desc": "Kitchen, bath or laundry line.",
    "price": "$129", "duration": "60 min" }
]
```

`group` sorts rows under a heading. `price` and `duration` are optional and must
only ever be a number the business actually published — never one you assumed.
Without them the rows still select and still send; the bar just says "3 services"
instead of a total. Most businesses will not give you prices on the first call,
and the page works fine that way.

If they already use a booking platform, put its link in `booking.url` and the
button sends people there instead.

## Photos, for businesses whose work is the product

```bash
./cc photo <slug> photo1.jpg photo2.jpg
```

Resized to 1400px and embedded as data URIs, so the page still opens with no
internet and still arrives as one file. A 4MB phone photo lands around 400KB.

Each photo also carries a **`kind`** — `work`, `place`, `team`, `product` or
`other` — and the page places it by that. Only `work` (a finished cut, a cake,
a re-roofed house, a client in the chair) may sit under "Recent work"; the
storefront and the interior go under "Around <name>"; `other` (stock, once
someone has looked) is kept but never shown. A photo with no `kind`
has not been looked at yet and never sits under "Recent work". `./cc shot
<slug>` writes every photo to `shots/<slug>/photos/` so you can look; the
harvest guesses from the site's own alt text and headings where it can.

This matters more than it sounds. A nail salon, a bakery or a barber is selling
something visual, and a text-only page cannot compete with a booking platform
that has a gallery — Revive Lash & Nail is on Bukkii with a photo grid, a priced
menu and per-technician booking, and their page beats anything we would send.

**Where a one-page rebuild actually wins:** trades, contractors, dental and
professional services. There the site is a brochure — who you are, what you are
licensed for, how to reach you — and being fast, secure and readable on a phone
is the whole job. Helix Mechanical's licence classes did more work than any
photograph would have.

## 5. Check our own page before we sell an audit

```bash
./cc check                 # runs the same 12 checks against the pages WE built
```

We pitch a twelve-point audit. Shipping a page that fails it is indefensible,
and an owner will notice — those are the exact things we just told him mattered.

A page needs **hours and reviews** before it goes out. Both come off their Google
listing and take a minute to add. Pricing is optional; plenty of trades and
practices do not publish it.

## 6. Build and check it

```bash
./cc build joes-auto
```

- **`index.html`** — the whole site in one file. No external requests, so it works
  from a double-click, as an email attachment, off a USB stick, or on any host.
  ~15KB, loads instantly.
- **`pitch.md`** — the audit table, the email to send, the price, the day-3
  follow-up text, and the answer to "what's the catch".

**Open it on your actual phone before you send it.** That's the demo.

## 7. Send it

Attach `index.html`, paste the email from `pitch.md`. Subject line is already
written. Don't attach a proposal, don't attach a deck — the page is the pitch.

To send a link instead, drop `index.html` on any static host (Netlify drop, GitHub
Pages, Cloudflare Pages — all free), put the URL in `liveUrl`, and rebuild.

## 8. Track it

```bash
./cc sent joes-auto                  # stamps today's date
./cc status joes-auto replied        # new | sent | replied | won | dead
./cc list
./cc sheet                           # rebuild the call sheet dashboard
```

`./cc sheet` writes `call-sheet.html` from `clients/` — every lead with its
number, phone script, email text and page file, sorted into who to call now, who
owes you a reply, and who is dead. It is the same file that gets published as the
dashboard, and tapping its buttons writes back to `clients/`, so the two never
disagree.

## 9. The morning dashboard

```bash
./cc dashboard                       # dashboard/index.html — two tabs
./cc dashboard --limit 30 --offline  # fewer on "Up next"; skip the is-it-live checks
```

One page, rebuilt and committed every morning at 6:30 Pacific by
`dashboard.yml`, so the phone never shows yesterday's numbers:

| Tab | What is on it |
|---|---|
| **Contacted** | Every business we have actually emailed, called or texted — number, email, the Gmail thread, our page (and whether it is really live), their site, what came back, the last note. Anything owed (a callback they asked for, three days of silence after an email, Seth's revisit date) sits at the top. |
| **Up next** | The 25–50 we have *not* reached, pages already built first, then the board's order. Each card says the one provable flaw, whether they are answering the phone right now in their own time zone, and what the page still needs before `./cc campaign` would send it. |

"Contacted" means a real attempt left the building: a line in
`outreach/sent-log.jsonl`, `./cc tried`, a bounce, a booked callback, or a
name on the suppression list. Nothing on the page is a new source of truth —
it reads `clients/`, `leads/`, the send log and `config/suppression.json`,
and reuses `board.js`, `campaign.js` and `brief.js` for every judgement.

**Seeing it on your phone.** The dashboard lists every prospect, so it is
exactly what `tools/publish.js` keeps off the public site. It is served
anyway, at `https://<cloudflarePagesDomain>/dash/`, but only through
`worker.js`, which 404s unless the request carries `DASH_KEY`. Set that
secret once in the Worker's settings (Variables and Secrets), then open
`/dash/?key=<the key>` once — a cookie keeps it open after that. With no
secret set, `/dash/` is a 404, not a page.

**Tap-to-log — for you or someone calling on your behalf.** Every card has
buttons: No answer, Sent, Replied, Won, Not interested, Callback…, Note….
Each tap writes straight to `clients/<slug>/business.json` through the
GitHub API — real the moment it's tapped, the same fields `./cc tried` and
`./cc status` write, so a tap and a terminal command never disagree. The
card updates itself in place; it does not jump to the other tab until the
next 6:30am rebuild reads the change, so a just-logged card in "Up next"
says so rather than pretending to have moved.

This needs a second secret, `GH_TOKEN`: a **fine-grained** personal access
token scoped to **only this repository**, with **Contents: Read and write**
permission and nothing else. Create it at GitHub → Settings → Developer
settings → Fine-grained tokens, then set it with
`npx wrangler secret put GH_TOKEN` (run that yourself — don't paste the
token into chat). Without `GH_TOKEN`, `/dash/` still works for reading;
the buttons just answer "not set up yet" instead of saving.

Anyone with the `/dash/?key=` link can log calls under this scheme — there
is no per-caller identity yet. Fine for one trusted employee; if you add
more than one, say so and it's worth giving each their own key so you can
tell who logged what and revoke one without touching the others.

---

## Making the call

`CALL.md` is the script. The goal of the call is to get an email address, not to
sell a website — which makes it a 45-second call that is hard to lose.

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
