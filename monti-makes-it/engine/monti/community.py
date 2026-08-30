"""Feedback, and reviews people write about us (CHG-033, CHG-034).

FEEDBACK IS STORED AS WELL AS SENT

The obvious build is a form that composes an email. Then the SMTP host is down
for four minutes, someone tells us the checkout is broken, and the only record of
it was inside a failed connection. So the row is written first and the email is
attempted second; `emailed_at` stays null when the send fails, and the admin list
shows those separately. A complaint we lost is worse than a complaint we were
slow to answer.

REVIEWS ARE MODERATED, AND NOTHING IS SEEDED

"Obviously we will control this" — so a submission lands PENDING and the public
page reads `status = 'APPROVED'` in the WHERE clause rather than filtering in a
template, because a filter in a template is one `{% for %}` away from being
forgotten.

There are no example testimonials in this file and none in the launch data. An
invented review on a client-facing page is what §1.5 exists to prevent, and it is
the version of that rule people break most easily, because a fake testimonial
feels like placeholder copy rather than a lie about a customer who does not
exist. The page shows an empty state until somebody real writes one.

Moderation is approve or decline with a reason, and a declined row is kept.
Deleting it would lose the fact that we chose not to publish something.
"""
from flask import current_app

from . import mail
from .db import execute, query
from .utils import now_str

KINDS = [
    ("PROBLEM", "Something is broken"),
    ("IDEA", "A suggestion"),
    ("PRAISE", "Something worked well"),
    ("GENERAL", "Something else"),
]
KIND_KEYS = {k for k, _ in KINDS}


# --------------------------------------------------------------------------
# Feedback
# --------------------------------------------------------------------------
def leave_feedback(message, *, name=None, email=None, kind="GENERAL", page=None,
                   user_id=None, customer_id=None):
    """Record it, then try to send it. Returns (row, emailed)."""
    message = (message or "").strip()
    if not message:
        raise ValueError("there is nothing in the message")
    if kind not in KIND_KEYS:
        kind = "GENERAL"

    feedback_id = execute(
        "INSERT INTO feedback (name, email, kind, message, page, user_id, customer_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ((name or "").strip() or None, (email or "").strip().lower() or None, kind,
         message, page, user_id, customer_id))

    label = dict(KINDS).get(kind, kind)
    emailed = False
    try:
        mail.send(
            current_app.config["SUPPORT_EMAIL"],
            f"[Feedback · {label}] {message[:60]}",
            template="feedback",
            name=name or "Someone who did not leave a name",
            email=email or "no address given",
            kind=label, message=message, page=page or "not recorded")
        emailed = True
        execute("UPDATE feedback SET emailed_at = ? WHERE id = ?", (now_str(), feedback_id))
    except Exception as exc:                                       # noqa: BLE001
        # Deliberately swallowed. The person who wrote it should not see an SMTP
        # error, and the row is already saved — `unsent()` is how we find out.
        current_app.logger.error("Feedback %s saved but not emailed: %s", feedback_id, exc)
    return query("SELECT * FROM feedback WHERE id = ?", (feedback_id,), one=True), emailed


def feedback_list(handled=None, limit=200):
    sql = "SELECT * FROM feedback"
    if handled is True:
        sql += " WHERE handled_at IS NOT NULL"
    elif handled is False:
        sql += " WHERE handled_at IS NULL"
    return query(sql + " ORDER BY created_at DESC LIMIT ?", (limit,))


def unsent():
    """Feedback that was saved and never reached anyone's inbox."""
    return query("SELECT * FROM feedback WHERE emailed_at IS NULL ORDER BY created_at DESC")


def mark_handled(feedback_id, by):
    execute("UPDATE feedback SET handled_at = ?, handled_by = ? WHERE id = ?",
            (now_str(), by, feedback_id))


# --------------------------------------------------------------------------
# Testimonials
# --------------------------------------------------------------------------
def submit_testimonial(author_name, email, body, *, author_role=None,
                       company_name=None, customer_id=None):
    author_name = (author_name or "").strip()
    email = (email or "").strip().lower()
    body = (body or "").strip()
    if not author_name or not email or not body:
        raise ValueError("a review needs a name, an email and something written")
    if "@" not in email:
        raise ValueError("that email address does not look right")
    if len(body) < 20:
        raise ValueError("a review that short will not tell anyone anything")

    testimonial_id = execute(
        "INSERT INTO testimonials (author_name, author_role, company_name, email, "
        "body, customer_id) VALUES (?, ?, ?, ?, ?, ?)",
        (author_name, (author_role or "").strip() or None,
         (company_name or "").strip() or None, email, body, customer_id))
    try:
        mail.send(current_app.config["SUPPORT_EMAIL"],
                  f"[Review awaiting approval] {author_name}",
                  template="testimonial",
                  author=author_name, company=company_name or "—",
                  email=email, body=body)
    except Exception as exc:                                       # noqa: BLE001
        current_app.logger.error("Testimonial %s saved but not emailed: %s",
                                 testimonial_id, exc)
    return query("SELECT * FROM testimonials WHERE id = ?", (testimonial_id,), one=True)


def published():
    """What the public page shows. The status filter is in the query, so a
    template cannot forget it and a pending review cannot leak."""
    return query(
        "SELECT * FROM testimonials WHERE status = 'APPROVED' "
        "ORDER BY display_order DESC, decided_at DESC")


def awaiting():
    return query("SELECT * FROM testimonials WHERE status = 'PENDING' "
                 "ORDER BY submitted_at")


def all_testimonials():
    return query("SELECT * FROM testimonials ORDER BY submitted_at DESC")


def approve(testimonial_id, by):
    execute("UPDATE testimonials SET status = 'APPROVED', decided_at = ?, decided_by = ?, "
            "decline_reason = NULL WHERE id = ?", (now_str(), by, testimonial_id))


def decline(testimonial_id, by, reason=None):
    """Kept, not deleted. Choosing not to publish something is a fact worth having."""
    execute("UPDATE testimonials SET status = 'DECLINED', decided_at = ?, decided_by = ?, "
            "decline_reason = ? WHERE id = ?",
            (now_str(), by, (reason or "").strip() or None, testimonial_id))


def unpublish(testimonial_id, by):
    execute("UPDATE testimonials SET status = 'PENDING', decided_at = ?, decided_by = ? "
            "WHERE id = ?", (now_str(), by, testimonial_id))
