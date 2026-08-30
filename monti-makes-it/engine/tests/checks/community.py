"""A42 — nothing on the reviews page that a person did not write and approve.

A testimonials page is the easiest place in an application to break §1.5, and it
is the place people break it most cheerfully, because a fake review reads as
placeholder copy rather than as what it is: a claim about a customer who does not
exist, printed under a name.

So this check holds four things.

  Nothing seeded.      A fresh launch database has zero testimonials. Not "no
                       obviously fake ones" — zero. If the page is empty it says
                       so, and an empty page is the correct state until somebody
                       real writes something.

  Moderation is real.  A submission lands PENDING and does not appear publicly.
                       Checked by submitting one and fetching the page, not by
                       reading the status column: the filter has to be in the
                       query, and the way to prove that is to look at the HTML.

  Decline keeps it.    A declined review stays in the table with its reason. The
                       fact that we chose not to publish something is the part
                       worth having later, and deleting the row loses it.

  Feedback survives mail. The row is written before the send is attempted, so
                       feedback whose email failed is still there and is still
                       findable. Proven by breaking the mailer on purpose.

And one for the assistant: it must not answer a question the site has no answer
for. A search box that returns its least-bad match is worse than one that returns
nothing, and on a manufacturing site the least-bad match is eventually a price.
"""
import re

from . import Check, Finding

PROBE = "A42 probe"


def _clear(ctx):
    ctx.execute("DELETE FROM testimonials WHERE email LIKE 'a42%'")
    ctx.execute("DELETE FROM feedback WHERE message LIKE ?", (f"%{PROBE}%",))


def run(ctx):
    from monti import assistant, community
    from monti.blueprints.public import FAQS

    findings = []
    with ctx.app.app_context():
        _clear(ctx)

        # ---- nothing seeded ------------------------------------------------
        seeded = ctx.query("SELECT * FROM testimonials WHERE email NOT LIKE 'a42%'")
        if seeded:
            findings.append(Finding(
                "testimonials",
                f"{len(seeded)} review(s) exist that nobody submitted through the form. "
                f"First is by {seeded[0]['author_name']!r} — a testimonial nobody "
                "wrote is a claim about a customer who does not exist"))

        page = ctx.public_client.get("/reviews", follow_redirects=True)
        if page.status_code != 200:
            findings.append(Finding("GET /reviews", f"returned {page.status_code}"))
            return findings
        body = page.get_data(as_text=True)
        if not community.published() and "Nothing published yet" not in body:
            findings.append(Finding(
                "GET /reviews",
                "no approved reviews exist and the page does not say so — an empty "
                "state is the honest answer, and its absence usually means "
                "something was invented to fill the space"))

        # ---- a submission is not published --------------------------------
        row = community.submit_testimonial(
            "A42 Reviewer", "a42-review@example.test",
            "A42 probe review body, long enough to be accepted by the form rules.",
            company_name="A42 Probe Co")
        if row["status"] != "PENDING":
            findings.append(Finding(
                "community.submit_testimonial",
                f"a new review landed as {row['status']!r}. Anyone who can type could "
                "put words on the public page"))
        after = ctx.public_client.get("/reviews", follow_redirects=True).get_data(as_text=True)
        if "A42 probe review body" in after:
            findings.append(Finding(
                "GET /reviews",
                "an unapproved review is on the public page — the moderation is not "
                "in the query"))
        if any(t["id"] == row["id"] for t in community.published()):
            findings.append(Finding(
                "community.published",
                "returns a PENDING review, so every caller inherits the leak"))

        # ---- approve, then it appears; take it down, then it does not ------
        community.approve(row["id"], "a42-probe")
        live = ctx.public_client.get("/reviews", follow_redirects=True).get_data(as_text=True)
        if "A42 probe review body" not in live:
            findings.append(Finding(
                "GET /reviews", "an approved review is not on the page"))
        community.unpublish(row["id"], "a42-probe")
        gone = ctx.public_client.get("/reviews", follow_redirects=True).get_data(as_text=True)
        if "A42 probe review body" in gone:
            findings.append(Finding(
                "GET /reviews", "a review taken down is still published"))

        # ---- decline keeps the row and the reason -------------------------
        community.decline(row["id"], "a42-probe", "A42 probe reason")
        kept = ctx.query("SELECT * FROM testimonials WHERE id = ?", (row["id"],))
        if not kept:
            findings.append(Finding(
                "community.decline",
                "deleted the review. Choosing not to publish something is a fact, "
                "and it is now unrecoverable"))
        elif kept[0]["decline_reason"] != "A42 probe reason":
            findings.append(Finding(
                "community.decline", "did not keep the reason it was given"))

        # ---- feedback is stored before it is sent -------------------------
        before = ctx.query("SELECT COUNT(*) AS c FROM feedback")[0]["c"]
        saved = None
        try:
            saved, _emailed = community.leave_feedback(
                f"{PROBE} — the checkout button did nothing.",
                name="A42", email="a42-feedback@example.test", kind="PROBLEM",
                page="/portal/cart")
        except Exception as exc:                                   # noqa: BLE001
            # A door that raises is a defect this check should name, not a crash
            # that takes the suite down with it. If the mailer is what raised,
            # the row was never written and the feedback is gone — which is the
            # whole property under test.
            findings.append(Finding(
                "community.leave_feedback",
                f"raised {type(exc).__name__}: {exc}. Nothing was recorded, so "
                "whatever they wrote is gone"))
        if saved is not None:
            rows = ctx.query("SELECT * FROM feedback WHERE id = ?", (saved["id"],))
            if not rows:
                findings.append(Finding("community.leave_feedback", "wrote no row"))
            elif ctx.query("SELECT COUNT(*) AS c FROM feedback")[0]["c"] != before + 1:
                findings.append(Finding("feedback", "the row count did not move by one"))
        elif ctx.query("SELECT COUNT(*) AS c FROM feedback")[0]["c"] != before:
            findings.append(Finding("feedback", "a failed submission left a partial row"))

        # ---- the assistant declines rather than guessing -------------------
        assistant.reset()
        # Two shapes of off-topic question. The second is the one that gets
        # through: it shares a common word with the corpus, so a score-only
        # filter reads it as a match.
        for nonsense_q in ("what is the airspeed velocity of an unladen swallow",
                           "do you sell live tigers on tuesdays"):
            nonsense = assistant.answer(nonsense_q, faqs=FAQS)
            if nonsense["found"]:
                findings.append(Finding(
                    "assistant.answer",
                    f"answered {nonsense_q!r} with {nonsense['reply'][:60]!r}. A search "
                    "box that returns its least-bad match eventually returns a price"))

        # A weak match must present itself as the nearest thing, not as the
        # answer. This is the property that makes a small corpus safe: the
        # wording carries the uncertainty rather than a threshold pretending
        # there is none.
        weak = assistant.answer("price of bitcoin", faqs=FAQS)
        if weak["found"] and "not sure" not in weak["reply"]:
            findings.append(Finding(
                "assistant.answer",
                f"answered a loose match as though it were certain: "
                f"{weak['reply'][:70]!r}"))
        real = assistant.answer("how do I get a price", faqs=FAQS)
        if not real["found"]:
            findings.append(Finding(
                "assistant.answer",
                "has no answer for 'how do I get a price', which is the question the "
                "box exists for"))
        else:
            # Every answer has to be text that is already on a page, with the
            # link to that page. An answer with no source is an answer nobody
            # can check.
            for hit in real["hits"]:
                if not hit.get("endpoint") or not hit.get("body"):
                    findings.append(Finding(
                        "assistant.answer",
                        f"returned {hit.get('title')!r} with no source page behind it"))

        reply = ctx.public_client.post("/ask", data={
            "_csrf": ctx.csrf(ctx.public_client), "q": "where are the disclaimers"})
        if reply.status_code != 200:
            findings.append(Finding("POST /ask", f"returned {reply.status_code}"))
        else:
            payload = reply.get_json() or {}
            for link in payload.get("links", []):
                if not str(link.get("url", "")).startswith("/"):
                    findings.append(Finding(
                        "POST /ask",
                        f"pointed at {link.get('url')!r}, which is not a page on this site"))

        _clear(ctx)
    return findings


INSERT_SQL = '    feedback_id = execute(\n        "INSERT INTO feedback (name, email, kind, message, page, user_id, customer_id) "\n        "VALUES (?, ?, ?, ?, ?, ?, ?)",\n        ((name or "").strip() or None, (email or "").strip().lower() or None, kind,\n         message, page, user_id, customer_id))'

INSERT_SQL_AFTER_SEND = '    mail.send(current_app.config["SUPPORT_EMAIL"], "probe",\n              template="no-such-template-a42")\n    feedback_id = execute(\n        "INSERT INTO feedback (name, email, kind, message, page, user_id, customer_id) "\n        "VALUES (?, ?, ?, ?, ?, ?, ?)",\n        ((name or "").strip() or None, (email or "").strip().lower() or None, kind,\n         message, page, user_id, customer_id))'


def prove(ctx):
    """Four defects, each the way this surface actually goes wrong."""
    from pathlib import Path

    caught = []
    community_src = Path(__file__).resolve().parents[2] / "monti" / "community.py"
    assistant_src = Path(__file__).resolve().parents[2] / "monti" / "assistant.py"

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

    # 1. The moderation moves out of the query and into a habit.
    attempt("published() stopped filtering on status", community_src,
            '"SELECT * FROM testimonials WHERE status = \'APPROVED\' "\n'
            '        "ORDER BY display_order DESC, decided_at DESC")',
            '"SELECT * FROM testimonials "\n'
            '        "ORDER BY display_order DESC, decided_at DESC")',
            lambda f: "unapproved review is on the public page" in f.detail
            or "returns a PENDING review" in f.detail)

    # 2. Submissions arrive already published.
    attempt("a submission published itself", community_src,
            '"body, customer_id) VALUES (?, ?, ?, ?, ?, ?)",',
            '"body, customer_id, status) VALUES (?, ?, ?, ?, ?, ?, \'APPROVED\')",',
            lambda f: "landed as 'APPROVED'" in f.detail
            or "unapproved review is on the public page" in f.detail)

    # 3. Declining deletes, so the decision not to publish is lost.
    attempt("declining deleted the review", community_src,
            '''    execute("UPDATE testimonials SET status = 'DECLINED', decided_at = ?, decided_by = ?, "
            "decline_reason = ? WHERE id = ?",
            (now_str(), by, (reason or "").strip() or None, testimonial_id))''',
            '    execute("DELETE FROM testimonials WHERE id = ?", (testimonial_id,))',
            lambda f: "deleted the review" in f.detail)

    # 4. Feedback is composed into an email and only then written down, so a
    #    failing mailer loses it. The realistic version of this: someone builds
    #    the send first, because the send is the part that was asked for.
    attempt("the row was written after the email instead of before", community_src,
            INSERT_SQL, INSERT_SQL_AFTER_SEND,
            lambda f: "wrote no row" in f.detail or "row count did not move" in f.detail
            or "whatever they wrote is gone" in f.detail)

    # 5. The assistant answers everything, which is the same as answering nothing.
    attempt("the assistant returned its least-bad match", assistant_src,
            "    def search(self, question, limit=3, floor=0.34):",
            "    def search(self, question, limit=3, floor=-1.0):",
            # Matches on the stable half of the sentence. The first version
            # looked for wording this check no longer emits — the finding was
            # reworded and the proof kept hunting for the old text, which reads
            # as MISSED and is indistinguishable from a check that cannot fail.
            lambda f: "least-bad match eventually returns a price" in f.detail)

    missed = [name for name, ok, _ in caught if not ok]
    return (not missed), "; ".join(f"{n} -> {d}" for n, _, d in caught)


CHECKS = [Check("A42", "Reviews are written by people and published by a person",
                run, prove)]
