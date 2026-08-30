"""Spanish, without translating anything it must not touch.

Two rules shape every decision in this file, and they pull in opposite
directions from "just translate the page".

    §1.6 / SK-48   Nothing a client wrote may be machine-translated. Their
                   product descriptions, their notes, their company name, the
                   answer they typed into "what do you sell" — all of it stays
                   exactly as they wrote it, in whatever language they wrote it.
                   A translated version of a client's own words is us putting
                   words in their mouth.

    The money rule Currency and financial figures render identically in every
                   locale. A price that reads differently in Spanish is not a
                   translation, it is a different price.

HOW, AND WHY NOT gettext

The usual answer is to wrap 1,113 template literals in `_()`. That is a
mechanical edit across 83 templates, and it puts the protection rules in 1,113
separate places where each one can be got wrong quietly.

Instead the translation happens once, on the rendered HTML, as a token-level
rewrite. `html.parser` walks the output and everything — tags, attributes,
entities, whitespace — is emitted back byte-for-byte EXCEPT text that matches
the catalogue exactly. That makes the guarantee structural rather than
per-string: a thing is translated only if someone wrote a translation for that
exact phrase, so anything nobody translated is unchanged rather than guessed at.

It also makes the money rule checkable. Money never appears in the catalogue as
a bare figure, so `$2,980.00` cannot be rewritten. Where a phrase legitimately
contains a figure — "Under $50k a year" — the catalogue entry must carry the
SAME figure, byte for byte, or this module refuses to load. That is verified at
import, not at render, so a bad entry is a crash on boot and never a wrong
number on a client's screen.

FOUR LAYERS PROTECT CLIENT CONTENT

  1. A text node is translated only on an exact match of a curated phrase. A
     client's sentence is not going to be exactly "Add to order".
  2. Elements carrying client-written fields are marked `data-noloc`, and
     everything inside them is skipped outright.
  3. script, style, code, pre, textarea and their contents are never touched.
  4. Any text carrying a money figure or a reference (MMI-…) is skipped unless
     the translation reproduces those tokens identically.

A41 proves 1, 2 and 4 by seeding a client record whose text IS a catalogue
phrase and asserting it survives.

WHAT IS NOT TRANSLATED, AND SAYS SO

Coverage is partial and stated rather than implied: `coverage()` reports which
visible strings have no Spanish yet. An untranslated phrase renders in English,
which is a visible gap somebody can close — not a silent one.
"""
import html as html_mod
import re
from html.parser import HTMLParser

from flask import g, has_request_context, request, session

LOCALES = {
    "en": ("English", "en"),
    "es": ("Español", "es"),
}
DEFAULT = "en"

# Tags whose contents are never text for a reader.
# `title` is here because a page title routinely carries a client's product
# or company name and, being raw text, cannot hold a data-noloc marker. The
# browser tab stays English; the alternative is translating a client's
# product name into the one place nothing can protect it.
SKIP_TAGS = {"script", "style", "code", "pre", "textarea", "svg", "title"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
             "meta", "param", "source", "track", "wbr"}
# Attributes a reader sees. `value` is handled separately: it is a label on a
# button and client data on an input.
TRANSLATABLE_ATTRS = {"placeholder", "title", "aria-label", "alt"}

# Any figure at all must survive translation untouched — not just the ones
# wearing a currency symbol.
#
# The first version of this matched `$`, `€`, `£`, `¥` and percentages, and
# missed the case that actually matters most often: "from 20,000 units" becoming
# "desde 20.000 unidades". Spanish really does group thousands with a period,
# and a translator doing the right thing by their language quietly changes a
# quantity band. The brief was currency AND any important financial
# information; a quantity a price is quoted against is financial information.
#
# So: every run of digits, with whatever separators are glued to it, has to
# appear identically on both sides.
MONEY = re.compile(r"\d[\d,.\s]*[kKmMbB%]?")
# Our references. MMI-C-1001, MMI-O-2001, MMI-D-001 and so on.
REF = re.compile(r"\bMMI-[A-Z]+-?[\w]*\b")


def _tokens(text):
    """The parts of a string that a translation is not allowed to change."""
    return (tuple(m.group(0) for m in MONEY.finditer(text)),
            tuple(m.group(0) for m in REF.finditer(text)))


from .translations import ES                                        # noqa: E402


def _validate(table, name):
    """Refuse to load a catalogue that would alter a figure or a reference.

    At import, so a bad entry is a crash on boot rather than a wrong number in
    front of a client. There is no runtime path that can reach an unvalidated
    entry — this runs before the first request.
    """
    bad = []
    for source, target in table.items():
        if _tokens(source) != _tokens(target):
            bad.append((source, target))
    if bad:
        lines = "\n".join(f"    {s!r}\n      -> {t!r}" for s, t in bad[:10])
        raise ValueError(
            f"{name}: {len(bad)} entries change a figure or a reference. "
            f"Money and references must appear identically in both languages.\n{lines}")
    return table


CATALOGS = {"es": _validate(ES, "translations.ES")}


def normalise(text):
    return " ".join(text.split())


def available():
    return [(code, label) for code, (label, _) in LOCALES.items()]


def current():
    """The locale for this request: explicit choice, then session, then English.

    Accept-Language is deliberately NOT consulted. A Spanish-speaking buyer in
    a US office gets a page whose language they did not choose, and worse, a
    page whose language changes when they switch machines. The switcher is in
    the footer; the choice is theirs and it sticks.
    """
    # Not every template render happens inside a request. Emails are rendered
    # from `flask` commands and from background paths, and a context processor
    # that reaches for the session there brings the whole render down — which is
    # how a language switcher broke shipping an order.
    if not has_request_context():
        return DEFAULT
    chosen = session.get("locale")
    if chosen in LOCALES:
        return chosen
    return DEFAULT


def set_locale(code):
    if code not in LOCALES:
        return False
    session["locale"] = code
    return True


class _Rewriter(HTMLParser):
    """Emits the document back unchanged except for text the catalogue covers."""

    def __init__(self, table, lang):
        # convert_charrefs=False, and text runs are buffered instead.
        #
        # With it ON, "Packaging &amp; print" arrives whole — which is what a
        # catalogue lookup needs — but the entity spelling is lost, so every
        # untranslated `&#39;` came back as a bare apostrophe and the Spanish
        # page differed from the English one in places nothing had translated.
        #
        # With it OFF the entity spelling survives, but the text arrives in
        # pieces and no multi-word key could ever match.
        #
        # So: off, and the pieces are buffered until a tag boundary. The decoded
        # join is what the catalogue is asked about; the original pieces are what
        # gets emitted when there is no translation. Untranslated text is then
        # byte-identical, and only text somebody actually wrote Spanish for
        # changes at all.
        super().__init__(convert_charrefs=False)
        self.table = table
        self.lang = lang
        self.out = []
        self.skip = 0          # depth inside a region that must not be touched
        self.stack = []        # (tag, contributed_to_skip)
        self.hits = 0
        self.misses = set()
        self.buf = []          # [(raw, decoded)] since the last tag boundary

    # -- text buffering ----------------------------------------------------
    def _flush(self):
        if not self.buf:
            return
        raw = "".join(r for r, _ in self.buf)
        decoded = "".join(d for _, d in self.buf)
        self.buf = []
        if self.skip or not decoded.strip():
            self.out.append(raw)
            return
        new = self._lookup(decoded)
        if new is None:
            self.out.append(raw)
            return
        lead = decoded[:len(decoded) - len(decoded.lstrip())]
        trail = decoded[len(decoded.rstrip()):]
        self.out.append(lead + html_mod.escape(new, quote=False) + trail)
        self.hits += 1

    def _emit(self, text):
        self._flush()
        self.out.append(text)

    # -- helpers -----------------------------------------------------------
    def _lookup(self, text):
        key = normalise(text)
        if not key or not re.search(r"[A-Za-z]", key):
            return None
        value = self.table.get(key)
        if value is None:
            if len(key) > 1:
                self.misses.add(key)
            return None
        # Belt to the import-time braces: never emit a string whose figures or
        # references differ from the source, whatever the catalogue says.
        if _tokens(key) != _tokens(value):
            return None
        return value

    def _rewrite_attrs(self, tag, raw, attrs):
        out = raw
        for name, value in attrs:
            if not value:
                continue
            translatable = name in TRANSLATABLE_ATTRS or (
                name == "value" and tag == "input"
                and dict(attrs).get("type") in ("submit", "button"))
            if not translatable:
                continue
            new = self._lookup(value)
            if new and new != value:
                for quote in ('"', "'"):
                    needle = f'{name}={quote}{value}{quote}'
                    if needle in out:
                        out = out.replace(
                            needle,
                            f'{name}={quote}{html_mod.escape(new, quote=True)}{quote}', 1)
                        self.hits += 1
                        break
        return out

    # -- parser callbacks --------------------------------------------------
    def handle_starttag(self, tag, attrs):
        self._flush()
        raw = self.get_starttag_text() or ""
        lowered = {k.lower(): (v or "") for k, v in attrs}
        blocks = (tag in SKIP_TAGS or "data-noloc" in lowered
                  or lowered.get("translate") == "no")
        if tag == "html":
            raw = re.sub(r'lang="[^"]*"', f'lang="{self.lang}"', raw)
            if "lang=" not in raw:
                raw = raw[:-1] + f' lang="{self.lang}">'
        elif not blocks and self.skip == 0:
            raw = self._rewrite_attrs(tag, raw, attrs)
        self.out.append(raw)
        if tag not in VOID_TAGS:
            self.stack.append((tag, blocks))
            if blocks:
                self.skip += 1

    def handle_startendtag(self, tag, attrs):
        self._flush()
        raw = self.get_starttag_text() or ""
        lowered = {k.lower(): (v or "") for k, v in attrs}
        if self.skip == 0 and "data-noloc" not in lowered:
            raw = self._rewrite_attrs(tag, raw, attrs)
        self.out.append(raw)

    def handle_endtag(self, tag):
        self._flush()
        while self.stack:
            open_tag, blocks = self.stack.pop()
            if blocks:
                self.skip = max(0, self.skip - 1)
            if open_tag == tag:
                break
        self.out.append(f"</{tag}>")

    def handle_data(self, data):
        self.buf.append((data, data))

    def handle_entityref(self, name):
        self.buf.append((f"&{name};", html_mod.unescape(f"&{name};")))

    def handle_charref(self, name):
        self.buf.append((f"&#{name};", html_mod.unescape(f"&#{name};")))

    def handle_comment(self, data):
        self._emit(f"<!--{data}-->")

    def handle_decl(self, decl):
        self._emit(f"<!{decl}>")

    def handle_pi(self, data):
        self._emit(f"<?{data}>")

    def unknown_decl(self, data):
        self._emit(f"<![{data}]>")


def translate_html(html, locale):
    """The rendered page in `locale`. English is returned untouched."""
    table = CATALOGS.get(locale)
    if not table:
        return html, 0, set()
    rewriter = _Rewriter(table, LOCALES[locale][1])
    rewriter.feed(html)
    rewriter.close()
    rewriter._flush()
    return "".join(rewriter.out), rewriter.hits, rewriter.misses


def coverage(html, locale="es"):
    """(translated, untranslated phrases) for one rendered page.

    Reported rather than hidden. A phrase with no Spanish renders in English,
    and this is how someone finds out which ones.
    """
    _, hits, misses = translate_html(html, locale)
    return hits, sorted(misses)


def init_app(app):
    @app.context_processor
    def _inject():
        return {"locale": current(), "locales": available()}

    @app.after_request
    def _translate(response):
        # Only full HTML documents. An HTMX fragment or a CSV export goes
        # through untouched, and so does anything already streamed.
        if response.direct_passthrough:
            return response
        if not response.content_type or "text/html" not in response.content_type:
            return response
        locale = current()
        if locale == DEFAULT:
            return response
        try:
            body = response.get_data(as_text=True)
        except (UnicodeDecodeError, RuntimeError):
            return response
        translated, hits, misses = translate_html(body, locale)
        if hits:
            response.set_data(translated)
        g.locale_misses = misses
        return response
