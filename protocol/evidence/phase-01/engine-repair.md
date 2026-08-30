# The b708710 regression, repaired

`b708710` — *"Adopt the prototype stylesheet as the theme, everywhere"* — replaced
`monti/static/css/app.css` wholesale. The templates were not changed with it, so every
class and token the old stylesheet defined and the new one did not went on being asked for
and stopped resolving. **An undefined custom property does not fall back to the cascade; it
computes to nothing at all.**

That commit was reported as verified. What was verified was horizontal overflow and console
errors, neither of which notices a chart turning black or a border ceasing to exist.

## What was orphaned

**Nine classes**, emitted by templates, defined nowhere:
`.chart-wrap`, `.chart-svg`, `.chart-grid`, `.chart-axis`, `.chart-bar`, `.meter`,
`.meter-green`, `.range-row`, `.range-btn`.

**Nine tokens**, referenced 51 times across the stylesheet and templates:

| token | uses | what stopped working |
|---|---|---|
| `--sunk` | 13 | sunken surfaces drew flat |
| `--line` | 11 | borders vanished |
| `--line-soft` | 8 | dividers vanished |
| `--text-2` | 5 | secondary text colour stopped applying |
| `--radius` | 5 | corners went square |
| `--violet` | 4 | the not-yet-overdue clock lost its colour |
| `--ink-3` | 2 | tertiary text stopped applying |
| `--text` | 1 | primary ink stopped applying |
| `--green-line` | 1 | a card border vanished |
| `--sans` | 1 | one label lost its font stack |

## Measured after the repair

Chromium, 1440×1000, `/admin/revenue?period=90d`, against a labelled local development
seed (§1.5) so the chart and the bars had data to draw. Probe: `engine-repair-probe.mjs`.

```
rect.chart-bar   fill              rgb(30, 143, 99)     was rgb(0, 0, 0)
.chart-grid line stroke            visible              was none
.chart-axis text fill              muted                was default black
.meter           bounding box      125 x 8              was 127 x 0
.meter > span    display / bg      block / green        was inline / transparent
.range-btn       padding / border  11.2px / 1px         was 0px / 0px
.range-btn.active background       rgb(11, 92, 63)      was transparent
--text --sunk --line               all resolve          were undefined
```

Ten assertions, ten passing, no page errors. Screenshots `engine-chart-fixed.png` and
`engine-revenue-fixed.png`.

## What this is not

**This closes no register item.** It restores the state the build was in before a commit
of mine broke it. CHG-001, CHG-005 and CHG-010 stay OPEN and their gates are unchanged:

- **CHG-001** additionally requires seven distinct daily marks whose sum equals the
  headline. **It still does not** — `analytics.series()` emits its buckets from the
  window's start date while `summary()` includes today, so today is counted in the total
  and drawn nowhere. The gap is identical at every period. That is **D-031** and it is
  Phase 5's, untouched here.
- **CHG-005** requires a reader to rank clients from the bars with the numbers hidden.
  The bars render now; whether they are rankable is A11Y-01's call at Phase 7.
- **CHG-010** requires that no table repeats a filled primary button per row. The
  revenue screen still does — "Open portal", on every row. Untouched.

Suites after the repair: 217 end-to-end passing, 16/16 Class A passing.
