#!/usr/bin/env python3
"""
Check film text against the writing charters, in both languages.

The rules come from ``~/ai_dangers/good-writing.md`` and
``~/ai_dangers/bien-ecrire.md``. Those files are the authority and they live
outside this repository; what is encoded here is the mechanical subset, the
part a regular expression settles. Everything else in them is judgement and
stays judgement: whether a sentence earns its place, whether the argument is
written rather than hinted at, whether a sixteen-year-old follows it.

Both charters open on the same instruction, so this script exists before the
rewriting does: measure first. Correcting at random is what you do when you
have no count.

What it catches, and why each one is mechanical
-----------------------------------------------
**Em and en dashes.** Banned outright, in any language. A colon, a semicolon,
a parenthesis or a full stop says the same thing and commits to which.

**Comma followed by "and" / "et".** Tic number one in both charters.

**Opening on a negation.** "Nobody says", "No browser", "None of this": the
charters ask for what a thing is, with the negation following if it still
earns its place. Checked on the first word only, which is where the fault is.

**The reflex antithesis.** "It is not X, it is Y" and its cousins. Once is a
figure; three times is a mould. Counted rather than banned.

**Conference vocabulary and the named tics.** Flat word lists from both
documents: paradigm, ecosystem, lens, at the heart of, to leverage, mordre,
au cœur de, en creux, convoquer.

**Modal density.** Not an error: a location. The charters are explicit that a
raw count confuses senses, and that power and permission keep their modal. So
this reports and never fails.

Usage
-----
    python3 charter.py              # the eleven films, both cuts
    python3 charter.py --strict     # exit 1 on any hard finding

Author
------
Warith HARCHAOUI <warithmetics@deraison.ai>
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

# --- the mechanical rules -------------------------------------------------

DASHES = re.compile(r"[—–]")

COMMA_AND = re.compile(r",\s+(and|et)\b", re.I)

#: First word of a line. A negation here is the fault the charters name; the
#: same word mid-sentence is ordinary and stays.
OPENS_NEGATIVE = re.compile(
    r"^(no|not|nobody|none|nothing|never|neither|without"
    r"|aucun|aucune|personne|rien|jamais|ni|pas\b|sans)\b", re.I
)

ANTITHESIS = re.compile(
    r"\b(is not\s+\w+[,.]\s*it is\b"
    r"|not so much\b|less about\b.{0,40}\bthan about\b"
    r"|n'est pas\s+\w+[,.]\s*c'est\b"
    r"|non pas\b.{0,40}\bmais\b"
    r"|il ne s'agit pas tant\b)", re.I
)

#: Flat lists, lifted from section 6b of each charter.
BANNED_EN = (
    "at the heart of", "at the intersection of", "at the crossroads of",
    "on the cusp of", "beneath the surface", "writ large", "in the age of",
    "lies in", "resides in", "lurk", "rooted in",
    "to bite", "has teeth", "bites",
    "permeate", "suffuse", "crystallize", "coalesce around", "cascade",
    "interrogate", "problematize", "mobilize", "foreground", "unpack",
    "leverage", "to surface", "speak to", "address the", "impact",
    "paradigm", "ecosystem", "lens", "cornerstone", "keystone", "holistic",
    "synergy", "disruptive", "nuanced", "profound", "truly", "deeply",
    "it is important to note", "it is worth noting", "in a world where",
    "now more than ever", "at its core", "ultimately",
    "in the final analysis", "at the end of the day", "key takeaway",
    "pave the way", "shed new light", "bridge the gap", "echo", "resonate",
    "gesture",
)
BANNED_FR = (
    "au cœur de", "à la croisée de", "au croisement de", "à l'orée de",
    "en filigrane", "en creux", "par-delà", "en toile de fond",
    "à géométrie variable", "en demi-teinte",
    "réside dans", "loge dans", "se niche", "habite",
    "mordre", "mordant",
    "irriguer", "infuser", "innerver", "cristallise", "sédimente", "essaimer",
    "convoquer", "interroger", "questionner", "mobiliser", "articuler",
    "adresser", "impacter",
    "paradigme", "écosystème", "prisme", "clé de voûte", "pierre angulaire",
    "approche holistique", "synergie", "disruptif", "à l'ère de",
    "véritable", "fondamentalement", "profondément", "proprement",
    "il est important de noter", "force est de constater", "dans un monde où",
    "à l'heure où", "plus que jamais", "en définitive", "in fine",
    "au fond", "en dernière analyse", "faire écho", "résonner avec",
    "ouvrir la voie", "geste",
)

MODALS_EN = re.compile(r"\b(can|could|may|might|must|should|possible)\b", re.I)
MODALS_FR = re.compile(r"\b(peut|peuvent|pouvoir|possible|doit|doivent|devoir|devrait)\b", re.I)


def findings(text: str, lang: str) -> list[str]:
    """Hard findings for one line. Soft counts are handled by the caller."""
    out = []
    if DASHES.search(text):
        out.append("em/en dash")
    if COMMA_AND.search(text):
        out.append("comma + and/et")
    if OPENS_NEGATIVE.match(text.strip().lstrip("«\"'“ ")):
        out.append("opens on a negation")
    for word in (BANNED_EN if lang == "en" else BANNED_FR):
        if re.search(rf"\b{re.escape(word)}", text, re.I):
            out.append(f"banned: {word!r}")
    return out


def lines_of(spec: dict, lang: str) -> list[tuple[str, str]]:
    """Every user-visible string of one film cut, with where it sits."""
    import build_films

    resolved = build_films.in_language(spec, lang)
    out: list[tuple[str, str]] = []
    for i, sc in enumerate(resolved["scenes"]):
        kind = sc["type"]
        for key in ("line", "caption", "eyebrow", "mark"):
            if sc.get(key):
                out.append((f"s{i} {kind}.{key}", sc[key]))
        for a, b in sc.get("rows", ()):
            out.append((f"s{i} {kind}.row", f"{a}: {b}"))
        for item in sc.get("items", ()):
            out.append((f"s{i} {kind}.chip", item))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 when anything hard is found.")
    parser.add_argument("--narration", action="store_true",
                        help="Check the spoken lines instead of the screen.")
    args = parser.parse_args()

    import build_films
    import make_captions

    hard = 0
    soft = {"antithesis": 0, "modals": 0}
    for film, lang in build_films.cuts():
        spec = build_films.FILMS[film]
        if args.narration:
            pairs = [(f"vo{n}", t) for n, (_s, _d, t)
                     in enumerate(make_captions.FILMS[film][lang], 1)]
        else:
            pairs = lines_of(spec, lang)
        for where, text in pairs:
            for problem in findings(text, lang):
                print(f"  {film}.{lang} {where}: {problem}\n      {text}")
                hard += 1
            if ANTITHESIS.search(text):
                soft["antithesis"] += 1
            soft["modals"] += len(
                (MODALS_EN if lang == "en" else MODALS_FR).findall(text)
            )

    kind = "narration" if args.narration else "on-screen"
    print(f"\n{hard} hard finding(s) in the {kind} text")
    print(f"{soft['antithesis']} reflex antithesis, {soft['modals']} modal(s) "
          f"— both are locations to look at, not verdicts")
    return 1 if (args.strict and hard) else 0


if __name__ == "__main__":
    sys.exit(main())
