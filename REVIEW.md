# Where the business stands — 10 September 2026

A review of McManus Web Co. seventeen days in, written for Tyler and for
whoever is dialling off the dashboard. Every number here comes from
`clients/`, `outreach/sent-log.jsonl` and the git history, not from memory.
The earnings section is a model, not a forecast — there has not been a sale
yet, and until there is, every conversion number is borrowed.

---

## The numbers

| | |
|---|---|
| Pages built | **87** |
| Businesses actually contacted | **39** |
| Dials | **33** (7 reached a human, 7 went to voicemail) |
| Emails sent this week | **10** (Sep 8 — every one lacked real reviews) |
| Replies | **1** (RT Roofing — warm, but his site is fine; not a rebuild) |
| Sales | **0** · Revenue **$0** |
| Dead | **55 of 87** — 27 because their site was actually fine |
| Pages with real hours / real reviews | **9 / 2** of 87 |
| Leads researched (`siteKind` set) | 34 of 87 |
| Commits | 97 in 17 days · 40 of them on a single day |

The seven humans reached on the phone: two agreed to a callback (**neither
was called back**), one gave an email (Impression Dental), two hung up, one
was a gatekeeper guessing, one said no. One email from seven conversations
is the real number to improve first.

**Lead mix:** bakery 9 · hairdresser 8 · dentist 6 · florist 5 · fitness 5 ·
insurance 4 · dental 4 … plumber 2. `prospector.md` says trades and clinics
buy and salons do not. The scout *targets* trades (`craft=plumber`,
`craft=roofer`…), but OpenStreetMap barely maps trades in the US and maps
salons and bakeries densely — so the source delivers the wrong verticals no
matter how the config is written. The Google Places source that would fix
this is already in `research.js` and `scout.js`, gated on
`GOOGLE_MAPS_API_KEY`, which has never been set.

**Geography:** the lead files are national (Seattle, Milwaukee, Nashville,
Delaware) and the number on the pitch is a 302 (Delaware) area code, dialled
from San Diego. Both hurt pickup rate.

---

## Where it leaks, most expensive first

1. **Follow-through.** Valerio's (callback 28 Aug) and Le Parfait (callback
   31 Aug) were the two warmest phone leads and both were dropped, while El
   Cajon Family Dental was dialled six times. The dashboard's *Owed* strip
   now surfaces this; someone has to own it every morning.
2. **Building before qualifying.** A page is built for every scaffolded lead;
   half of them turn out to have a site that is fine. Audit first, build only
   what scores ≥5/7 failing. That halves the design and research load and,
   more importantly, halves the wasted calls.
3. **Thin pages.** 85 of 87 fail the campaign's own send gate. This is not a
   design problem — `render.js` is fine — it is a data problem, and one API
   key fixes it.
4. **Wrong verticals, wrong geography.** See above. One metro, a local
   number, trades and clinics.
5. **Email deliverability.** Five hard bounces in roughly thirty lifetime
   sends from a personal Gmail. Another batch like Sep 8 and the account gets
   throttled. `POLAR.md` already says so.
6. **Engineering ahead of selling.** 97 commits, 33 dials. The tooling is
   good now. It needs to be used.
7. **The trading work.** The `analyst` agent, `market.yml` and `trading/`
   have nothing to do with a $0-revenue web business. Park them until there
   is a first sale.

---

## What to expect to earn

Per 100 dials, using this business's own numbers where they exist and
industry-typical ones where they do not:

- ~25 reach a human (measured: 21%)
- ~8–10 agree to look at the page (measured: 1 in 7 — but that is with
  callbacks being dropped; "already built, costs nothing, don't like it
  don't pay" should do far better once they are actually made)
- ~1–2 buy at $750 + $60/month (a free-built, no-risk offer converts
  10–20% of the people who look)

An employee doing **40 dials a day, five days a week — 200 a week** — is
**2–4 sales a week, $1,500–3,000 a week in builds**, plus $60/month per
client stacking underneath.

| Horizon | Realistic if the fixes below land |
|---|---|
| Month 1 | 2–5 sales · $1.5–3.75k (pool is thin, callbacks need rebuilding) |
| Month 3 | ~$6–12k/month builds · ~$500–1,000/month recurring |
| Month 6 | ~$36–72k cumulative builds · $1.5–3k/month care base |

**The constraint is callable leads, not pages or demand.** 200 dials a week
needs 800+ fresh, qualified, right-vertical leads a month. There are 81
callable in the pipeline and 94 with a phone in the lead files. The
prospector has to produce ten times more, or the caller runs dry in a week.

**One offer to test:** $0 up front, $99/month — site, hosting, updates,
cancel any time. A far easier cold close, and fifty of them is $5,000 a
month recurring. Run it against the $750 offer on twenty leads each and let
the numbers decide.

**The single most valuable thing this month is one closed deal.** It gives
the real close rate, a testimonial, and a live site to point at. Seth Wright
(Swinley Spa, revisit 15 Oct) is the closest.

---

## Do this, in order

1. **Set `GOOGLE_MAPS_API_KEY` as a repository secret**, then run
   *Research a business* with a blank slug. Real hours, reviews, ratings,
   phone, website — and the right verticals — flow into every page. Fixes
   leaks 3 and 4 in ten minutes. Google's Places pricing moved to free
   monthly call tiers per SKU in 2025; at this volume it is free to a few
   tens of dollars a month — check the current SKU table before relying on
   a number.
2. **Pick one metro. Get a local number** (Google Voice is free) for
   whoever is calling.
3. **40 dials a day, in the windows the dashboard shows, every one logged.**
   The goal of a call is an email or permission to text — not a sale.
4. **This week: call Valerio's, Le Parfait and Seth.** Those are the three
   warmest names in the building.
5. **Scout: audit first, build second.** No page for a site scoring ≥3/7.
6. **Pause `market.yml` and the analyst routine.**
7. **Merge the Seth fix** (below) so he is on the caller's list tomorrow.

---

## The agents, ten times better

**Prospector.** Today: 60 scaffolds a run, half for sites that are fine, in
verticals that do not buy. Ten times better: switch the source to Google
Places (the key above), search per category per metro, dedupe against the
pipeline, and add **signal-based leads** — expired SSL, parked domains,
copyright ≤2018, new business registrations (state bulk lists are public
downloads even where the search UI blocks bots). Those are the easiest
closes there are. Target: 200 qualified, trades-and-clinics, single-metro
leads a run, landing on the dashboard with a call window already attached.

**Designer.** The weekly `render.js` pass is fine. Pages are not losing on
design; they are losing on content. Ten times better: own the content
pipeline — research, photo harvest and kind-tagging run on every new lead
automatically, so pages pass `./cc check` on arrival. Then build the one
sales asset that does not exist yet: a **before/after image** (their site
beside ours, phone width, one picture) that travels with every text and
email. That is the pitch. Last, put the proof on the page itself — the
seven checks, theirs against ours.

**Analyst.** The paper-trading analyst should be switched off. The version
this business needs is a **sales analyst**: dials → reached → viewed →
replied → won, cut by vertical, metro, hour of day and opener line. The
tap-to-log buttons now produce exactly that data at volume. Once a week:
"trades at 7am convert three times salons at 2pm — stop calling salons."
That turns the caller's day into a learning loop instead of a log.

**Two agents that do not exist yet and should:**

- **Closer.** Owns the *Owed* strip. Every morning: what is due, a drafted
  text or email for each, and a nag until it is logged. Would have caught
  both dropped callbacks.
- **Fulfilment.** When a status flips to `won`, runs `DELIVERY.md`: content
  form, hosting, DNS checklist, invoice. It is all manual today, and the
  first sale will expose that.

---

## On using Polar instead of Google Maps

Tyler's idea: drive Google Maps in Polar (the agentic browser, see
`POLAR.md`) to gather hours, reviews and leads, rather than setting up the
Places API.

**"Instead of" is the wrong frame. It is both, for different jobs.**

The Places API answers *structured* questions — hours, rating, review count,
review text with the author's name, website, phone — for thousands of
businesses a month, in milliseconds, for roughly nothing, with the source
attribution the never-invent-a-fact rules are built on. `research.js`
already knows how to read it. Polar is a browser with hands: a minute or so
per business, real token cost per page, and driving Google Maps' interface
at volume is exactly the bot-defended pattern that already got the CSLB
scraper rejected this week — with Google's terms forbidding it on top. At
800 leads a month it is not viable. At ten a day it is fine.

Where Polar genuinely beats an API, use it there:

1. **"Is this really their site?"** — six wrong URLs in one week, every one
   caught by a human looking. `POLAR.md` already calls this the single
   highest-value dull task in the pipeline. Work down every card flagged
   *open their site first*.
2. **Reading their own site where a scan fails** — hours, services, reviews
   behind tabs or in images. This is what took Pearl Cosmetic from 10/12
   to 12/12.
3. **Yelp**, where there is no usable API and the reviews are richer for
   salons and restaurants.
4. **Contact forms** — the only channel for the ~80% of leads with no
   email. Its existing job. Ten a day, "show me before submitting."
5. **Bot-gated public records** — the CSLB licence check that scripts
   cannot pass. A human at the checkpoint solving the CAPTCHA turns
   "declined" into "ten a day."

Two rules from `POLAR.md` that stand regardless: everything Polar reads is
untrusted text written by strangers, so it never signs into Gmail and never
touches anything that spends money or changes a live site; and a CAPTCHA
means no — it is the site asking not to be automated.

**Concrete next step:** a *Polar queue* tab on the dashboard. Every card
flagged *open their site first* or *page still needs: hours / reviews*
becomes a task with a paste-ready prompt. That turns the idea into a daily
loop for the employee, at exactly the volume Polar is good at.

---

## Since this review was written

- `swinley-spa-services` carried status `spec` — set back when the page
  still held guessed prices — which hid Seth from both the call sheet and
  the dashboard. Corrected to `replied`. He is now on the Contacted tab.
