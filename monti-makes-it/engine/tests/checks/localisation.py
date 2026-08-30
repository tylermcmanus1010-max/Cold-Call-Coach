"""A41 — Spanish for the interface, and nothing else.

Two things must survive a language change untouched, and both are the kind of
thing that breaks silently.

  MONEY AND REFERENCES
  A price that reads differently in Spanish is not a translation, it is a
  different price. Same for MMI- references, SKUs and version hashes: they are
  identifiers, not words. This check renders the same pages in both locales and
  asserts the set of money figures and references is identical — not "looks
  similar", identical.

  WHAT A CLIENT WROTE
  §1.6 / SK-48: nothing a client wrote may be machine-translated. Their product
  name, their specification, their note. A translated version of a client's own
  words is us putting words in their mouth, and the client is the last person
  who would notice.

  The realistic failure is not that a translator translates a paragraph — it is
  a collision. A member names a product "Quality" or "Materials", the catalogue
  has those as interface words, and the exact-match rule that normally protects
  client text now works against it. So this check does exactly that: it renames
  a real product to a phrase that IS in the Spanish catalogue, renders the page
  in Spanish, and asserts the product is still called what the member called it.

The third property is honesty. Coverage is partial, and an untranslated phrase
must render in English rather than being guessed at. `i18n.coverage` reports
what is missing; this check asserts the reporting is real by confirming a phrase
with no entry comes back untranslated and named in the miss list.
"""
import re

from . import Check, Finding

MONEY = re.compile(r"[$€£¥]\s?[\d][\d,.]*")
REF = re.compile(r"\bMMI-[A-Z]+-?[\w]*\b")
# Pages that carry money, references and client-written text between them.
ROUTES = [
    ("public", "/"),
    ("public", "/catalogue"),
    ("public", "/disclaimers"),
    ("member", "/portal/products"),
    ("member", "/portal/products/MMI-D-001"),
    ("member", "/portal/membership"),
    ("member", "/portal/ledger"),
]
# A phrase that IS in the Spanish catalogue as interface language, chosen so it
# does not otherwise appear on the product page. The first version of this check
# used "Materials", which is also one of the six genome section headings — our
# own taxonomy, correctly translated — so the check reported a §1.6 violation
# against a heading nobody had complained about. The assertion below is now on
# the product's own element rather than on the word appearing anywhere.
COLLIDING_NAME = "Talk to a person"


def _client_for(ctx, surface):
    return ctx.member_client if surface == "member" else ctx.public_client


def _fetch(ctx, surface, route, locale):
    client = _client_for(ctx, surface)
    with client.session_transaction() as sess:
        if locale == "en":
            sess.pop("locale", None)
        else:
            sess["locale"] = locale
    return client.get(route, follow_redirects=True).get_data(as_text=True)


def run(ctx):
    from monti import i18n

    findings = []
    with ctx.app.app_context():
        if "es" not in i18n.CATALOGS:
            findings.append(Finding("i18n.CATALOGS", "no Spanish catalogue is loaded"))
            return findings

        # ---- money and references are identical in both languages ---------
        translated_anything = False
        for surface, route in ROUTES:
            english = _fetch(ctx, surface, route, "en")
            spanish = _fetch(ctx, surface, route, "es")
            if english != spanish:
                translated_anything = True

            en_money, es_money = MONEY.findall(english), MONEY.findall(spanish)
            if en_money != es_money:
                only_en = sorted(set(en_money) - set(es_money))
                only_es = sorted(set(es_money) - set(en_money))
                findings.append(Finding(
                    f"{route} (es)",
                    f"the money on this page changed with the language. "
                    f"English only: {only_en[:4]}; Spanish only: {only_es[:4]}"))

            en_ref, es_ref = REF.findall(english), REF.findall(spanish)
            if sorted(en_ref) != sorted(es_ref):
                findings.append(Finding(
                    f"{route} (es)",
                    f"references changed with the language: "
                    f"{sorted(set(en_ref) ^ set(es_ref))[:4]}"))

            if 'lang="es"' not in spanish and "<html" in spanish:
                findings.append(Finding(
                    f"{route} (es)",
                    "served Spanish without saying so — the document still declares "
                    "lang=en, so a screen reader pronounces it as English"))

        if not translated_anything:
            findings.append(Finding(
                "i18n.translate_html",
                "no page changed at all between English and Spanish — the switch "
                "is doing nothing"))

        # ---- a client's words survive a collision --------------------------
        item = ctx.query("SELECT * FROM decision_items WHERE customer_id = ? "
                         "AND ref = 'MMI-D-001'", (ctx.member_customer_id,))
        if item:
            original = item[0]["client_name"]
            ctx.execute("UPDATE decision_items SET client_name = ? WHERE id = ?",
                        (COLLIDING_NAME, item[0]["id"]))
            try:
                spanish = _fetch(ctx, "member", "/portal/products/MMI-D-001", "es")
                translation = i18n.CATALOGS["es"].get(COLLIDING_NAME)
                # Asserted on the protected regions themselves, not on the whole
                # page: a word appearing somewhere proves nothing about whether
                # THIS value was translated.
                protected = re.findall(r"<span data-noloc[^>]*>(.*?)</span>",
                                       spanish, re.DOTALL)
                if translation and any(translation in p for p in protected):
                    findings.append(Finding(
                        "GET /portal/products/MMI-D-001 (es)",
                        f"a product the member named {COLLIDING_NAME!r} was rendered as "
                        f"{translation!r}. §1.6 — their words, not ours, and the member "
                        "is the last person who would notice"))
                if not any(COLLIDING_NAME in p for p in protected):
                    findings.append(Finding(
                        "GET /portal/products/MMI-D-001 (es)",
                        f"the product name {COLLIDING_NAME!r} the member set is not "
                        "rendered in a protected region, so nothing is stopping a "
                        "future catalogue entry from translating it"))
            finally:
                ctx.execute("UPDATE decision_items SET client_name = ? WHERE id = ?",
                            (original, item[0]["id"]))

        # ---- the catalogue itself cannot move a figure ---------------------
        for source, target in i18n.CATALOGS["es"].items():
            if i18n._tokens(source) != i18n._tokens(target):
                findings.append(Finding(
                    "translations.ES",
                    f"{source!r} -> {target!r} changes a figure or a reference"))

        # ---- coverage is reported, not implied ------------------------------
        page = _fetch(ctx, "public", "/how-it-works", "en")
        hits, misses = i18n.coverage(page, "es")
        if hits and not misses:
            findings.append(Finding(
                "i18n.coverage",
                "reports a fully translated page. With 265 entries against a site "
                "this size that is a reporting bug, not a milestone"))
        untranslated = [m for m in misses if m in _fetch(ctx, "public", "/how-it-works", "es")]
        if misses and not untranslated:
            findings.append(Finding(
                "i18n.coverage",
                "lists phrases as untranslated that do not appear on the Spanish "
                "page — the miss report does not describe what is rendered"))
    return findings


def prove(ctx):
    """Three defects: a moved figure, a translated client name, a silent lang."""
    from pathlib import Path

    caught = []
    i18n_src = Path(__file__).resolve().parents[2] / "monti" / "i18n.py"
    trans_src = Path(__file__).resolve().parents[2] / "monti" / "translations.py"

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

    # 1. A catalogue entry that moves a price.
    #
    # This needs TWO edits and the first version only made one: disabling the
    # import guard changes nothing on its own, because the shipped catalogue has
    # no bad entry for the guard to catch. The defect has to be introduced as
    # well as let through, which is also what would really happen — someone adds
    # a translation with the figure "helpfully" localised, and the guard is the
    # only thing between that and a client's screen.
    def attempt_bad_entry(label, matches):
        orig_i18n, orig_trans = i18n_src.read_text(), trans_src.read_text()
        guardless = orig_i18n.replace("    if bad:", "    if False:", 1)
        # An EXISTING entry, with its figure moved the way a translator would
        # move it — Spanish groups thousands with a period, so this is the
        # mistake someone makes by doing their job properly.
        #
        # The first version of this proof appended a second entry with the same
        # key instead of editing the real one. Python keeps the last value in a
        # dict literal, so the correct entry further down overrode the seeded
        # bad one and nothing was ever wrong. A proof that edits a line the
        # program then ignores is not a proof.
        seeded = orig_trans.replace(
            '"from 20,000 units": "desde 20,000 unidades",',
            '"from 20,000 units": "desde 20.000 unidades",', 1)
        assert guardless != orig_i18n and seeded != orig_trans, \
            "proof 1 no longer matches the source"
        i18n_src.write_text(guardless); trans_src.write_text(seeded)
        try:
            ctx.reload()
            hits = [f for f in run(ctx) if matches(f)]
            caught.append((label, bool(hits), str(hits[0]) if hits else "MISSED"))
        finally:
            i18n_src.write_text(orig_i18n); trans_src.write_text(orig_trans)
            ctx.reload()

    attempt_bad_entry("a translation moved a figure",
                      lambda f: "changes a figure" in f.detail
                      or "money on this page changed" in f.detail)

    # 2. Client-written text loses its protection: the marked regions stop being
    #    skipped, so a product named after an interface word gets translated.
    attempt("client-written regions stopped being skipped", i18n_src,
            '        blocks = (tag in SKIP_TAGS or "data-noloc" in lowered\n'
            '                  or lowered.get("translate") == "no")',
            '        blocks = tag in SKIP_TAGS',
            lambda f: "their words, not ours" in f.detail)

    # 3. The page is translated without declaring it.
    attempt("Spanish served as lang=en", i18n_src,
            '            raw = re.sub(r\'lang="[^"]*"\', f\'lang="{self.lang}"\', raw)',
            '            pass',
            lambda f: "still declares" in f.detail)

    missed = [name for name, ok, _ in caught if not ok]
    return (not missed), "; ".join(f"{n} -> {d}" for n, _, d in caught)


CHECKS = [Check("A41", "Spanish translates the interface, never money or a client's words",
                run, prove)]
