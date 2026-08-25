# The Long-Form Engine

**YouTube long-form is the business. Everything else is top-of-funnel.**

## The number that decides the strategy

| Format | RPM (B2B/sales niche) | Revenue per 1M views |
|---|---|---|
| YouTube long-form | $7–11 | **$7,000–11,000** |
| YouTube Shorts | $0.15–0.25 | $150–250 |
| TikTok Creator Rewards | ~$0.40–1.00 per 1k qualified | $400–1,000 |
| Facebook Reels | ~$0.20–0.50 per 1k | $200–500 |

Shorts RPM runs 3–14% of long-form in nearly every niche. It takes roughly
**11,000–34,000 Shorts views to earn what 1,000 long-form views earn.**

One long-form view is worth 20–50 short-form views. That single ratio dictates
every decision below.

**The good news:** the sales/B2B niche survives the pivot intact. Finance,
insurance, B2B software, and real estate advertisers pay the highest rates on
the platform because their customers are worth thousands each. We are already in
the top CPM tier. If the niche were gaming or entertainment, ad revenue would be
a dead end.

## Path to monetization — the math

YouTube gives you two doors. Take the long-form one.

| Path | Requirement | Reality |
|---|---|---|
| Shorts | 1,000 subs + **10M Shorts views / 90 days** | 111,000 views/day. Brutal. |
| Long-form | 1,000 subs + **4,000 watch hours / 12 months** | Very achievable. |

**4,000 watch hours = 240,000 watch minutes.**

At a 10-minute video with 45% average retention, each view returns ~4.5 watch
minutes. So:

```
240,000 minutes ÷ 4.5 minutes per view ≈ 53,000 long-form views
```

Over 12 months that's about **1,000 long-form views per week.** At two uploads a
week, 500 views per video. That is a realistic first-year target, and it is a
completely different order of difficulty than 10M Shorts views in 90 days.

Run the numbers for your own assumptions:

```
node content-ops/tools/revenue.mjs --rpm 9 --length 10 --retention 45
```

## The three structural levers

### 1. The 8-minute threshold

Videos over 8 minutes are eligible for **mid-roll ads.** This is the single
largest RPM multiplier available to you — it can roughly double revenue per view
versus a 7:59 video with one pre-roll.

**Every long-form video targets 9–14 minutes.** Not 8:05 — that reads as
padding-to-threshold and audiences feel it. Build content that genuinely earns
9–14 minutes.

### 2. Watch time beats retention percentage

This is counterintuitive and most creators get it backwards:

| Video | Retention | Watch time per view |
|---|---|---|
| 6 min | 60% | 3.6 min |
| 12 min | 40% | **4.8 min** |

The 12-minute video at "worse" retention delivers 33% more watch time, more
mid-roll impressions, and more revenue. **Optimize the absolute minutes, not the
percentage.** A high retention rate on a short video is a vanity metric.

Floor to respect: below ~30% average retention YouTube stops recommending. Target
the 40–50% band on a 10–14 minute video.

### 3. Session time

YouTube rewards keeping viewers **on YouTube**, not just on your video. A viewer
who finishes your video and immediately watches another is worth far more to the
algorithm than one who leaves.

- End screens pointing to a specific next video, every time
- Every video in a playlist, no exceptions
- Reference your own videos mid-content ("I broke this down fully in the
  gatekeeper one") — it plants the next click
- Never end with a wind-down. End mid-momentum, pointing somewhere.

## Formats that legitimately fill 9–14 minutes

Thirty-second tactics don't stretch. These have natural length:

| Format | Length | Why it holds |
|---|---|---|
| **Multi-call teardown** | 12–16 min | 3–4 calls, annotated. Each call is a fresh loop. |
| **Line-by-line script breakdown** | 10–12 min | Natural sequence, built-in progression. |
| **"100 calls" documentary episode** | 12–18 min | Story arc, real stakes, repeatable weekly. |
| **Objection deep-dive** | 9–12 min | One objection, six variants, real audio for each. |
| **Reaction / analysis** | 10–14 min | Famous sales scenes, viral clips, others' calls. Cheap to produce. |
| **Head-to-head test** | 10–14 min | Two scripts, 50 calls each, real data. |
| **Rebuild** | 9–12 min | Take a bad call, rebuild it live, run it again. |

## 20 long-form concepts

Packaged title-first — the title and thumbnail are designed before the video
exists, and the video is built to deliver them.

**Teardowns**
1. "I Analyzed 50 Cold Calls. The Good Ones All Did This One Thing." — 14 min
2. "Ranking 10 Cold Call Openers From Worst to Best" — 12 min
3. "This Cold Call Went Perfectly Until Second 41" — 10 min
4. "3 Cold Calls, 3 Hangups, 3 Fixable Mistakes" — 13 min
5. "I Rebuilt the Worst Cold Call I've Ever Heard" — 11 min

**The series** *(the spine — weekly, numbered, public scoreboard)*
6. "100 Cold Calls in 30 Days: Week 1" — 12 min
7. "Week 2: I Changed One Sentence and Everything Changed" — 12 min
8. "Week 3: The Worst Day" — 12 min
9. "Week 4: Final Numbers, Including What Failed" — 16 min

**Tests**
10. "Script A vs Script B: 100 Calls Each. Here's the Data." — 13 min
11. "Does the Pattern Interrupt Still Work? I Tested It 50 Times." — 11 min
12. "I Cold Called at 5 Different Times of Day for a Week" — 12 min
13. "Permission Openers vs Direct Openers: 200 Calls" — 14 min

**Deep dives**
14. "Every Way to Handle 'Not Interested' (Ranked)" — 12 min
15. "The First 8 Seconds: A Frame-by-Frame Breakdown" — 10 min
16. "Voicemails That Actually Get Returned" — 9 min
17. "The Gatekeeper Playbook" — 13 min

**Reaction**
18. "A Sales Trainer Reacts to Cold Calls in Movies" — 14 min
19. "Reacting to the Worst Sales Advice on TikTok" — 12 min
20. "I Watched 100 Sales Gurus. Here's What They All Get Wrong." — 15 min

Concepts 18–20 are the cheapest to produce and the most likely to break out —
reaction content borrows an existing audience's search intent. Use them when the
production budget for teardowns runs dry.

## Retention architecture for 10–14 minutes

Same principles as short-form, longer arc.

| Time | Job |
|---|---|
| 0:00–0:15 | Cold open on the most compelling moment in the video. No intro, no logo, no "what's up." |
| 0:15–0:45 | The promise + the stakes. What they'll know by the end, why it matters. |
| 0:45–1:30 | **First real payoff.** Deliver something usable before minute two. |
| Every 90–120s | Re-engagement beat: new call, chapter card, sharp angle change, number reveal. |
| ~50% mark | The biggest single payoff. Place your best material at the midpoint, not the end — it carries viewers through the mid-roll. |
| Final 60s | Resolve, then point at the next video. No wind-down. |

**Chapters:** add them. They improve retention because viewers who would have
left instead skip forward — a skip keeps the session alive, an exit doesn't.

**Mid-roll placement:** YouTube auto-places, but manual is better. Put breaks
immediately *after* a payoff, never before one. An ad interrupting an unresolved
loop is where people leave.

## Packaging — title and thumbnail

For an ad-revenue channel, packaging is the highest-leverage work you do. A great
video with a bad thumbnail earns nothing.

**Title rules**
- Under 60 characters so it doesn't truncate
- Lead with the number or the conflict
- Front-load searchable terms — long-form gets search traffic for years, and
  search traffic is the compounding kind
- Never clickbait past what you deliver. Ad revenue depends on retention, and
  betrayed viewers leave at 0:30

**Thumbnail rules**
- Three elements maximum. It's viewed at 210×118 pixels.
- Brand red as the accent, always — consistency compounds recognition
- Text: 3–4 words maximum, at a size readable on a phone
- The thumbnail states the *conflict*, the title states the *specific*. Never
  duplicate each other — that wastes half your packaging.

Generate branded thumbnails:

```
python3 content-ops/assets/generate_thumbnail.py --top "50 cold calls" --bottom "one pattern" --out concept-01.png
```

## Upload cadence

| Asset | Frequency | Role |
|---|---|---|
| Long-form | **2×/week** | The revenue |
| Shorts | 1–2/day | Subscriber acquisition, cut from long-form |
| TikTok | 2–3/day | Discovery + hook testing |
| Reels / FB | 1–2/day | Reach, near-zero marginal cost |
| X | 3–5/day | Idea testing before production spend |

Two long-form a week is the floor that makes the math work. Every short-form
piece is cut from long-form footage — you are not producing two content streams,
you are producing one and harvesting it.

## What changes from the old plan

| Was | Now |
|---|---|
| TikTok primary | **YouTube long-form primary** |
| 30-second tactics | **9–14 minute formats** |
| Optimize 3s retention | **Optimize total watch minutes** |
| Email list is the goal | **Subscribers + watch hours are the goal** |
| Short-form is the product | **Short-form feeds the product** |

Short-form still matters — it's how people find you, and subscribers are half the
monetization requirement. It just isn't where the money is.
