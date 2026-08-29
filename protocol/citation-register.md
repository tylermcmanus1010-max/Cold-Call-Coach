# Citation register

RSCH-01's §5 register. Custodian: RSCH-01 (SK-01). Every entry carries source, domain,
tier, date, and the specific decision it informs.

**Status: NOT OPENED.** Phase 3 opens it.

A domain is satisfied when RSCH-01 says the register shows it satisfied, not when the
owning agent says it read enough (§5.4).

## Domain targets (§5.2)

| Domain | Min | Owning agent | Cited so far |
|---|---|---|---|
| Accessibility & contrast standards | 25 | DS-01 | 0 |
| Data visualization practice and chart correctness | 30 | VIZ-01 | 0 |
| Financial document standards | 35 | DOC-01 | 0 |
| Payment states, ACH and card settlement behavior | 20 | DOC-01 | 0 |
| Internationalization | 30 | I18N-01 | 0 |
| Multi-tenant isolation and access control patterns | 25 | ADMIN-01 | 0 |
| Usability: form design, first-run, plain language | 30 | UX-01 | 0 |
| Contract manufacturing / import operations context | 30 | SITE-01 | 0 |
| Competitor and adjacent-product teardown | 25 | SITE-01 | 0 |
| **Total** | **250** | | **0** |

## Staging (§5.3)

- Phase 4 does not open until accessibility + dataviz are satisfied — 55 sources, called at Phase 3.
- Phase 10 does not open until the i18n domain is satisfied.
- Phase 16 does not open until the financial-document domain is satisfied.
- The remainder must be complete before Phase 20.

## Open against §5

**D-021** — the payment-states / ACH and card-settlement domain requires 20 sources and has
no in-scope decision to cite against. **D-022** — Phase 16's entry names one of the two
financial domains. Both are filed in `decisions.md` with options and a recommendation; both
change when a phase may open, and neither is resolved here.
