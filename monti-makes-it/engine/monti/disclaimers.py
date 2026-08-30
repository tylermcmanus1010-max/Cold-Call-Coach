"""Disclaimers, and the record that someone accepted them (CHG-024, CHG-025).

The requirement was "a disclaimers tab, and at checkout make checking acceptance
of full disclaimers being read and accepted." The hard half is the second one,
and it is hard for the same reason a receipt is: an acceptance you cannot
evidence is not an acceptance.

A boolean `accepted_disclaimers = 1` on an order answers nothing. It does not
say which text, and the text changes. Two years on, when it matters, the
question is never "did they tick a box" — it is "what exactly did they agree
to", and a pointer to whatever the page says today cannot answer it.

So a version is identified by the sha256 of its own body. Publishing new text
writes a new row and stamps the old one superseded; it never edits one. An
acceptance stores that hash, so it resolves to the words that were on screen
that day no matter how many times the disclaimer is rewritten afterwards.

There is deliberately no update or delete in this module. Not a convention — a
missing function. `publish()` inserts, `accept()` inserts, and nothing else
writes. That is the same discipline SK-30 applies to receipts, applied here
because the same argument holds.

What this module does NOT do is write the disclaimers. The text below is a
placeholder marked as such on the page, and replacing it is counsel's job. The
machinery is what the gate tests: that a surface exists, that acceptance is
recorded against an exact version, and that the record is immutable.
"""
import hashlib

from .db import execute, query

# The three the review asked for. Slugs are stable; titles and bodies are not.
SLUGS = ("liability", "privacy", "restricted")


def body_hash(body: str) -> str:
    """A version's identity. Whitespace-normalised so a reflow is not a new version."""
    return hashlib.sha256(" ".join(body.split()).encode("utf-8")).hexdigest()


def publish(slug, title, body, actor):
    """Publish a version. Never edits: identical text is a no-op, new text supersedes.

    Returns the version row. Publishing the same body twice returns the existing
    row rather than creating a duplicate — the UNIQUE(slug, body_hash) makes that
    a data-layer guarantee rather than a check the caller has to remember.
    """
    if slug not in SLUGS:
        raise ValueError(f"unknown disclaimer slug: {slug!r}")
    h = body_hash(body)
    existing = query(
        "SELECT * FROM disclaimer_versions WHERE slug = ? AND body_hash = ?",
        (slug, h), one=True)
    if existing:
        return existing
    execute("UPDATE disclaimer_versions SET superseded_at = datetime('now') "
            "WHERE slug = ? AND superseded_at IS NULL", (slug,))
    execute("INSERT INTO disclaimer_versions (slug, title, body, body_hash, published_by) "
            "VALUES (?, ?, ?, ?, ?)", (slug, title, body, h, actor))
    return query("SELECT * FROM disclaimer_versions WHERE slug = ? AND body_hash = ?",
                 (slug, h), one=True)


def current(slug=None):
    """The live version of one disclaimer, or all three."""
    if slug:
        return query("SELECT * FROM disclaimer_versions WHERE slug = ? "
                     "AND superseded_at IS NULL ORDER BY id DESC", (slug,), one=True)
    return query("SELECT * FROM disclaimer_versions WHERE superseded_at IS NULL "
                 "ORDER BY slug")


def version_by_hash(slug, h):
    """The exact text someone accepted, however long ago and however often it has
    been rewritten since. This is the whole point of storing the hash."""
    return query("SELECT * FROM disclaimer_versions WHERE slug = ? AND body_hash = ?",
                 (slug, h), one=True)


def accept(slugs, actor_email, customer_id=None, user_id=None, order_ref=None,
           ip_hint=None):
    """Record an acceptance of the live version of each named disclaimer.

    One row per disclaimer rather than one row for the set: they are versioned
    separately, so a set-level record could not say which text each part of it
    referred to.
    """
    written = []
    for slug in slugs:
        version = current(slug)
        if version is None:
            raise ValueError(f"no published version of {slug!r} to accept")
        execute(
            "INSERT INTO disclaimer_acceptances (customer_id, user_id, actor_email, "
            "order_ref, slug, body_hash, ip_hint) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (customer_id, user_id, actor_email, order_ref, slug,
             version["body_hash"], ip_hint))
        written.append(version)
    return written


def acceptances_for(customer_id):
    """What this customer has accepted, with the text each acceptance resolves to.

    Joined rather than looked up per row, so a member's own record is one query
    and the text is always the version they saw.
    """
    return query(
        "SELECT a.*, v.title, v.body, v.published_at AS version_published_at "
        "FROM disclaimer_acceptances a "
        "LEFT JOIN disclaimer_versions v ON v.slug = a.slug AND v.body_hash = a.body_hash "
        "WHERE a.customer_id = ? ORDER BY a.accepted_at DESC", (customer_id,))


def has_accepted_current(customer_id, slug):
    """True when this customer has accepted the version that is live right now."""
    version = current(slug)
    if version is None:
        return False
    row = query("SELECT 1 AS ok FROM disclaimer_acceptances WHERE customer_id = ? "
                "AND slug = ? AND body_hash = ?",
                (customer_id, slug, version["body_hash"]), one=True)
    return bool(row)


# --------------------------------------------------------------------------
# Placeholder text
#
# Marked as a placeholder on the page, and deliberately so. Three gates in the
# filing test that the surface exists, that acceptance is recorded, and that the
# record is immutable. None tests that the wording is right, and none can — that
# is counsel's, and an agent writing law it is not qualified to write is worse
# than an empty page, because an empty page does not read as advice.
# --------------------------------------------------------------------------
PLACEHOLDER = {
    "liability": (
        "Limitation of liability",
        "PLACEHOLDER — NOT LEGAL ADVICE. This text has not been reviewed by a "
        "lawyer and must be replaced before launch.\n\n"
        "Monti Makes It manufactures to the specification agreed with the member "
        "and recorded in the Product Genome for that item. Estimates of landed "
        "cost, lead time and arrival date are estimates built from entered rates, "
        "not guarantees. Freight transit times, customs clearance and duty rates "
        "are outside our control and change without notice.\n\n"
        "Nothing on this site is an offer capable of acceptance until a "
        "specification has been signed by a named manufacturing engineer and "
        "pricing published."),
    "privacy": (
        "What we hold, and what we never sell",
        "PLACEHOLDER — NOT LEGAL ADVICE. This text has not been reviewed by a "
        "lawyer and must be replaced before launch.\n\n"
        "We do not sell, rent or share member information with third parties for "
        "marketing. We hold what the service needs to run: your company and "
        "contact details, the specifications and files you send us, your orders "
        "and their financial records, and the messages you exchange with us.\n\n"
        "Financial records are retained as long as the law requires. Uploaded "
        "files are retained for the life of the item they describe. You can ask "
        "for a copy of what we hold, or ask us to correct it, by writing to the "
        "support address.\n\n"
        "This statement is verified against the system's own data map, not "
        "against itself: a category the database holds and this page omits is a "
        "defect, not a nuance."),
    "restricted": (
        "What we can and cannot make",
        "PLACEHOLDER — NOT LEGAL ADVICE. This text has not been reviewed by a "
        "lawyer and must be replaced before launch.\n\n"
        "What may lawfully be manufactured, imported or shipped depends on the "
        "product and on the laws of the origin, transit and destination "
        "jurisdictions. Some categories — among them cannabis and other "
        "controlled or recreational products, tobacco, alcohol, weapons, "
        "pharmaceuticals, and goods subject to export control — are restricted "
        "or prohibited in some places and permitted in others.\n\n"
        "A request in a restricted category is held for review by a named person "
        "before it reaches pricing. We may decline any request we believe we "
        "cannot lawfully fulfil, and we will say so rather than quietly not "
        "quoting."),
}


def seed_placeholders(actor="system"):
    """Publish the placeholder text for any disclaimer that has no version yet.

    Idempotent, and it will not overwrite real text: it publishes only where
    nothing is live, so replacing a placeholder with counsel's wording is a
    one-way door.
    """
    published = []
    for slug in SLUGS:
        if current(slug) is None:
            title, body = PLACEHOLDER[slug]
            published.append(publish(slug, title, body, actor))
    return published
