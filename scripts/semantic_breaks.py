#!/usr/bin/env python3
"""
Line breaks where a reader would put them, in the films and on the site.

The rule (Warith, 2026-11-06): when a text runs over several lines, the breaks
fall at the seams of its meaning, and this matters most where there is least
room, on a phone. ``text-wrap: balance`` equalises line *lengths* and knows
nothing about meaning: measured the same day across the eleven films, it
wrote ``Sprezzature est un moteur ⏎ d'IA pour le design``, ``It points at the
⏎ wrong line`` and ``and the ⏎ catalogue marks``, each line a fine length and
each break in the middle of a phrase.

Two instruments, at two strengths
---------------------------------
1. **Phrases** are wrapped in ``<span class="ph">``, styled
   ``display: inline-block``. An inline-block is atomic, so the line breaks
   *between* phrases; and it is shrink-to-fit, so a phrase wider than the line
   wraps inside itself instead of overflowing. That is exactly the priority a
   typographer wants: break at a seam if any seam fits, inside a phrase only
   when none does. It holds at every width without knowing the width, which is
   what responsive needs and what no list of fixed ``<br>`` can give.
2. **No-break spaces** inside a phrase hold what must never part at all: a
   short word and the word it introduces (``la·main``, ``of·the·13·tools``), a
   number and its noun, a name and its number (``WCAG·1.4.2``), French tight
   punctuation (``vraiment·:``).

Where the seams are
-------------------
Each gap between two words gets a cost, from the shape of the words alone so
no language has to be passed in (the French and English function words do not
collide):

====  ===========================================================  =========
cost  gap                                                          becomes
====  ===========================================================  =========
0     after a sentence end ``. ! ? …``                              seam
1     after ``, ; : —``                                             seam
2     before a word that opens a phrase (``the``, ``pour``, ``qu'``)  seam
3     before a complement (``of``, ``de``, ``du``, ``d'IA``)          space
4     between two content words (``même façon``, ``AI engine``)     space
5     between two function words (``de chaque``), the last resort   space
∞     after a function word, number→noun, name→number, ``·:``       no-break
====  ===========================================================  =========

A phrase longer than :data:`MAX_WORDS` is cut again at its cheapest inner gap
nearest the middle, so one long clause cannot claim a whole line by itself.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import html
import re

NBSP = " "

#: Words that open a phrase: a break may come before them, never after.
#: Articles, determiners, prepositions, conjunctions, subject pronouns.
OPENERS = frozenset({
    # English
    "a", "an", "the", "to", "in", "on", "at", "for", "by", "with", "from",
    "into", "onto", "over", "under", "about", "as", "and", "or", "but", "nor",
    "than", "that", "this", "these", "those", "their", "our", "your", "my",
    "his", "her", "its", "no", "not", "every", "each", "some", "any", "if",
    "when", "while", "so", "we", "they", "you", "i", "he", "she", "where",
    "which", "who", "what", "how", "why", "before", "after", "without",
    "through", "inside", "between", "against",
    # French
    "le", "la", "les", "un", "une", "des", "au", "aux", "à", "et", "ou",
    "mais", "ni", "que", "qui", "quand", "si", "en", "dans", "par", "pour",
    "sur", "sous", "sans", "avec", "chez", "entre", "vers", "ce", "cet",
    "cette", "ces", "son", "sa", "ses", "leur", "leurs", "mon", "ma", "mes",
    "notre", "nos", "votre", "vos", "il", "elle", "ils", "elles", "on", "je",
    "tu", "nous", "vous", "ne", "se", "y", "comme", "dont", "où", "avant",
    "après", "contre", "depuis", "pendant", "chaque", "aucun", "aucune",
})

#: Words that hang a complement on the noun before them (``a folder of
#: Markdown``, ``167 types de graphiques``): the break before them is a poor
#: one, the break after them is forbidden.
LINKS = frozenset({"of", "de", "du"})

#: Elided French openers, written into the next word: ``l'image``, ``qu'on``.
_ELIDED_OPENER = re.compile(r"^(?:l|qu|n|s|j|c|m|t|jusqu|lorsqu|puisqu)['’]", re.I)
_ELIDED_LINK = re.compile(r"^d['’]", re.I)
#: An elided clitic pair that leans on the verb after it. Listed, not sized:
#: a five-letter ceiling also caught ``l'AEO``, which is an article and a noun.
_CLITIC_SRC = r"^(?:l|qu|n|s|j|c|m|t)['’](?:y|a|ai|as|il|ils|elle|elles|on|en|est|es)$"
_CLITIC = re.compile(_CLITIC_SRC, re.I)

#: A bare number, or a number with a short unit stuck to it.
_NUMBER = re.compile(r"^\d[\d.,]*(?:[A-Za-zµ%°]{1,3})?$")
#: A name that takes a number after it: WCAG 1.4.2, ISO 3166, Python 3.10.
_NAMED_SPEC = re.compile(r"^[A-Z][A-Za-z]{1,9}$")
#: French punctuation that takes a space before it and must not open a line.
_FRENCH_TIGHT = ("»", ":", ";", "!", "?")

#: A phrase longer than either is cut again at its cheapest inner gap, which
#: gives the line a second rank of seams before it falls back to plain spaces.
MAX_WORDS = 6
MAX_CHARS = 28

_STRIP = "«»\"'“”‘’(),;:.!?…—–"
NEVER = 99


def _bare(word: str) -> str:
    return word.strip(_STRIP).lower()


def _kind(word: str) -> str:
    bare = _bare(word)
    if bare in OPENERS or _ELIDED_OPENER.match(word.lstrip("«(\"“")):
        return "opener"
    if bare in LINKS or _ELIDED_LINK.match(word.lstrip("«(\"“")):
        return "link"
    return "content"


def gap_cost(word: str, nxt: str) -> int:
    """The cost of a line break between *word* and *nxt*; see the module table."""
    if nxt in _FRENCH_TIGHT or nxt.startswith(_FRENCH_TIGHT) or word.endswith("«"):
        return NEVER
    if word.endswith((".", "!", "?", "…")):
        return 0
    if word.endswith((",", ";", ":", "—", "–")) or nxt in ("—", "–"):
        return 1
    # The word's own kind, not its elision: ``d'IA`` is a link *and* the
    # noun it introduces, so the gap after it is a content gap.
    if _bare(word) in OPENERS or _bare(word) in LINKS:
        # Two function words in a row (``de chaque``, ``of the``) keep a
        # breakable space between them, priced above every other gap: a chain
        # bound end to end is one unbreakable word, and ``de·chaque·coordonnée.``
        # measured 102 % of the portrait column. Inside a phrase span this
        # break is taken only when the phrase cannot fit a line at all.
        return 5 if _kind(nxt) in ("opener", "link") else NEVER
    # An elided clitic pair leans on the verb after it: ``n'y a``, ``l'a
    # dessiné``, ``qu'il exige``. Without this, the French ``a`` (the verb)
    # read as the English article and opened a phrase: ``n'y ⏎ a pas``.
    if _CLITIC.match(word.strip(_STRIP)):
        return NEVER
    if _NUMBER.match(word) and not _NUMBER.match(nxt.strip(".,;:!?")):
        return NEVER if _kind(nxt) == "content" else 3
    if _NAMED_SPEC.match(word.strip(_STRIP)) and _NUMBER.match(nxt.strip(".,;:!?")):
        return NEVER
    return {"opener": 2, "link": 3}.get(_kind(nxt), 4)


def _cut(words: list[str], costs: list[int]) -> list[tuple[int, int]]:
    """Split ``words[0:n]`` into phrases: (start, end) index pairs."""
    seams = [i + 1 for i, c in enumerate(costs) if c <= 2]
    bounds = [0, *seams, len(words)]
    out: list[tuple[int, int]] = []
    for a, b in zip(bounds, bounds[1:]):
        out.extend(_split_long(a, b, costs, words))
    return out


def _split_long(
    a: int, b: int, costs: list[int], words: list[str] | None = None
) -> list[tuple[int, int]]:
    chars = sum(len(w) + 1 for w in words[a:b]) - 1 if words else 0
    if b - a <= MAX_WORDS and chars <= MAX_CHARS or b - a < 2:
        return [(a, b)]
    inner = [(costs[i], abs((i + 1) - (a + b) / 2), i + 1)
             for i in range(a, b - 1) if costs[i] < NEVER]
    if not inner:
        return [(a, b)]
    _, _, at = min(inner)
    return _split_long(a, at, costs, words) + _split_long(at, b, costs, words)


def phrases(text: str) -> list[str]:
    """Group *text* into phrases, no-break spaces already inside each.

    Examples
    --------
    >>> [p.replace(NBSP, "·") for p in phrases("Sprezzature is an AI engine for Design")]
    ['Sprezzature is', 'an·AI engine', 'for·Design']
    >>> [p.replace(NBSP, "·") for p in phrases("Sprezzature est un moteur d'IA pour le design")]
    ['Sprezzature est', "un·moteur d'IA", 'pour le·design']
    >>> [p.replace(NBSP, "·") for p in phrases("It points at the wrong line, with confidence.")]
    ['It points', 'at the·wrong line,', 'with·confidence.']
    >>> [p.replace(NBSP, "·") for p in phrases("vraiment : non")]
    ['vraiment·:', 'non']
    """
    words = text.split()
    if not words:
        return []
    costs = [gap_cost(w, n) for w, n in zip(words, words[1:])]
    out = []
    for a, b in _cut(words, costs):
        piece = words[a]
        for i in range(a, b - 1):
            piece += (NBSP if costs[i] >= NEVER else " ") + words[i + 1]
        out.append(piece)
    return out


def bind(text: str) -> str:
    """The no-break half alone, for places that cannot hold markup."""
    return " ".join(phrases(text))


def _spans(parts: list[str], cls: str) -> str:
    if len(parts) < 2:
        return "".join(html.escape(p, quote=False) for p in parts)
    return " ".join(f'<span class="{cls}">{html.escape(p, quote=False)}</span>' for p in parts)


def to_html(text: str, cls: str = "ph") -> str:
    """*text* escaped, one ``<span class="ph">`` per phrase.

    Two sentences nest: each sentence is a span holding its phrase spans, so
    the seam between sentences is preferred to any seam inside one. Measured
    on 2026-11-06, balance alone wrote ``or it refuses. There is ⏎ no third
    outcome.``, a fine pair of lengths with the full stop in the wrong place.
    A single phrase gets no span: there is no seam to prefer.

    Examples
    --------
    >>> to_html("a picture")
    'a\\xa0picture'
    >>> to_html("It points at the line.")
    '<span class="ph">It points</span> <span class="ph">at the\\xa0line.</span>'
    """
    sentences: list[list[str]] = [[]]
    for p in phrases(text):
        sentences[-1].append(p)
        if p.endswith((".", "!", "?", "…")):
            sentences.append([])
    sentences = [s for s in sentences if s]
    if len(sentences) < 2:
        return _spans(sentences[0] if sentences else [], cls)
    return " ".join(f'<span class="{cls}">{_spans(s, cls)}</span>' for s in sentences)


#: The stylesheet half. ``.ph-loose`` is set by :data:`FIT_JS`.
CSS = ".ph{display:inline-block}.ph-loose{display:inline}"



# ---------------------------------------------------------------------------
# The site: the same rule, run in the reader's browser
# ---------------------------------------------------------------------------
#: What the site runs. A port of :func:`gap_cost`, :func:`phrases` and
#: :func:`to_html`, generated from this file so the word lists have one home;
#: ``tests/test_the_site_breaks_like_the_films.py`` runs both on the same
#: sentences and requires the same seams.
#:
#: Why at runtime and not written into the pages: a heading stays readable in
#: the source (``<h2>Ce que fait la suite</h2>``, not eight spans), a page
#: edited by hand gets the rule without a build step, and the fit pass needs
#: the real width anyway. Without JavaScript the page is what it was before.
#:
#: Two strengths, by element: display text (headings, captions, summaries,
#: quotes) gets phrase spans; running text (paragraphs, list items, cells)
#: gets the no-break spaces only, and ``text-wrap: pretty`` from the
#: stylesheet does the rest.
_JS = r"""/* Generated by scripts/semantic_breaks.py, do not edit: line breaks where a
   reader would put them. `python3 scripts/semantic_breaks.py --write-js`. */
(function () {
var OPENERS = new Set(%(openers)s), LINKS = new Set(%(links)s);
var STRIP = /^[%(strip)s]+|[%(strip)s]+$/g;
var EL_OPEN = /^(?:l|qu|n|s|j|c|m|t|jusqu|lorsqu|puisqu)['’]/i, EL_LINK = /^d['’]/i;
var CLITIC = /%(clitic)s/i;
var NUM = /^\d[\d.,]*(?:[A-Za-zµ%%°]{1,3})?$/, SPEC = /^[A-Z][A-Za-z]{1,9}$/;
var NB = " ", NEVER = 99, MAX_WORDS = %(max_words)d, MAX_CHARS = %(max_chars)d;
function bare(w) { return w.replace(STRIP, "").toLowerCase(); }
function lead(w) { return w.replace(/^[«("“]+/, ""); }
function kind(w) {
  var b = bare(w);
  if (OPENERS.has(b) || EL_OPEN.test(lead(w))) return "opener";
  if (LINKS.has(b) || EL_LINK.test(lead(w))) return "link";
  return "content";
}
function tight(n) { return /^[»:;!?]/.test(n); }
function trimP(w) { return w.replace(/^[.,;:!?]+|[.,;:!?]+$/g, ""); }
function cost(w, n) {
  if (tight(n) || /«$/.test(w)) return NEVER;
  if (/[.!?…]$/.test(w)) return 0;
  if (/[,;:—–]$/.test(w) || n === "—" || n === "–") return 1;
  var b = bare(w);
  if (OPENERS.has(b) || LINKS.has(b)) return kind(n) === "content" ? NEVER : 5;
  if (CLITIC.test(w.replace(STRIP, ""))) return NEVER;
  if (NUM.test(w) && !NUM.test(trimP(n))) return kind(n) === "content" ? NEVER : 3;
  if (SPEC.test(w.replace(STRIP, "")) && NUM.test(trimP(n))) return NEVER;
  var k = kind(n);
  return k === "opener" ? 2 : k === "link" ? 3 : 4;
}
function splitLong(a, b, c, words) {
  var chars = -1;
  for (var i = a; i < b; i++) chars += words[i].length + 1;
  if ((b - a <= MAX_WORDS && chars <= MAX_CHARS) || b - a < 2) return [[a, b]];
  var best = null;
  for (var j = a; j < b - 1; j++) {
    if (c[j] >= NEVER) continue;
    var key = [c[j], Math.abs((j + 1) - (a + b) / 2), j + 1];
    if (!best || key[0] < best[0] || (key[0] === best[0] && (key[1] < best[1] ||
        (key[1] === best[1] && key[2] < best[2])))) best = key;
  }
  if (!best) return [[a, b]];
  return splitLong(a, best[2], c, words).concat(splitLong(best[2], b, c, words));
}
function phrases(text) {
  var words = text.split(/\s+/).filter(Boolean);
  if (!words.length) return [];
  var c = [], i, out = [];
  for (i = 0; i < words.length - 1; i++) c.push(cost(words[i], words[i + 1]));
  var bounds = [0];
  for (i = 0; i < c.length; i++) if (c[i] <= 2) bounds.push(i + 1);
  bounds.push(words.length);
  for (i = 0; i < bounds.length - 1; i++) {
    splitLong(bounds[i], bounds[i + 1], c, words).forEach(function (r) {
      var p = words[r[0]];
      for (var k = r[0]; k < r[1] - 1; k++) p += (c[k] >= NEVER ? NB : " ") + words[k + 1];
      out.push(p);
    });
  }
  return out;
}
function span(text, kids) {
  var s = document.createElement("span");
  s.className = "ph";
  if (kids) kids.forEach(function (k, i) { if (i) s.appendChild(document.createTextNode(" ")); s.appendChild(k); });
  else s.textContent = text;
  return s;
}
function nodes(ps) {
  if (ps.length < 2) return [document.createTextNode(ps.join(""))];
  return ps.map(function (p) { return span(p); });
}
function build(text) {
  var sentences = [[]];
  phrases(text).forEach(function (p) {
    sentences[sentences.length - 1].push(p);
    if (/[.!?…]$/.test(p)) sentences.push([]);
  });
  sentences = sentences.filter(function (s) { return s.length; });
  if (sentences.length < 2) return nodes(sentences[0] || []);
  return sentences.map(function (s) { return span(null, nodes(s)); });
}
var SKIP = /^(CODE|PRE|KBD|SAMP|SCRIPT|STYLE|TEXTAREA|SVG|MATH|NOSCRIPT)$/;
function texts(el) {
  var out = [], w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, {
    acceptNode: function (n) {
      for (var p = n.parentNode; p && p !== el; p = p.parentNode)
        if (SKIP.test(p.nodeName.toUpperCase()) || (p.classList && p.classList.contains("ph"))) return 2;
      return /\S/.test(n.nodeValue) ? 1 : 2;
    } });
  for (var n; (n = w.nextNode());) out.push(n);
  return out;
}
function apply(el, display) {
  if (el.closest("[data-no-phrases]") || el.dataset.phrased) return;
  el.dataset.phrased = "1";
  texts(el).forEach(function (n) {
    var v = n.nodeValue, head = v.match(/^\s*/)[0], tail = v.match(/\s*$/)[0];
    if (!display) { n.nodeValue = head + phrases(v).join(" ") + tail; return; }
    var f = document.createDocumentFragment();
    if (head) f.appendChild(document.createTextNode(head));
    build(v).forEach(function (k, i) { if (i) f.appendChild(document.createTextNode(" ")); f.appendChild(k); });
    if (tail) f.appendChild(document.createTextNode(tail));
    n.parentNode.replaceChild(f, n);
  });
}
var DISPLAY = "h1,h2,h3,h4,h5,h6,figcaption,summary,blockquote,dt,th,[data-phrases]";
var RUNNING = "p,li,dd,td";
%(fit)s
function run() {
  document.querySelectorAll(DISPLAY).forEach(function (el) { apply(el, true); });
  document.querySelectorAll(RUNNING).forEach(function (el) { apply(el, false); });
  fit();
}
if (typeof document === "undefined") { module.exports = { phrases: phrases }; return; }
var st = document.createElement("style");
st.textContent = "%(css)s";
document.head.appendChild(st);
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run); else run();
if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);
var t; addEventListener("resize", function () { clearTimeout(t); t = setTimeout(fit, 80); });
window.sprezzaturePhrases = { phrases: phrases, apply: apply, fit: fit };
})();
"""

#: The fit pass, shared by the films (:data:`FIT_JS`) and the site script.
_FIT_FN = """function fit() {
  var a = document.querySelectorAll(".ph"), i, e, s, lh;
  for (i = 0; i < a.length; i++) a[i].classList.remove("ph-loose");
  for (i = 0; i < a.length; i++) {
    e = a[i]; s = getComputedStyle(e); lh = parseFloat(s.lineHeight);
    if (!(lh > 0)) lh = parseFloat(s.fontSize) * 1.25;
    if (e.offsetHeight > lh * 1.5) e.classList.add("ph-loose");
  }
}"""

#: The runtime half. An inline-block wider than its line wraps inside itself
#: and then fills whole lines, so its neighbours can no longer share them:
#: measured on 2026-11-06, ``Un WAV, et son WebVTT posé juste à côté.`` went
#: from two lines to four in the square cut. So a phrase that wraps is let go
#: (``display: inline``) and its inner seams take over, outermost first, since
#: ``querySelectorAll`` returns a sentence before the phrases inside it. Run
#: on load, when the fonts arrive (a width measured in the fallback font is a
#: different width), and on resize, which is the case this rule is for.
#: ``offsetHeight`` and not the bounding box: an element mid-animation may be
#: scaled, and a transform is not layout.
FIT_JS = (
    "(function () {\n" + _FIT_FN + "\nfit();\n"
    "if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);\n"
    "var t; addEventListener(\"resize\", function () { clearTimeout(t); t = setTimeout(fit, 80); });\n"
    "})();"
)


#: Links keep their underline through an inline-block: decoration does not
#: propagate into an atomic inline, so it is inherited explicitly.
SITE_CSS = CSS.replace("display:inline-block", "display:inline-block;text-decoration:inherit")


def js() -> str:
    """The site script, from the same tables as the films."""
    import json

    def esc_class(chars: str) -> str:
        return "".join("\\" + c if c in "]\\^-/" else c for c in chars)

    return _JS % {
        "openers": json.dumps(sorted(OPENERS), ensure_ascii=False),
        "links": json.dumps(sorted(LINKS), ensure_ascii=False),
        "strip": esc_class(_STRIP),
        "max_words": MAX_WORDS,
        "clitic": _CLITIC_SRC,
        "max_chars": MAX_CHARS,
        "fit": _FIT_FN,
        "css": SITE_CSS,
    }


if __name__ == "__main__":
    import pathlib
    import sys

    target = pathlib.Path(__file__).resolve().parent.parent / "web/js/phrases.js"
    if "--write-js" in sys.argv:
        target.write_text(js(), encoding="utf-8")
        print(target)
    elif "--check-js" in sys.argv:
        ok = target.is_file() and target.read_text(encoding="utf-8") == js()
        print("in sync" if ok else f"{target} is stale: run --write-js")
        sys.exit(0 if ok else 1)
    else:
        for line in sys.stdin:
            print(" | ".join(p.replace(NBSP, "·") for p in phrases(line)))
