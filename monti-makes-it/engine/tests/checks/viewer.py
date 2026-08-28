"""A16 — every item exposes an image viewer or says it has none (WI-G-11).

§0.3.8 makes the viewer a requirement on every item in the client portal, and
§1.6 makes a missing one a P1. The failure this catches is not a crash — it is
an item that renders a blank space where its images should be, which reads to a
member as a broken page and to a reviewer as "no images yet".

So the check accepts exactly two outcomes per item: a wired viewer, or the
explicit empty state. Silence is the failure.
"""
import re

from . import Check, Finding

VIEWER = re.compile(r'data-iv="([^"]+)"')
EMPTY = re.compile(r'data-iv-empty="([^"]+)"')


def _item_routes(ctx):
    routes = []
    for row in ctx.query("SELECT sku FROM catalog_items WHERE is_public = 1 AND is_active = 1"):
        routes.append(("public", f"/catalogue/{row['sku']}", ctx.public_client))
    for row in ctx.query(
            "SELECT item_id FROM catalogue_registrations WHERE customer_id = ? AND active = 1",
            (ctx.member_customer_id,)):
        routes.append(("portal", f"/portal/catalog/{row['item_id']}", ctx.member_client))
    return routes


def run(ctx):
    findings = []
    routes = _item_routes(ctx)
    if not routes:
        return [Finding("A16", "no item pages exist to check — an unexercised viewer "
                               "check is not a pass")]
    for surface, route, client in routes:
        body = client.get(route, follow_redirects=True).get_data(as_text=True)
        if VIEWER.search(body) or EMPTY.search(body):
            continue
        findings.append(Finding(
            f"{surface}:{route}",
            "neither an image viewer nor an explicit empty state is present"))
    return findings


def prove(ctx):
    """Remove the viewer from one item page, confirm A16 names that page."""
    from pathlib import Path
    tpl = (Path(__file__).resolve().parent.parent.parent / "monti" / "templates"
           / "public" / "catalogue_item.html")
    original = tpl.read_text()
    marker = "{{ viewer(item.images, item.name, 'cat-' ~ item.id) }}"
    if marker not in original:
        return False, "the viewer call is not where the proof expects it"
    try:
        tpl.write_text(original.replace(marker, ""))
        findings = run(ctx)
        caught = bool(findings)
        note = str(findings[0]) if findings else "MISSED"
    finally:
        tpl.write_text(original)
    return caught, f"viewer removed from the public item page -> {note}"


CHECKS = [Check("A16", "Every item page carries a viewer or an explicit empty state",
                run, prove)]
