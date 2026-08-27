# When they say yes

The five-minute version: get their content, put the page on free hosting, point
their domain at it **without touching their email**, get approval, get paid,
then hand over the login.

---

## 1. The yes call — collect this before you touch anything

- **Who owns the domain, and where is it registered?** GoDaddy, Namecheap,
  Network Solutions, their old web guy. This is the one thing that stalls jobs.
- **Do they have email on that domain?** `something@theirbusiness.com` means
  yes. Read the warning in step 3 before you change a single DNS record.
- Logo, and 5–10 photos of the shop, the team, the work.
- Anything on the page they want changed — services, wording, prices.
- The email address for enquiries, and where they want the form to go.
- Confirm the hours and the phone number out loud. Google is often wrong.

Send a short email after the call confirming price, what's included, and that
they own the site. For a $750 job that email *is* the contract.

## 2. Put it live

### First, prove it is actually ready

```bash
./cc host swinley-spa-services
```

This refuses to write anything while the page still has our guesses on it —
a placeholder phone number, prices the owner has not agreed to, an email at a
domain nobody owns. All of that is harmless in an attachment and none of it is
harmless live, where a wrong email swallows enquiries silently and a price we
invented is one they have to honour.

It wants four sign-offs in `business.json`, and it is worth getting them in
writing rather than a nod on the phone:

```json
"liveUrl": "https://theirdomain.com",
"status": "won",
"confirmed": { "prices": true, "email": true, "hours": true, "area": true }
```

Then it writes `sites/<slug>/`:

| File | What it does |
|---|---|
| `index.html` | the page |
| `_headers` | security headers, read by both Cloudflare Pages and Netlify |
| `robots.txt` | lets search engines in, points at the sitemap |
| `sitemap.xml` | the one URL, so Google indexes it without waiting to be found |

Setting `liveUrl` also puts a canonical link, an `og:url` and the schema URL on
the page. Without it Google has to guess which address is the real one.

### Then put the folder somewhere

- **Cloudflare Pages** — pages.cloudflare.com, Create → Upload assets, drag the
  `sites/<slug>` folder in. Live in about a minute on `something.pages.dev`,
  HTTPS included, free.
- **Netlify Drop** — netlify.com/drop does the same thing.

Send them that temporary URL first. They approve on it, *then* you touch a
domain. Never the other way around.

## 3. Point their domain — without killing their email

**This is the one that ends relationships.** If a business has email on their
domain and you move their nameservers, their email stops. Mid-job. They will
not care whose fault it is.

Two ways to connect a domain, and only one is safe by default:

| | What it does | Risk |
|---|---|---|
| **Change nameservers** to the host | Hands the whole domain over, MX records included | **Breaks their email** unless you recreate every record first |
| **Add A / CNAME records** at their existing registrar | Points only the website | Safe — MX records stay where they are |

**Use the second one.** Log into their registrar, add the records the host gives
you, change nothing else. Their email keeps working because you never touched
the MX records.

### The exception: a domain they just bought

That whole warning is about protecting email that already exists. A brand new
domain has no email, no records and nothing to break — so for a first-time
business, putting it fully on Cloudflare is the *better* setup, not the risky
one:

- Cloudflare Registrar sells domains at cost, about $10 a year, and the
  nameservers are already theirs when you buy it there
- Adding it to a Pages project is then two clicks, with the certificate handled
- **Cloudflare Email Routing is free**, and forwards `them@theirdomain.com`
  straight to the Gmail they already read. That is how a one-man business gets
  an email on their own domain without paying for a mailbox.

Know which situation you are in before you touch anything. Existing business
with existing email: records only, never nameservers. Fresh domain: Cloudflare
end to end.

### Whose name the domain goes in

**Theirs.** They register it, on their own card, in their own account, and they
add you to it. A domain in your name is a hostage, they will eventually notice,
and it costs you the referral. If they want you to buy it for them, buy it and
transfer it the day they pay.

If you must change nameservers, screenshot every existing DNS record first —
especially MX and TXT — and recreate them at the new host before switching.

Then wait. DNS takes anywhere from ten minutes to a few hours. Don't panic, and
don't tell the client something is broken while it propagates.

## 4. Getting paid

Your pitch says "if you don't like it, you don't pay." So the order is:

1. They approve the page on the temporary URL
2. Domain points at it, HTTPS confirmed working
3. **Then** invoice

Stripe Invoicing or Square both take cards and take minutes to set up. Plenty of
small businesses would rather write a check — take it, it clears fine.

Mark it: `./cc status <slug> won`

## 5. The two rounds of changes

Two rounds means two batches, not two individual tweaks. Say so kindly and
early: *"send me everything you want changed in one go and I'll do it all at
once."* Otherwise you get eleven emails over three weeks for one job.

Edit `business.json`, run `./cc host <slug>`, drag `sites/<slug>` back to the
host. That is the whole update loop, and it takes minutes.

## 6. The $60 a month

Hosting is free, so this is nearly all margin — which means it has to be worth
something to them. What it covers:

- Hosting, SSL renewal, backups
- Unlimited small text, hours and price changes
- You noticing before they do when something breaks

Be clear what it is not: a new page, a booking system or a redesign is new work.

Bill it monthly through Stripe. Skip it entirely for anyone who hesitates — a
$750 job you actually get paid for beats a $60 subscription argument.

## 7. If they ever leave

They own the site. Hand over the HTML file and point their domain wherever they
ask. Do it quickly and without friction — in a town this size the referral is
worth more than the retainer.
