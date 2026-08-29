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

## Open question against §5, filed for AIM-00

The **payment states / ACH and card settlement** domain requires 20 sources and is
assigned to DOC-01. CHG-007 was scrapped (§2.2) and PAY-01 is dormant (§4.7), so no
in-scope decision depends on that domain. §5.1 requires every source to be *"cited
against the decision it informs."* Twenty sources with no decision to inform cannot
satisfy that test. Either the domain minimum drops and the §5 total becomes 230, or the
in-scope decisions those 20 sources inform must be named. Recorded here rather than
resolved, because changing a §5 minimum is a scope change under §12.
