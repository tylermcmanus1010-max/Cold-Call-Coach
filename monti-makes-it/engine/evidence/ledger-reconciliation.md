# Ledger reconciliation

Reproduce with:

```
flask --app app seed && python tests/evidence.py
```

- historic orders backfilled into the ledger: **465**
- ledger total (settled charges and manual confirmations): **$5,357,632.62**
- order-log total (orders marked paid): **$5,357,632.62**
- payment-provider total: **not compared** — there is no provider connection in this environment, so the third leg of §11.4.2's reconciliation is unverified. Ledger and order log are compared; ledger and provider are not.
- breaks: **0**

No break found. The reconciler compares four things: a paid order
with no settled row, a settled row with no paid order, two charge
rows for one order, and the two totals against each other.

`reconcile()` has no write path to `ledger_entries`. §11.4.2 forbids closing
a break by adjusting the ledger, and the way that is enforced is that the
reconciler has nothing to adjust with — it can only write a row describing
what it found.

Asserted continuously by `A32`.
