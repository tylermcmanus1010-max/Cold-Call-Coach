"""A38 — an acceptance resolves to the exact words that were on the screen.

The requirement was "a disclaimers tab, and at checkout make checking acceptance
of full disclaimers being read and accepted." The first half is a page. The
second half is the one that is easy to fake, and faking it is the normal way
this gets built: a boolean column, `accepted_disclaimers = 1`.

That column is worth nothing, and it is worth nothing in a specific way. It says
a box was ticked. It does not say what the box said. Disclaimers get rewritten —
that is the point of having a version table at all — and once the text changes,
a boolean points at whatever the page says today rather than at what the member
read. The moment the record matters is the moment the two have diverged, which
is precisely the moment a boolean stops being able to answer.

So this check does not test that a checkbox exists. It tests four things a
boolean cannot do:

  Enforcement.   Paying without the field must not pay. Checked by replaying the
                 form without it, the way a scripted client would, rather than
                 by looking at the template — a `required` attribute is a
                 courtesy to a browser and is not a control.

  Resolution.    Every acceptance row must resolve, through its stored hash, to a
                 version row that still holds the body text.

  Version-bind.  Rewrite the disclaimer, and the old acceptance must still
                 resolve to the OLD body. This is the property under test. A
                 boolean fails it by construction, and so does a foreign key to
                 a row that gets edited in place.

  Immutability.  `monti/disclaimers.py` must contain no path that edits or
                 deletes an acceptance, and none that edits a version's body.
                 Scanned from the source, because a convention nobody checks is
                 a convention that lasts until the first hurry.

There is a fifth, and it is here because of §1.5 rather than because of the
review note. The shipped text is a placeholder — writing law we are not
qualified to write would be worse than shipping nothing, because an empty page
does not read as advice. §1.5 says placeholder content may not sit on a
client-facing surface. The resolution is not to hide it: it is that any body
still carrying the placeholder marker must render a visible stop on the page, so
the exposure is bounded and legible rather than silent. That is checked here,
and it stops being relevant the day counsel's wording is published.
"""
import re
from pathlib import Path

from . import Check, Finding

SOURCE = Path(__file__).resolve().parents[2] / "monti" / "disclaimers.py"
TEMPLATE = (Path(__file__).resolve().parents[2] / "monti" / "templates" / "public"
            / "disclaimers.html")

# An acceptance row may only ever be inserted. A version row may be inserted, and
# may have `superseded_at` stamped — that is how a new version retires the old
# one without touching its body. Anything else against either table is an edit to
# a record someone relied on.
_WRITE = re.compile(
    r"(UPDATE|DELETE\s+FROM)\s+(disclaimer_versions|disclaimer_acceptances)\b",
    re.IGNORECASE)


def _probe_order(ctx):
    """A payable order for the member, carrying no catalogue lines.

    No lines on purpose: registration gating runs before the acceptance gate, and
    an order that trips the earlier one would make this check pass for the wrong
    reason — the payment was refused, just not by the control under test.
    """
    import os
    ref = f"MMI-O-A38{os.getpid()}"
    existing = ctx.query("SELECT id FROM orders WHERE ref = ?", (ref,))
    if existing:
        return existing[0]["id"], ref
    return ctx.execute(
        "INSERT INTO orders (ref, customer_id, status, payment_status, "
        "subtotal_cents, total_cents) VALUES (?, ?, 'PENDING_PAYMENT', 'UNPAID', "
        "1000, 1000)", (ref, ctx.member_customer_id)), ref


def _cleanup(ctx, ref):
    ctx.execute("DELETE FROM disclaimer_acceptances WHERE order_ref = ?", (ref,))
    ctx.execute("DELETE FROM order_items WHERE order_id IN "
                "(SELECT id FROM orders WHERE ref = ?)", (ref,))
    ctx.execute("DELETE FROM ledger_entries WHERE order_id IN "
                "(SELECT id FROM orders WHERE ref = ?)", (ref,))
    ctx.execute("DELETE FROM orders WHERE ref = ?", (ref,))


def run(ctx):
    from monti import disclaimers as disc

    findings = []
    order_id, ref = _probe_order(ctx)
    try:
        with ctx.app.app_context():
            live = disc.current()

        if not live:
            # Not a nuance. The checkout renders the acceptance only when
            # something is published, so an empty table is a checkout that has
            # quietly stopped asking — the failure this check exists to catch,
            # in its most complete form.
            findings.append(Finding(
                "disclaimer_versions",
                "nothing is published, so the checkout shows no acceptance at all "
                "and every order is paid without one"))
            return findings

        # 1. The surface. Unauthenticated, because a disclaimer someone has to
        #    sign in to read is not a disclosure.
        page = ctx.public_client.get("/disclaimers")
        if page.status_code != 200:
            findings.append(Finding("GET /disclaimers",
                                    f"returned {page.status_code} to a signed-out reader"))
        else:
            body = page.data.decode("utf-8", "replace")
            for version in live:
                if version["title"] not in body:
                    findings.append(Finding(
                        f"GET /disclaimers", f"does not show {version['slug']!r}"))
                if version["body_hash"][:12] not in body:
                    findings.append(Finding(
                        "GET /disclaimers",
                        f"shows {version['slug']!r} without its version hash, so a "
                        "reader cannot tell which text they are looking at"))
                # §1.5 — placeholder on a client-facing surface, unmarked.
                if "PLACEHOLDER" in version["body"] and "notice-stop" not in body:
                    findings.append(Finding(
                        "GET /disclaimers",
                        f"{version['slug']!r} is still placeholder text and the page "
                        "carries no stop notice saying so"))

        # 2. Enforcement. Replay the form without the field.
        before = ctx.query("SELECT COUNT(*) AS c FROM disclaimer_acceptances "
                           "WHERE order_ref = ?", (ref,))[0]["c"]
        token = ctx.csrf(ctx.member_client)
        refused = ctx.member_client.post(f"/portal/orders/{order_id}/pay",
                                         data={"_csrf": token, "method": "card"},
                                         follow_redirects=False)
        after = ctx.query("SELECT COUNT(*) AS c FROM disclaimer_acceptances "
                          "WHERE order_ref = ?", (ref,))[0]["c"]
        order = ctx.query("SELECT * FROM orders WHERE ref = ?", (ref,))[0]
        if order["checkout_session_id"]:
            findings.append(Finding(
                f"POST /portal/orders/{order_id}/pay",
                "started a checkout for a form with no acceptance on it — the "
                "control is in the template only, so anything that is not a "
                "browser can pay without accepting"))
        if after != before:
            findings.append(Finding(
                "disclaimer_acceptances",
                "recorded an acceptance for a request that did not contain one"))
        if refused.status_code not in (301, 302):
            findings.append(Finding(
                f"POST /portal/orders/{order_id}/pay",
                f"answered {refused.status_code} to an unaccepted payment instead of "
                "sending the member back to read them"))

        # 3. Resolution, on a real acceptance through the same door.
        accepted = ctx.member_client.post(
            f"/portal/orders/{order_id}/pay",
            data={"_csrf": token, "method": "card", "accept_disclaimers": "1"},
            follow_redirects=False)
        rows = ctx.query("SELECT * FROM disclaimer_acceptances WHERE order_ref = ?", (ref,))
        if len(rows) != len(live):
            findings.append(Finding(
                "disclaimer_acceptances",
                f"wrote {len(rows)} rows for {len(live)} live disclaimers — an "
                "acceptance that does not name each text it covers cannot say "
                "which of them was agreed to"))
        with ctx.app.app_context():
            for row in rows:
                resolved = disc.version_by_hash(row["slug"], row["body_hash"])
                if resolved is None:
                    findings.append(Finding(
                        f"disclaimer_acceptances#{row['id']}",
                        f"stores {row['body_hash'][:12]!r} for {row['slug']!r}, which "
                        "resolves to no text at all"))
                elif not row["actor_email"]:
                    findings.append(Finding(
                        f"disclaimer_acceptances#{row['id']}",
                        "records no person — an acceptance nobody made"))
        if accepted.status_code not in (301, 302, 303):
            findings.append(Finding(
                f"POST /portal/orders/{order_id}/pay",
                f"answered {accepted.status_code} to an accepted payment"))

        # 4. Version-bind. Rewrite one, and the old acceptance must not move.
        if rows:
            slug = rows[0]["slug"]
            old_hash = rows[0]["body_hash"]
            with ctx.app.app_context():
                original = disc.version_by_hash(slug, old_hash)
                old_body = original["body"] if original else None
                disc.publish(slug, "A38 probe — rewritten",
                             (old_body or "") + "\n\nA38 probe clause.", "a38-probe")
                still = disc.version_by_hash(slug, old_hash)
                if still is None or still["body"] != old_body:
                    findings.append(Finding(
                        f"disclaimer_versions.{slug}",
                        "publishing new text changed what an existing acceptance "
                        "resolves to — the record now says the member agreed to "
                        "words they never saw"))
                if disc.has_accepted_current(ctx.member_customer_id, slug):
                    findings.append(Finding(
                        f"disclaimers.has_accepted_current({slug!r})",
                        "reports the member has accepted the current version after "
                        "the text was rewritten under them"))
                # Put the original back live. `publish` supersedes rather than
                # edits, so this leaves the probe's version in the table as a
                # superseded row — which is correct: deleting it would be the
                # exact edit this check forbids.
                if old_body is not None:
                    disc.publish(slug, original["title"], old_body, "a38-probe-restore")

        # 5. Immutability, from the source.
        source = SOURCE.read_text()
        for match in _WRITE.finditer(source):
            line_no = source[:match.start()].count("\n") + 1
            line = source.splitlines()[line_no - 1]
            # The one legitimate write: stamping the outgoing version superseded.
            if "superseded_at" in line and "UPDATE" in line.upper():
                continue
            findings.append(Finding(
                f"monti/disclaimers.py:{line_no}",
                f"edits or deletes a record someone relied on: {line.strip()[:90]}"))
    finally:
        _cleanup(ctx, ref)
    return findings


def prove(ctx):
    """Four defects, each the shape someone would actually ship."""
    caught = []
    portal = Path(__file__).resolve().parents[2] / "monti" / "blueprints" / "portal.py"

    def attempt(label, path, before, after, matches):
        original = path.read_text()
        broken = original.replace(before, after, 1)
        assert broken != original, f"proof {label!r} no longer matches the source"
        path.write_text(broken)
        try:
            ctx.reload()
            hits = [f for f in run(ctx) if matches(f)]
            caught.append((label, bool(hits), str(hits[0]) if hits else "MISSED"))
        finally:
            path.write_text(original)
            ctx.reload()

    # 1. The classic: the checkbox is in the template, the server never looks.
    attempt("the server stopped checking the box it renders", portal,
            '        if not request.form.get("accept_disclaimers"):\n'
            '            flash("Please read and accept the disclaimers before paying.", "error")\n'
            '            return redirect(url_for("portal.checkout", order_id=order_id))\n',
            "",
            lambda f: "no acceptance on it" in f.detail)

    # 2. The record loses its grip on the text — a stored hash that points nowhere
    #    is a boolean wearing a hash's clothes.
    attempt("the acceptance stored a hash that resolves to no text", SOURCE,
            '             version["body_hash"], ip_hint))',
            '             "0" * 64, ip_hint))',
            lambda f: "resolves to no text" in f.detail)

    # 3. Publishing edits in place instead of superseding — the version table
    #    still exists, and stops meaning anything.
    attempt("publishing rewrote the old version in place", SOURCE,
            '    execute("UPDATE disclaimer_versions SET superseded_at = datetime(\'now\') "\n'
            '            "WHERE slug = ? AND superseded_at IS NULL", (slug,))\n'
            '    execute("INSERT INTO disclaimer_versions (slug, title, body, body_hash, published_by) "\n'
            '            "VALUES (?, ?, ?, ?, ?)", (slug, title, body, h, actor))',
            '    execute("UPDATE disclaimer_versions SET body = ?, body_hash = ? "\n'
            '            "WHERE slug = ? AND superseded_at IS NULL", (body, h, slug))\n'
            '    execute("INSERT OR IGNORE INTO disclaimer_versions (slug, title, body, body_hash, published_by) "\n'
            '            "VALUES (?, ?, ?, ?, ?)", (slug, title, body, h, actor))',
            lambda f: "edits or deletes a record" in f.detail
            or "resolves to" in f.detail or "never saw" in f.detail)

    # 4. §1.5 — the placeholder loses its stop notice and reads as advice.
    attempt("placeholder text lost the notice saying it is a placeholder", TEMPLATE,
            "notice-stop", "notice-quiet",
            lambda f: "no stop notice" in f.detail)

    missed = [name for name, ok, _ in caught if not ok]
    return (not missed), "; ".join(f"{n} -> {d}" for n, _, d in caught)


CHECKS = [Check("A38", "An acceptance resolves to the exact disclaimer text that was shown",
                run, prove)]
