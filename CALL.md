# The call

**The goal of the call is to get an email address. Not to sell a website.**

That makes it a 45-second call you cannot really lose, and it is why the page
is attached to an email rather than described down the phone.

---

## Say this

> "Hi [name], my name's Tyler — I build websites for businesses here in
> [their town]. I'm not going to sell you anything on the phone. I noticed
> [the one specific thing]. I already built you a new version — can I email it
> over so you can look at it on your phone? No cost, no obligation."

Get the email address. **Read it back to him.** Hang up.

## The one specific thing

Take it straight from `pitch.md`. One fact, said plainly, no jargon:

| What the audit found | What you say |
|---|---|
| No HTTPS | "Chrome shows visitors a 'Not secure' warning before they see anything" |
| Not mobile-friendly | "It doesn't fit a phone screen — people have to pinch and zoom" |
| No tap-to-call | "Your number isn't tappable, so people have to write it down" |
| Hosting placeholder | "Your domain shows a blank hosting page — people assume you closed" |
| Copyright years old | "It looks like nobody's touched it since [year]" |

One is enough. Listing five sounds like an attack.

## If they say

**"How much?"** → "$750 if you want it. But look at it first — what's the best email?"

**"We already have someone."** → "No problem, I'll send it anyway. Delete it if it's not useful. What's the best email?"

**"Send it to info@..."** → Fine. Read it back and send it.

**"Not interested."** → "Understood, thanks for your time." Hang up. Next.

## Never

- Never mention a bad review
- Never promise a fix, a date, or a feature on the phone
- Never touch anyone's domain or DNS the same day
- Never quote a number other than the ones in `config/pricing.json`

## Nobody picked up

Do not leave a voicemail. Cold voicemails are rarely returned and you lose the
live conversation you were calling for. Log it and move down the list:

```
./cc tried hue-salon "no answer"
```

Best times to catch a small business, roughly:

| | Try | Avoid |
|---|---|---|
| Salons, barbers, spas | Tue–Thu 10–11am | Fri, Sat, and lunchtime |
| Trades — plumbers, roofers, auto | 7–8am, or 4–5pm | Mid-morning, they are on a job |
| Dentists, medical | 9–11am, 2–4pm | Monday morning, lunch |
| Restaurants, bakeries | 2–4pm | Any mealtime |

Four attempts is enough. `./cc status <slug> dead` and spend the time on a
business that answers the phone.

## After

1. Attach `index.html`, paste the email from `pitch.md`, send
2. `./cc sent <slug>`
3. No reply in three days → send the follow-up text at the bottom of `pitch.md`
4. They say yes → `DELIVERY.md`
