#!/usr/bin/env python3
"""Write WebVTT captions for the five films, English and French.

The text is not transcribed: it is the narration script the Kokoro voice was
generated from, and the timings are the measured start and duration of each
WAV. That is exact where a transcriber would only be close.

Run from brag-output/:  python3 make_captions.py [out-dir]
Default out-dir is ../web/video.
"""

from __future__ import annotations

import pathlib
import sys

# start, duration, text. Durations are the measured lengths of _assets/vo-*.wav.
FILMS: dict[str, dict[str, list[tuple[float, float, str]]]] = {
    "sprezzature": {
        "en": [(0.90, 3.093, "A sentence, you can read back. A picture, you cannot."),
               (4.60, 3.499, "So Sprezzature renders what it drew, then actually looks at it."),
               (12.10, 2.283, "Ten skills, one loop, five ways in."),
               (18.30, 2.261, "It even auditions the model it hires."),
               (22.20, 2.731, "Sprezzature. Make it, audit it, then look at it.")],
        "fr": [(0.90, 3.093, "Une phrase, on peut la relire. Une image, non."),
               (4.60, 3.499, "Alors Sprezzature dessine, puis regarde vraiment le résultat."),
               (12.10, 2.283, "Dix skills, une seule boucle, cinq portes d'entrée."),
               (18.30, 2.261, "Il fait même passer une audition au modèle qu'il emploie."),
               (22.20, 2.731, "Sprezzature. Fabriquer, auditer, puis regarder.")],
    },
    "figures-et-cartes": {
        "en": [(0.80, 3.029, "Every figure is written as vector graphics directly."),
               (4.40, 3.776, "A hundred and twenty-seven kinds. Maps on a real projection."),
               (10.90, 2.219, "Rendered, looked at, fixed, then shipped.")],
        "fr": [(0.80, 3.029, "Chaque figure est écrite directement en vectoriel."),
               (4.40, 3.776, "Cent vingt-sept types. Des cartes sur une vraie projection."),
               (10.90, 2.219, "Rendu, regardé, corrigé, puis livré.")],
    },
    "accessibilite": {
        "en": [(0.80, 3.093, "You cannot see your chart the way a colour blind reader does."),
               (4.40, 3.669, "So the simulator renders those eyes, and the loop looks through them."),
               (13.60, 1.771, "And none of it leaves your machine.")],
        "fr": [(0.80, 3.093, "Vous ne voyez pas votre graphique comme un lecteur daltonien."),
               (4.40, 3.669, "Le simulateur dessine ces yeux-là, et la boucle regarde à travers."),
               (13.60, 1.771, "Et rien de tout cela ne quitte votre machine.")],
    },
    "interface": {
        "en": [(0.80, 2.709, "A command line is a wall. This builds the door."),
               (4.40, 4.245, "Point it at argparse, Click or Typer. Every flag becomes a field."),
               (10.90, 3.541, "Thirty laws of user experience, audited from the source.")],
        "fr": [(0.80, 2.709, "Une ligne de commande est un mur. Ceci en fait une porte."),
               (4.40, 4.245, "Pointez-le sur argparse, Click ou Typer. Chaque option devient un champ."),
               (10.90, 3.541, "Trente lois d'expérience utilisateur, auditées depuis la source.")],
    },
    "moteur-local": {
        "en": [(0.90, 1.323, "Who checks the checker?"),
               (4.50, 2.624, "It picks the strongest model your machine can hold."),
               (10.90, 4.373, "Then seeds a flaw, seeds a defect, and hires only what catches both.")],
        "fr": [(0.90, 1.323, "Qui contrôle le contrôleur ?"),
               (4.50, 2.624, "Il choisit le modèle le plus fort que la machine peut tenir."),
               (10.90, 4.373, "Puis il sème un défaut, puis un défaut visuel, "
                              "et n'engage que ce qui attrape les deux.")],
    },
}

LINE_LIMIT = 58
# Punctuation keeps its place on the left of a break; a connector word moves to
# the right, so neither half of a split caption reads as a fragment.
AFTER = (". ", ", ", " ; ")
BEFORE = (" and ", " et ", " puis ", " then ", " so ", " alors ")


def stamp(t: float) -> str:
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


def split_line(text: str) -> tuple[str, str]:
    mid, best = len(text) / 2, None
    for seps, keep_left in ((AFTER, True), (BEFORE, False)):
        for sep in seps:
            i = text.find(sep)
            while i != -1:
                cut = i + len(sep.rstrip()) if keep_left else i
                if 14 < cut < len(text) - 14:
                    d = abs(cut - mid)
                    if best is None or d < best[0]:
                        best = (d, text[:cut].strip(), text[cut:].strip())
                i = text.find(sep, i + 1)
    if best:
        return best[1], best[2]
    words, run = text.split(), 0
    for k, w in enumerate(words):
        run += len(w) + 1
        if run >= mid:
            return " ".join(words[:k + 1]), " ".join(words[k + 1:])
    return text, ""


def cues(lines):
    out = []
    for start, dur, text in lines:
        if len(text) <= LINE_LIMIT:
            out.append((start, start + dur, text))
            continue
        a, b = split_line(text)
        mid = start + dur * (len(a) / (len(a) + len(b)))
        out += [(start, mid, a), (mid, start + dur, b)]
    return out


def main() -> None:
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "../web/video")
    out.mkdir(parents=True, exist_ok=True)
    for film, langs in FILMS.items():
        for lang, lines in langs.items():
            body = ["WEBVTT", ""]
            for n, (a, b, text) in enumerate(cues(lines), 1):
                body += [str(n), f"{stamp(a)} --> {stamp(b)}", text, ""]
            path = out / f"{film}.{lang}.vtt"
            path.write_text("\n".join(body), encoding="utf-8")
            print(path)


if __name__ == "__main__":
    main()
