"""Class A checks — machine-decidable, and each one proven able to fail.

A check that has never failed is not a check (protocol §0.2.7). Every check here
ships with a proof that injects a realistic defect, asserts the check names it,
and puts the defect back. `python tests/class_a.py --prove` runs those proofs;
a check counts toward coverage only when its proof passes.
"""


class Finding:
    """One located violation. `where` is a file:line, a table.column, or a route."""

    def __init__(self, where, detail):
        self.where = where
        self.detail = detail

    def __str__(self):
        return f"{self.where} — {self.detail}"


class Check:
    """id, what it asserts, how to run it, and how to prove it can fail.

    `run(ctx)` returns a list of Findings; empty means the check passes.
    `prove(ctx)` breaks something real, confirms `run` names it, then reverts.
    It returns (caught, what_was_broken) so the proof log records the defect.
    """

    def __init__(self, cid, title, run, prove):
        self.id = cid
        self.title = title
        self.run = run
        self.prove = prove


def collect():
    """Every check, in id order. Imported lazily so a broken module is loud."""
    from . import (agents, brand, community, data, disclaimercheck, gating,
                   ledgercheck,
                   localisation, money, onedoor, productmerge, provenance,
                   scheduling, tenancy, tooling, viewer)
    checks = []
    for module in (tenancy, brand, gating, money, data, viewer, agents, tooling,
                   ledgercheck, provenance, onedoor, disclaimercheck, productmerge, scheduling, localisation, community):
        checks.extend(module.CHECKS)
    return sorted(checks, key=lambda c: c.id)
