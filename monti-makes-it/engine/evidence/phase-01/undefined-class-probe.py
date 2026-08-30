#!/usr/bin/env python3
"""Which CSS classes do the templates emit that the stylesheet never defines?

This exists because the same defect has now been found three times by eye and
never by a test:

  b708710   the stylesheet was replaced wholesale and .chart-bar, .meter,
            .range-btn and six colour tokens stopped existing. Templates kept
            emitting them. SVG fell back to its default black fill and the bar
            charts turned into black slabs. Reported as verified, because what
            was checked was horizontal overflow and console errors — neither of
            which an undefined class produces.
  .prose    the disclaimers page emitted it for running text. Nothing defined
            it, the global reset is p{margin:0}, and three separate legal
            clauses rendered as one run-on paragraph.
  .table    the acceptance table was written with a class this stylesheet has
            never had. It has .data.

An undefined class is silent in a way almost nothing else in a web stack is:
no console error, no failed request, no 404, no exception. The element simply
renders unstyled and looks like a design decision. Finding it needs a probe.

METHOD, and what it can and cannot decide
  - Classes emitted: every class="..." literal in every .html under templates/,
    with Jinja expressions stripped. A class assembled entirely inside {{ }} is
    invisible to this and is reported as a known blind spot, not silently
    skipped.
  - Classes defined: every .name in a selector position in app.css, plus any
    class named in a JS file (classList.add / toggle / a className literal),
    because a class the stylesheet defines for JS to attach is not undefined.
  - The answer is a warning, not a verdict. A class may legitimately exist only
    as a hook. The output lists where each one is emitted so a human can decide.
"""
import json
import re
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2]
TEMPLATES = ENGINE / "monti" / "templates"
CSS = ENGINE / "monti" / "static" / "css"
JS = ENGINE / "monti" / "static" / "js"

# class="..." and class='...'. The value may contain Jinja; that is handled below.
CLASS_ATTR = re.compile(r"""class\s*=\s*["']([^"']*)["']""", re.IGNORECASE)
JINJA = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.DOTALL)
# Stands in for a stripped Jinja expression. No whitespace and no quotes,
# so it stays glued to whatever it was glued to and leaves the attribute
# value's own quoting intact.
MARK = "\u0000JINJA\u0000"
# A class name, found only inside a selector list. The first version of this
# probe used a negative lookbehind to avoid matching decimals like `1.5rem`, and
# that lookbehind also excluded every compound selector: in `table.data` the dot
# is preceded by a word character, so `.data` — defined on line 773 and emitted
# by 45 templates — was reported as undefined. The probe was wrong, not the
# stylesheet. Scanning only the text before each `{` removes the need for the
# lookbehind entirely, because declaration values (where the decimals live) are
# never in a selector.
CSS_CLASS = re.compile(r"\.([A-Za-z_][\w-]*)")
JS_CLASS = re.compile(r"""classList\.(?:add|remove|toggle|contains)\(\s*["']([\w-]+)["']"""
                      r"""|className\s*=\s*["']([\w -]+)["']"""
                      r"""|querySelector(?:All)?\(\s*["'][^"']*?\.([\w-]+)""")


def emitted():
    """{class: [template:line, ...]} plus the attributes we could not fully read.

    Jinja is stripped from the whole file BEFORE class attributes are found, not
    after. Doing it the other way round breaks on the commonest line in this
    codebase — class="{{ 'active' if request.endpoint == 'portal.cart' }}" — where
    the quote inside the expression ends the attribute match early and leaves a
    fragment like `.{{` to be reported as a class. Stripping first means the
    attribute regex only ever sees balanced quotes.
    """
    found, blind = {}, []
    for path in sorted(TEMPLATES.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        # A marker with no whitespace and no quotes, so it stays attached to the
        # stub it replaced and the attribute regex still sees a closed value.
        stripped = JINJA.sub(MARK, text)
        for match in CLASS_ATTR.finditer(stripped):
            raw = match.group(1)
            # Line numbers come from the stripped text; a Jinja block spanning
            # lines would shift them, so count newlines in the ORIGINAL text up
            # to the same offset. The substitution never adds newlines and can
            # only remove them, so the original offset is at least this one —
            # close enough to point a person at the right area, and the file is
            # named alongside it.
            line = stripped[: match.start()].count("\n") + 1
            where = f"{path.relative_to(ENGINE)}:{line}"
            if MARK in raw:
                blind.append((where, raw.strip()))
            for name in raw.split():
                if MARK in name:
                    continue        # half a class name this probe cannot read
                found.setdefault(name, []).append(where)
    return found, blind


def defined():
    names = set()
    for path in sorted(CSS.rglob("*.css")):
        text = path.read_text(encoding="utf-8")
        # Strip comments and url(...) so a word inside either is not read as a
        # selector. This is the class of mistake that made an earlier probe of
        # mine report "none found" over two real hits.
        text = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)
        text = re.sub(r"url\([^)]*\)", " ", text)
        # Selector lists only: everything between the end of one rule and the
        # opening brace of the next.
        for chunk in text.split("}"):
            selector = chunk.split("{", 1)[0]
            if selector.lstrip().startswith("@"):
                # @media / @supports conditions carry no classes, but the rules
                # nested inside them do and arrive as later chunks.
                selector = selector.split(")", 1)[-1]
            names |= set(CSS_CLASS.findall(selector))
    for path in sorted(JS.rglob("*.js")) if JS.exists() else []:
        text = path.read_text(encoding="utf-8")
        for groups in JS_CLASS.findall(text):
            for g in groups:
                names |= set(g.split()) if g else set()
    return names


def main():
    used, blind = emitted()
    have = defined()
    missing = {name: places for name, places in sorted(used.items()) if name not in have}

    print(f"templates scanned : {len(list(TEMPLATES.rglob('*.html')))}")
    print(f"classes emitted   : {len(used)}")
    print(f"classes defined   : {len(have)}  (app.css + JS attachments)")
    print(f"emitted, undefined: {len(missing)}")
    print(f"blind spots       : {len(blind)} class attributes containing Jinja "
          f"(the literal words in them WERE read; a name built entirely inside "
          f"{{{{ }}}} was not)")
    print()
    for name, places in missing.items():
        shown = places[:4]
        more = f"  (+{len(places) - 4} more)" if len(places) > 4 else ""
        print(f"  .{name}")
        for place in shown:
            print(f"      {place}")
        if more:
            print(f"     {more}")
    # -- the blind spot, made legible ------------------------------------
    #
    # `class="flash flash-{{ category }}"` is where this probe is weakest: the
    # literal `flash` is read, and the class that actually carries the colour is
    # not. That is not hypothetical — .flash-error and .flash-ok were both
    # missing from the stylesheet and this probe reported zero undefined classes
    # while every error message on the site rendered as a neutral white card.
    #
    # It cannot be decided automatically: the probe does not know the set of
    # values `category` can take. What it can do is show the prefix and every
    # defined class that starts with it, so a person can see at a glance whether
    # the family is one rule or twelve.
    families = {}
    for where, raw in blind:
        for token in raw.split():
            if MARK in token and not token.startswith(MARK):
                families.setdefault(token.split(MARK)[0], set()).add(where)
    if families:
        print("\ndynamic class families — the prefix is literal, the suffix is not.")
        print("Check each against the values the template can actually produce.")
        for prefix, places in sorted(families.items()):
            siblings = sorted(n for n in have if n.startswith(prefix) and n != prefix)
            print(f"  {prefix}*  defined: {', '.join(siblings) if siblings else 'NOTHING'}")
            for place in sorted(places)[:3]:
                print(f"      {place}")

    out = Path(__file__).with_name("undefined-classes.json")
    out.write_text(json.dumps(
        {"undefined": missing, "blind_spots": blind[:200],
         "dynamic_families": {k: sorted(v) for k, v in sorted(families.items())},
         "counts": {"emitted": len(used), "defined": len(have),
                    "undefined": len(missing), "blind": len(blind)}}, indent=2))
    print(f"\nwritten: {out.relative_to(ENGINE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
