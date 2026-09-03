# Using Polar for this business

Polar is a Chromium-based AI browser for macOS. It drives websites the way a
person does — clicking, typing, navigating — inside sessions you are already
signed into, and it can run workflows on a schedule.

## First, the mismatch

**Polar cannot make phone calls.** It automates a browser. So it does not
solve "I can't call while I'm at work" directly, and anything promising
otherwise is worth ignoring.

What it *can* do is work the channel that does function at 11am on a Tuesday:
**their own contact form**. That is what `./cc forms` and `./cc outreach` are
for. Polar is the hands; the queue is the brief.

The order of value for a desk job, highest first:

1. **Text messages.** You can send a text from your desk in ten seconds and
   nobody notices. Trades in particular would rather be texted than called.
   The queue gives you a prefilled one per lead. This needs no software at all.
2. **Contact forms.** Their published inbox, no address guessed, works any
   hour. This is where Polar earns its keep.
3. **5am and after 4pm calls.** Still the highest conversion by a distance.
   `./cc brief` orders the morning by who can actually answer.

## The rules, which apply to Polar exactly as they apply to you

- **One message per business, ever.** No reply is a reply. A second one is
  what turns outreach into spam.
- **Ten a day, not a hundred.** Every message names something true about that
  specific business. Volume is what breaks it.
- **A CAPTCHA means no.** It is the site asking not to be automated. The queue
  marks those; finish them by hand or skip them.
- **Never send to a lead flagged "the domain may not be theirs."** The queue
  already refuses to include them. On the phone you can correct a wrong URL
  mid-sentence; in writing it is permanent.
- **Read every message before it goes.** Not because the copy is bad, but
  because our data has been wrong about a URL six times in one week.

## What to actually tell Polar

Open `outreach/index.html` — the send queue — alongside it, then give it one
business at a time:

> Open <FORM URL>. Find the contact form. Fill it in with:
> name Tyler McManus, email tylermcmanus1010@gmail.com, phone 302-649-6600,
> and this exact message in the message box: <PASTE>.
> Do not change the wording. If the form has a CAPTCHA, stop and tell me
> instead of trying to complete it. When it is filled in, show me the form
> before submitting.

**"Show me before submitting" is the whole safety design.** Keep it there even
once you trust it, because the failure mode is not a bad submission — it is
twenty bad submissions under your own name before you notice.

For a scheduled run, the honest version is *preparation*, not sending: have it
open the next five forms and fill them, then leave them for you to check and
submit at lunch.

## What not to let it near

Agentic browsers act on what they read, and most of what this one reads is
untrusted pages written by strangers. A page can contain text aimed at the
agent rather than the human. So:

- **Do not sign it into your Gmail to do outreach.** Every piece of email this
  business sends runs through that one account. Two guessed addresses already
  hard-bounced on 30 August and one was retried after a permanent 550 — the
  downside there is not two lost emails, it is losing the ability to send at
  all. An agent looping on a send failure is exactly that risk, automated.
- **Do not give it anything that can spend money.** No card on file, no
  registrar account, no hosting billing.
- **Do not let it near a client's live site or DNS.** Those are other people's
  businesses. Changes there are made deliberately, by you, with their approval.

Reading is fine. Signing in as you, to something that matters, is not.

## Two jobs it is genuinely good at, that have nothing to do with sending

**Verifying a URL before you pitch.** Six wrong URLs in one week, every one
caught by opening the site on a phone. That check — "open this, does the page
name this business, is it a real site or a placeholder" — is a browser task,
it is dull, and it is the single highest-value thing in this pipeline. Have it
work down the leads flagged *open this first*.

**Filling in what a page scan cannot prove.** We refuse to claim hours,
address, services, reviews or a call-to-action, because a scan reads them
wrong. A browser agent looking at the rendered page can read them correctly.
That turns five unusable checks into real material — and material off their
own site is what took Pearl Cosmetic from 10/12 to 12/12.

Both of those make the calls you *do* make better, which is worth more than
another twenty messages.
