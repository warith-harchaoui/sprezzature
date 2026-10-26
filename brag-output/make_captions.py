#!/usr/bin/env python3
"""Write WebVTT captions for the four films, English and French.

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
        "en": [(0.90, 3.328, "Design is know-how. Most of it is already written down."),
               (4.60, 4.245, "Thirty laws of UX. Contrast ratios. Cited, not guessed."),
               (10.40, 3.733, "Then a model does what no reference can. It looks at what you made."),
               (16.80, 2.283, "The same rules that build the thing audit it."),
               (22.20, 2.731, "Sprezzature. Make it, audit it, then look at it.")],
        "fr": [(0.90, 3.328, "Le design est un savoir-faire. L'essentiel est déjà écrit."),
               (4.60, 4.245, "Trente lois d'UX. Des rapports de contraste. Cités, pas devinés."),
               (10.40, 3.733, "Puis un modèle fait ce qu'aucune référence ne peut : il regarde ce que vous avez fait."),
               (16.80, 2.283, "Les mêmes règles qui fabriquent la chose l'auditent."),
               (22.20, 2.731, "Sprezzature. Fabriquer, auditer, puis regarder.")],
    },
    "colors": {
        "en": [(1.10, 3.179, "Light grey on white reads fine. To you, indoors."),
               (5.50, 4.736, "To a reader with low vision, the text and the background are too close to separate."),
               (11.50, 3.669, "About one man in twelve sees red and green as the same bar."),
               (17.50, 3.669, "So the simulator renders those eyes, from measured matrices."),
               (24.00, 3.733, "Protanopia, deuteranopia, tritanopia, and plain grey."),
               (31.50, 3.989, "The thresholds are the standard's. The matrices are a published paper's."),
               (41.00, 4.139, "It audits every pair, and suggests a fix that stays close to your colour."),
               (49.50, 2.816, "Pure standard library. No network, no model."),
               (55.80, 2.731, "Sprezzature. Make it, audit it, then look at it.")],
        "fr": [(1.10, 3.179, "Un gris clair sur blanc se lit très bien. Pour vous, à l'intérieur."),
               (5.50, 4.736, "Pour un lecteur malvoyant, le texte et le fond sont trop proches pour se séparer."),
               (11.50, 3.669, "Environ un homme sur douze voit le rouge et le vert comme une seule barre."),
               (17.50, 3.669, "Alors le simulateur dessine ces yeux-là, à partir de matrices mesurées."),
               (24.00, 3.733, "Protanopie, deutéranopie, tritanopie, et le gris simple."),
               (31.50, 3.989, "Les seuils viennent de la norme. Les matrices, d'un article publié."),
               (41.00, 4.139, "Il audite chaque paire, et propose une correction qui reste proche de votre couleur."),
               (49.50, 2.816, "Bibliothèque standard pure. Pas de réseau, pas de modèle."),
               (55.80, 2.731, "Sprezzature. Fabriquer, auditer, puis regarder.")],
    },
    "figures-et-cartes": {
        "en": [(0.80, 3.029, "Every figure is written as vector graphics directly."),
               (4.40, 3.840, "A hundred and sixty-seven kinds. Maps on a real projection."),
               (10.90, 2.219, "Rendered, looked at, fixed, then shipped.")],
        "fr": [(0.80, 3.029, "Chaque figure est écrite directement en vectoriel."),
               (4.40, 3.840, "Cent soixante-sept types. Des cartes sur une vraie projection."),
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
}

LINE_LIMIT = 58
# Punctuation keeps its place on the left of a break; a connector word moves to
# the right, so neither half of a split caption reads as a fragment.
AFTER = (". ", ", ", " ; ", " : ", ": ", " — ")
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
