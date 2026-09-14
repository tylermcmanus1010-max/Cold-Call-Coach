# Agent Reach — finding leads where no API reaches

Agent Reach (github.com/Panniantong/agent-reach) is an installer that puts a
set of platform CLIs in front of an AI agent on **your Mac**. For this
business it is worth exactly one thing: **finding local businesses whose
only web presence is a Facebook page or an Instagram profile.** Those are
the "no website at all" leads — the easiest close in the playbook, and the
ones OpenStreetMap and Google Places cannot see.

It does not run here, and it does not run on GitHub Actions. The channels
that find leads drive your own logged-in Chrome through a browser
extension (OpenCLI), the same way Polar does. Everything it finds comes
into the pipeline through `./cc import` — see the README, section 10.

## What to use, what to leave alone

| Channel | Verdict | Why |
|---|---|---|
| **Facebook** (OpenCLI) | **Use** | Pages for trades and clinics with no site. Search by trade + town. |
| **Instagram** (OpenCLI) | **Use** | Salons, barbers, food — profiles with a phone and no link. |
| Web (Jina Reader) | Optional | Turns a URL into clean text. `research.js` already reads sites; this only helps on JavaScript-only pages. |
| Reddit | Skip | Needs your account cookies; the doc suggests a paid proxy to dodge Reddit's blocks. That is evasion. Not for this business. |
| Twitter/X | Skip | Cookie auth, account risk, and no local trades live there. |
| YouTube, GitHub, LinkedIn, Bilibili, XHS, podcasts | Skip | Nothing to do with a plumber in Poway. |
| Exa search | Maybe later | Paid web search API. Could answer "does this business have a site". Not now. |

## Rules, which are the same as POLAR.md's

- **A secondary account.** Agent Reach's own docs say so: platforms detect
  automation and restrict accounts, and a cookie is a full login. Make a
  second Facebook/Instagram login for this and never use your main one.
- **Read only.** It searches and reads pages. It never posts, messages,
  follows, likes or comments. Outreach is the phone, the text, the form.
- **No proxies, no CAPTCHA solving.** A block is the platform saying no.
- **Volume is what breaks it.** Twenty searches in an evening, not two
  hundred. This is a scout, not a scraper.
- **Never paste cookies or tokens into a chat with me.** They live on your
  Mac in `~/.agent-reach/`, nowhere else.
- **Nothing it reads is a fact until a person checks it.** A phone number
  off a Facebook page goes in as a lead to *call*, not as a claim on a
  page. `./cc import` writes nothing that is not a name, number, town and
  URL, and builds no page — audit first, build second.

## Setting it up, once, on the Mac

Give the agent on your Mac this, and approve the system install when it
asks — that is the safe default in their doc:

```
Safely check and install Agent Reach: https://raw.githubusercontent.com/Panniantong/agent-reach/main/docs/install.md
Only the facebook and instagram channels. Read-only use. Do not set up Reddit, Twitter or any proxy.
```

Then the one manual step Chrome insists on: add the OpenCLI extension
from the Chrome Web Store, sign the **secondary** account into
facebook.com and instagram.com in that Chrome, and run `opencli doctor`
until it says the extension is connected.

## The job to give it

One metro, the trades that buy, and the output in the exact shape
`./cc import` reads. Paste this to the agent on your Mac:

```
Use OpenCLI to find local businesses with no real website. Metro: Poway, Escondido, El Cajon and Santee, CA. Trades, in this order: plumber, electrician, HVAC, roofer, general contractor, auto repair, dentist, veterinarian, chiropractor.

For each trade and town run: opencli facebook search "<trade> <town>" -f yaml
Then for the businesses it returns, open the page and keep only the ones that are (a) an owner-run local business, not a chain, (b) with a phone number shown, and (c) with NO website link, or a link to a Facebook/Instagram/Yelp/Linktree page rather than their own domain.

Do not post, message, like, follow or comment on anything. Do not solve a CAPTCHA. Stop after 20 searches.

Write the result to ~/Desktop/leads-<today>.csv with exactly this header row:
name,phone,website,city,state,category,notes

website = their own domain if they have one, otherwise blank. notes = where you found it and the one thing you saw (e.g. "FB page, 340 followers, last post March, no site").
```

The same works for Instagram with `opencli instagram search "<trade> <town>" -f yaml`
and `opencli instagram profile <handle> -f yaml` — a profile with a phone
number in the bio and no link is the lead.

## Getting the list in

From the Mac, in this repo:

```bash
./cc import ~/Desktop/leads-2026-09-14.csv --dry-run   # see what would happen
./cc import ~/Desktop/leads-2026-09-14.csv             # scaffold them, unmeasured
```

Or, without a terminal: put the CSV at `leads/polar/leads-2026-09-14.csv`
with the GitHub app and commit it to `main`. `import.yml` imports it,
measures each lead in a real browser, decides what is at the URL, rebuilds
the dashboard and moves the file to `leads/polar/done/`. They are on the
caller's Up next tab by the next build, tagged *not measured yet* until
the audit has run. `leads/polar-template.csv` is the header row to copy.

Duplicates against the pipeline, toll-free numbers, anyone on the
do-not-contact list, and rows with nothing to reach them by are skipped
with the reason. A lead with no website at all is exactly what you want:
it is the strongest pitch there is, and the page is built only once they
say they are interested.
