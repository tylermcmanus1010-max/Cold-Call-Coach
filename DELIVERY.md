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

Free, and it satisfies the HTTPS promise in your pitch:

- **Netlify Drop** — netlify.com/drop. Drag `index.html` onto the page. Live in
  seconds on a `something.netlify.app` URL, HTTPS included, free tier is plenty
  for a one-page local business site.
- **Cloudflare Pages** is the same idea if you prefer it.

Send them that URL first. They approve on the temporary URL, *then* you touch
their domain. Never the other way around.

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

Edit `business.json`, run `./cc build <slug>`, drag the new file to the host.
That is the whole update loop, and it takes minutes.

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
