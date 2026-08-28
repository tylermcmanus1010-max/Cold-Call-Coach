"""A05 — tenant isolation, the product's core promise.

§1.4 puts "prevent one member from reaching another member's data" above every
other launch priority, so this is the check that runs first and the one whose
failure is never a P1.

Two details matter. The first is that cross-tenant access must return 404, not
403: a 403 confirms the row exists, which tells a prober they have found a real
order id belonging to someone else. The second is that asset URLs count as
routes — an image or a document reachable by guessing its id is the same breach
as a page, and it is the half that gets forgotten because it does not look like
a page.
"""
from . import Check, Finding

# Route templates probed as the wrong member. `{id}` is filled with a row id
# that belongs to somebody else.
SCOPED_ROUTES = [
    "/portal/quotes/{quote_id}",
    "/portal/orders/{order_id}",
    "/portal/orders/{order_id}/checkout",
    "/portal/files/{file_id}",
]


def run(ctx):
    findings = []
    other = ctx.other_customer_id
    if other is None:
        return [Finding("A05", "only one customer exists — tenancy cannot be probed, "
                               "and an unprobed tenancy check is not a pass")]

    ids = {
        "quote_id": ctx.first_id("quotes", other),
        "order_id": ctx.first_id("orders", other),
        "file_id": ctx.first_file_id(other),
    }

    for template in SCOPED_ROUTES:
        needed = [k for k in ids if "{" + k + "}" in template]
        if any(ids[k] is None for k in needed):
            continue
        route = template.format(**ids)
        r = ctx.member_client.get(route)
        if r.status_code == 404:
            continue
        if r.status_code == 403:
            findings.append(Finding(
                route, "returned 403 — confirms the row exists to someone who should "
                       "not know it does; §Glossary requires 404"))
        elif r.status_code < 400:
            findings.append(Finding(
                route, f"returned {r.status_code} — another member's row was served"))
        else:
            findings.append(Finding(route, f"returned {r.status_code}, expected 404"))
    return findings


def prove(ctx):
    """Remove one scoping clause, confirm A05 names it, put it back."""
    from pathlib import Path
    auth = Path(__file__).resolve().parent.parent.parent / "monti" / "auth.py"
    original = auth.read_text()
    present = """    if customer_id is None or row_customer != customer_id:
        abort(404)"""
    if present not in original:
        return False, "own_or_404's scoping clause is not where the proof expects it"
    try:
        auth.write_text(original.replace(present, "    if False:\n        abort(404)"))
        ctx.reload()
        findings = run(ctx)
        caught = bool(findings)
        note = str(findings[0]) if findings else "MISSED"
    finally:
        auth.write_text(original)
        ctx.reload()
    return caught, f"own_or_404 scoping clause removed -> {note}"


CHECKS = [Check("A05", "Tenant isolation on every member-scoped route and asset URL",
                run, prove)]
