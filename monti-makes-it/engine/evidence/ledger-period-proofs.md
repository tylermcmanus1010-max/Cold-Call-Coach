# Ledger period proofs (`A33`)

The three views are groupings of one row set, so they must sum identically
over the same range — and the finer grouping must compose into the coarser.

| view | buckets | bucket sum | grand total | agree |
|---|---|---|---|---|
| month | 12 | $5,367,695.42 | $5,367,695.42 | yes |
| quarter | 5 | $5,367,695.42 | $5,367,695.42 | yes |
| year | 2 | $5,367,695.42 | $5,367,695.42 | yes |

## Boundary handling

Ranges are half-open — inclusive start, exclusive end. Split at `2026-04-01 00:00:00`:

- rows before: **474**
- rows from that instant on: **454**
- rows in the ledger: **928**
- 474 + 454 = 928 ✓

## Roll-up

The months inside each quarter are summed and compared to that quarter, and
the quarters inside each year to that year. This is the assertion that
catches a view bucketing by a different clock — without it, a quarter view
one second out of step still passes every other check, because its rows are
still each in exactly one bucket and still sum to the same grand total.
