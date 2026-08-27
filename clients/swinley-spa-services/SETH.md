# Seth Wright — Swinley Spa Services

He already wants to buy. This is not a cold call, so do not pitch him like one.
Do not tell him what is wrong with his website — he does not have one. Show him
the thing, price it, and ask for what you need.

**402-201-5518** · Omaha metro · owner and only technician

---

## The timing, which is the strongest thing you have

It is late August. **Pool closing season in Nebraska runs September into
October**, and closing is one of his two biggest jobs of the year at $265 a
pool. If the site is live in five business days he has the whole window with a
page that takes bookings.

Say this. It is true, it is specific, and it is the reason to do it now rather
than in spring.

---

## What to send

Three files, all attached in one email:

| File | What it is |
|---|---|
| `swinley-spa-services.html` | the site, with his own logo |
| `swinley-spa-services-refreshed.html` | the same site, with the redrawn logo |
| `swinley-logo-refresh.html` | the two logos side by side, and why |

The email is in `email.txt` — paste it as is. It is written for him, not the
cold-call template.

---

## On the phone

> Seth — I've got it done. I'm sending you three files, open them on your phone.
>
> Two of them are the same website, the only difference is the logo. One uses
> yours as it is, the other uses a version I redrew so it's sharp on a van or a
> shirt. Third file shows you both and what changed. You pick.
>
> The bit I want you to try: scroll to the services and tap a few. Tap a weekly
> hot tub plan and a pool closing. See the bar at the bottom add them up? That
> texts you the whole request in one go. That's what Vagaro charges people
> monthly for. Yours is built in.
>
> It's $750 to put it on your own domain, live in five business days. $60 a
> month after that if you want me hosting it and making changes — cancel any
> time. Logo files are yours either way.
>
> One thing on timing. Closing season starts in a few weeks. If we go now you've
> got a page taking bookings for the whole run of it.
>
> Four things I need off you: your email, your say-so on every price — I put
> normal Omaha rates in so the page worked, they're mine not yours — three
> reviews from customers with their real names, and your exact town.
>
> And go and check swinleyspaservices.com is free. Do that today.

---

## The money

| | |
|---|---|
| Build | **$750** — live on his domain in 5 business days |
| Hosting and changes | **$60/month** — SSL, backups, unlimited text and price edits, cancel any time |
| Logo files | **included** |
| Guarantee | Doesn't like it, doesn't pay. Keeps the page either way. |

The logo is real design work and you could charge $150–250 for it. Recommend
you don't, on this one. He's your first paying client, the work is already
done, and throwing it in is what makes $750 feel like a decision he doesn't
have to think about.

---

## If he pushes back

**"That's more than I thought."**
Booksy or Vagaro is $30–90 a month on its own, and that's just the booking. The
$60 covers hosting, the certificate, backups and any change he wants made. And
he can cancel it.

**"Can you do it cheaper?"**
Don't cut the $750 — that is the work. Offer instead: $750 flat and he hosts it
himself. He gets the file, it runs anywhere, and he pays nothing monthly. You
lose the recurring but you keep the price and the relationship. Say plainly that
he'll be on his own for changes.

**"Let me think about it."**
Fine — the page is his either way, that's the deal. Only push on one thing: get
the domain today, before someone else has it. That costs him about $12 and
commits him to nothing.

---

## Before it goes live

- [ ] His email address, for the site
- [ ] Every price confirmed by him — **the ones on there now are mine, not his**
- [ ] Three real reviews with real names. Nothing invented, and this is the only
      real gap left on the page.
- [ ] His exact town — the service area currently reads Omaha metro
- [ ] Domain registered
- [ ] Wordmark converted to outlines, if he takes the redrawn logo, before
      anything gets printed
- [ ] Email working at the domain **before** the site points at it
- [ ] DNS — see the hosting run below. The "never move their nameservers" rule
      in `DELIVERY.md` is about businesses with existing email. Seth has no
      domain yet, so it does not apply to him.

---

## When he says yes — the hosting run

`./cc host swinley-spa-services` will refuse until all of this is true. That is
deliberate: everything on the page that is still a guess of mine gets caught
before it goes in front of his customers.

### Order of operations

1. **He registers swinleyspaservices.com himself**, on his own card. Cloudflare
   Registrar, about $10 a year, and it lands on Cloudflare nameservers ready to
   go. In his name, not yours — get added to the account instead.
2. **Set up the email before the site.** `seth@swinleyspaservices.com` is on the
   page and does not exist yet. Cloudflare Email Routing is free and forwards it
   to whatever he reads now. Do this first — an enquiry that bounces is a job he
   never hears about, and he never finds out why.
3. **Fill in what he confirms** in `business.json`: every price, the email, the
   hours, the towns. Then `"status": "won"` and
   `"liveUrl": "https://swinleyspaservices.com"`.
4. `./cc host swinley-spa-services` → drag `sites/swinley-spa-services` onto
   Cloudflare Pages. He approves on the `pages.dev` URL.
5. **Only then** attach the domain, in the Pages project's Custom Domains tab.
   His domain is new, so there is no email to break — the nameserver warning in
   `DELIVERY.md` is about businesses with an existing domain, not him.
6. Confirm HTTPS is live, then invoice.

### The freeze-season point, if he stalls

He does not need the whole site to benefit. If he registers the domain and sets
up email forwarding this week, he has a professional address on his van and his
quotes before closing season, which is the thing his competitors mostly do not
have. The site can follow. Getting him moving on the $10 part is usually what
unsticks the $750 part.

### Do not go live with

- The reviews section empty **and** him under the impression it is finished —
  tell him plainly it is the last gap, and that three real ones fix it
- Any price he has not said yes to out loud
- An email address that has not received a test message
