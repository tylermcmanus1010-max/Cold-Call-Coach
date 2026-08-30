"""The thing in the corner that answers "where do I find…".

WHAT IT IS, AND WHAT IT IS NOT

It answers from this site's own content — the questions page, the page map, the
membership rules, the disclaimer titles — and every answer carries a link to the
page it came from. It does not have a language model behind it, and the label in
the corner says "Ask a question", not "AI assistant", because it is not one.

That was a decision, not a shortfall, and it is worth stating plainly.

A language model here would answer more fluently and would eventually answer a
question about lead time, or minimum order, or what a run costs. It would be
confident and it would be wrong, and the person reading it would have no way to
tell. This site's whole position is that it does not show a number it cannot
stand behind — a chat box that invents one undoes that in a sentence, and undoes
it in the place a first-time visitor is most likely to look.

So this retrieves. It cannot say anything nobody wrote, because it only ever
returns text that already exists on a page, alongside the link to that page. Ask
it something it has no answer for and it says so and offers a person. That is
less impressive and more useful.

The hook for a model is in `answer()` and deliberately left unconnected — see
`LLM_NOTE`. Connecting it is a decision with a cost, and the cost belongs to
whoever makes it.

HOW THE MATCHING WORKS

Bag-of-words with inverse document frequency, which is old and fits: the corpus
is a few dozen short passages, the vocabulary is this business's own, and a
question is three or four words. Rare words carry the match — "cannabis" or
"tooling" identifies a passage, "the" identifies nothing — and the score is
normalised by question length so a long question is not automatically a better
match than a short one.

Below the floor it returns nothing rather than the least-bad passage. The failure
mode of a search box is not "no results", it is a confident irrelevant one.
"""
import math
import re
from collections import Counter

STRONG = 0.7          # at or above this, answer; below it, say it is only the nearest

LLM_NOTE = (
    "A language model is not connected. The plumbing point is `answer()`: give it "
    "a callable that takes (question, passages) and returns prose, and constrain "
    "that callable to the passages it is handed. Anything that can answer without "
    "them will eventually invent a price."
)

STOP = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "do", "does", "did",
    "i", "you", "we", "they", "it", "my", "your", "our", "me", "us", "them",
    "to", "of", "in", "on", "at", "for", "with", "and", "or", "but", "if", "how",
    "what", "when", "where", "who", "why", "can", "will", "would", "should", "could",
    "have", "has", "had", "get", "got", "there", "this", "that", "these", "those",
    "any", "some", "much", "many", "about", "from", "into", "out", "up", "down",
}

WORD = re.compile(r"[a-z0-9']+")

# The page map. Written here rather than derived from the route table, because
# what a page is FOR is not something a URL knows, and a directory of routes is
# not an answer to "where do I ask for a price".
PAGES = [
    ("Request a quote", "public.quote",
     "Tell us what you want made and we come back with a landed price. Open to "
     "anyone — you do not have to be a member to ask for a quote.",
     "quote price pricing cost estimate landed how much request ask"),
    ("Apply for membership", "public.apply",
     "Membership is what lets you order. You apply, a person reads it, and you "
     "book a call from the times we have open.",
     "apply membership join member application account sign up register consultation call book"),
    ("Catalogue", "public.catalogue_index",
     "What we already make. Members see their own pricing; everyone can look.",
     "catalogue catalog products items browse shop range"),
    ("How it works", "public.how_it_works",
     "The route from a rough description to a shipped run, step by step.",
     "how works process steps stages timeline manufacture production"),
    ("Membership", "public.membership_page",
     "What membership costs, what it includes, and what the request allowance is.",
     "membership cost benefits allowance quota included terms"),
    ("Questions", "public.faq",
     "The questions people ask most, answered.",
     "faq questions help answers support"),
    ("Disclaimers", "public.disclaimers_page",
     "Liability, privacy, and what we can and cannot lawfully make. Each one is "
     "versioned, and accepting one at checkout records which version you read.",
     "disclaimer legal liability terms privacy restricted cannabis alcohol weapons "
     "prohibited lawful law"),
    ("Privacy", "public.privacy",
     "What we hold about you, and what we never sell.",
     "privacy data gdpr personal information hold delete"),
    ("Contact", "public.contact",
     "How to reach a person.",
     "contact email phone reach talk person human speak"),
    ("Feedback", "public.feedback",
     "Tell us what is wrong with the site or the service. It reaches a person.",
     "feedback complain complaint problem bug broken suggestion idea improve"),
    ("Leave a review", "public.testimonials",
     "Write about working with us. Reviews are read and published by a person.",
     "review testimonial rate rating recommend reference"),
    ("Member login", "auth.login",
     "The way in for members.",
     "login sign in account portal password access"),
]


def _tokens(text):
    return [w for w in WORD.findall((text or "").lower()) if w not in STOP and len(w) > 1]


class Index:
    """A small searchable corpus, built once per process from real page content."""

    def __init__(self, passages):
        self.passages = passages
        self.docs = [Counter(_tokens(p["haystack"])) for p in passages]
        n = len(self.docs) or 1
        seen = Counter()
        for d in self.docs:
            seen.update(d.keys())
        # Smoothed IDF. A word in every passage identifies nothing; a word in one
        # identifies that one.
        self.idf = {w: math.log((n + 1) / (c + 1)) + 1.0 for w, c in seen.items()}
        # A word this site has never used is evidence the question is about
        # something else, so it is expensive rather than free. Weighting it at
        # 1.0 — the old default — made "recommend a restaurant" look like a
        # three-quarters match on the reviews page, because the half it missed
        # cost nothing.
        self.unseen = math.log(n + 1) + 1.0

    def search(self, question, limit=3, floor=0.34):
        """Passages that plausibly answer the question, best first, or nothing.

        The score is how much of the question, weighted by how rare its words
        are, this passage accounts for. It is a relevance ordering and NOT a
        confidence: after stop words go, "how do I get a price" is the single
        word "price", so a passage containing it scores 1.0. That is why the
        wording in `answer()` is tiered rather than the threshold being tuned
        until it lies convincingly.

        Below the floor it returns nothing. "do you sell live tigers on
        tuesdays" scores 0.18 against the privacy page on the word "sell"; a
        search box that offers that is worse than one that offers nothing.
        """
        q = set(_tokens(question))
        if not q:
            return []
        weight = sum(self.idf.get(w, self.unseen) for w in q) or 1.0
        scored = []
        for passage, doc in zip(self.passages, self.docs):
            matched = [w for w in q if doc.get(w)]
            if not matched:
                continue
            score = sum(self.idf.get(w, self.unseen) for w in matched) / weight
            if score >= floor:
                scored.append((score, passage))
        scored.sort(key=lambda pair: (-pair[0], pair[1]["title"]))
        return [{**p, "score": round(s, 3)} for s, p in scored[:limit]]


_INDEX = None


def build_index(faqs):
    """Build from the questions page and the page map. Nothing is invented here:
    every passage is text that is already published somewhere."""
    passages = []
    for section, items in faqs:
        for question, answerText, _source in items:
            passages.append({
                "kind": "faq",
                "title": question,
                "body": answerText,
                "endpoint": "public.faq",
                "where": f"Questions · {section}",
                "haystack": f"{section} {question} {answerText}",
            })
    for title, endpoint, blurb, keywords in PAGES:
        passages.append({
            "kind": "page",
            "title": title,
            "body": blurb,
            "endpoint": endpoint,
            "where": "Page",
            "haystack": f"{title} {blurb} {keywords}",
        })
    return Index(passages)


def index(faqs=None):
    global _INDEX
    if _INDEX is None:
        if faqs is None:
            raise RuntimeError("the assistant index has not been built yet")
        _INDEX = build_index(faqs)
    return _INDEX


def reset():
    """Drop the cached index. Only the tests need this."""
    global _INDEX
    _INDEX = None


def answer(question, faqs=None, phrase=None):
    """What to show for a question. Returns {found, reply, hits}.

    `phrase` is the model hook and stays unused unless somebody passes one. If
    they do, it is handed the passages and its output replaces the phrasing —
    never the links, which keep pointing at pages that really say this.
    """
    question = (question or "").strip()
    if not question:
        return {"found": False, "reply": "Ask me where something is and I will "
                                         "point you at the page.", "hits": []}
    hits = index(faqs).search(question)
    if not hits:
        return {
            "found": False,
            "reply": ("I do not have an answer for that. I only know what is already "
                      "written on this site, and I would rather say so than guess. "
                      "A person will answer properly — the contact page has the "
                      "addresses."),
            "hits": [],
        }
    lead = hits[0]
    body = lead["body"] if lead["kind"] == "faq" else f"{lead['title']} — {lead['body']}"
    # Two tiers, and the difference is honesty rather than accuracy. A strong
    # match answers. A weak one says it is the nearest thing rather than
    # dressing a guess as an answer — which is the failure mode that matters
    # here, because a confident wrong answer about price or lead time is exactly
    # what this site spends the rest of its pages not doing.
    if lead["score"] >= STRONG:
        reply = body
    else:
        reply = ("I am not sure I have this one. The nearest thing on the site is "
                 f"\u201c{lead['title']}\u201d — {body} If that is not it, the contact "
                 "page reaches a person.")
    if phrase is not None:
        reply = phrase(question, hits)
    return {"found": True, "reply": reply, "hits": hits}
