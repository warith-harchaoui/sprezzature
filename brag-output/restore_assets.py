#!/usr/bin/env python3
"""Check — and with --fix, rebuild — _assets/, the asset tree the films render from.

git does not track _assets/: a WAV and an MP3 do not delta-compress, so none of
it belongs in a clone. The .gitignore used to claim everything needed to rebuild
the films from nothing stayed tracked. That was not true, and this script is the
audit that says exactly how far it goes.

Three classes, and the distinction is the whole point:

  A. copies of files git DOES track (fonts, figures, maps) — restored here, and
     verified byte-for-byte against their source rather than assumed.
  B. output of a tool that is still on the machine (Kokoro narration, the colour
     vision simulations, the resized logo) — regenerated. The narration comes
     back byte-identical: Kokoro is deterministic for a given text, voice and
     speed, verified against vo-global-3.wav on hyperframes 0.8.60.
  C. neither: a licensed music track, three sound effects, a pinned GSAP build,
     five screen captures. These exist in exactly one place, and if that place
     is a single disk the films are one disk failure from unrenderable. Pass
     --seed to restore them from an off-repo archive.

Run from brag-output/:
    python3 restore_assets.py                    # report only
    python3 restore_assets.py --fix              # restore A and B
    python3 restore_assets.py --fix --seed DIR   # also restore C from an archive
    python3 restore_assets.py --into /tmp/probe  # rebuild elsewhere, touch nothing
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import shutil
import subprocess
import sys
import tarfile

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parent

# ---------------------------------------------------------------------------
# A. Copies of tracked files. Keys are paths inside _assets/, values are paths
#    inside the monorepo. Verified by SHA-256 on 2026-10-02: every pair matched.
# ---------------------------------------------------------------------------
FIGURES = ("alluvial", "bar-grouped", "bellcurve", "calendar-heatmap", "candlestick",
           "chord", "choropleth", "circle-packing", "clustermap", "corr-matrix",
           "map-flow", "sankey")

TRACKED: dict[str, str] = {
    "fonts/Roboto-Variable.woff2": "web/fonts/roboto/Roboto-Variable.woff2",
    "fonts/Roboto-Serif-Variable.woff2": "web/fonts/roboto-serif/Roboto-Serif-Variable.woff2",
    "fonts/Roboto-Mono-Variable.woff2": "web/fonts/roboto-mono/Roboto-Mono-Variable.woff2",
    # Despite the name this is not a desaturated copy: it is byte-identical to
    # bar-grouped.svg. The grey pass happens at render time, in the composition.
    "figures/bar-grouped-gray.svg": "web/img/figures/bar-grouped.svg",
    "figures/kde2d-contour.png": "web/img/figures/kde2d-contour.png",
    "figures/surface3d.png": "web/img/figures/surface3d.png",
    # The films' only two raster maps, and the one figure that is really a map.
    # NOTE: sprezzature-maps is actively changing how situation plates render.
    # When its work lands and web/img/maps/ is regenerated, these two change
    # with it and the five films stop matching the gallery they quote.
    "figures/situation-western-europe.png": "web/img/maps/situation-western-europe.png",
    "maps/situation-western-europe.png": "web/img/maps/situation-western-europe.png",
    "maps/situation-himalaya.png": "web/img/maps/situation-himalaya.png",
    "maps/choropleth-diverging.svg": "web/img/maps/choropleth-diverging.svg",
    "maps/choropleth-sequential.svg": "web/img/maps/choropleth-sequential.svg",
}
TRACKED.update({f"figures/{n}.svg": f"web/img/figures/{n}.svg" for n in FIGURES})

# ---------------------------------------------------------------------------
# B. Reproducible by a tool. Film key -> VO stem prefix; the narration text
#    itself lives in make_captions.py, which git does track, so the script that
#    writes the subtitles and the script that writes the voice cannot drift.
# ---------------------------------------------------------------------------
VO_PREFIX = {"sprezzature": "global", "figures-et-cartes": "figures",
             "accessibilite": "access", "interface": "interface",
             "moteur-local": "engine"}

VOICE, SPEED = "af_heart", "0.95"

CVD = ("00-original.png", "01-protanopia.png", "02-deuteranopia.png",
       "03-tritanopia.png", "04-grayscale.png")

# ---------------------------------------------------------------------------
# C. Nowhere else. Each line says why, because "missing" is useless on its own.
# ---------------------------------------------------------------------------
SEED_ONLY: dict[str, str] = {
    "music/happy-beats-business-moves-vol-12-by-ende-dot-app.mp3":
        "licensed track (ende.app). build_films.py's 42-value BEATS grid is "
        "measured off this file at 109.96 BPM — another track re-times all 15 films",
    "sfx/impact/impactBell_heavy_000.ogg": "registry item; `hyperframes add` refetches over the network",
    "sfx/impact/impactSoft_medium_001.ogg": "idem",
    "sfx/interface/drop_001.ogg": "idem",
    "vendor/gsap.min.js": "CDN-fetchable, but the pinned version is written down nowhere",
    "shots/cli-gui.png":
        "render_html output, but the argparse written for the shot was not kept. "
        "Fields on screen: --kind --input --output --accessibility --title --audit",
    "shots/cli-gui-full.png":
        "same as shots/cli-gui.png, full page at 760x1040 — the argparse that "
        "produced it was not kept either",
    "shots/engine-full.png":
        "full-page recapture of best-engine-ai-helper's GUI — hashes match none "
        "of its assets/screenshots/, so it is a recapture and not a copy",
    "shots/engine-hardware.png": "idem",
    "shots/engine-models.png": "idem",
    "engine-logo.png": "420x420, matches no best-engine-ai-helper icon byte-for-byte",
    "music/cues/happy-beats-business-moves-vol-12-by-ende-dot-app.music-cues.json":
        "derived from the MP3 by `npx hyperframes beats <project>`",
    "music/audio-data.js":
        "derived from the MP3 by hyperframes-creative/scripts/extract-audio-data.py, "
        "3 bands at 30fps, wrapped as window.AUDIO_DATA",
}


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def narration() -> dict[str, str]:
    """VO stem -> the English line it was synthesized from, read from make_captions."""
    sys.path.insert(0, str(ROOT))
    from make_captions import FILMS

    return {f"{VO_PREFIX[film]}-{n}": text
            for film, langs in FILMS.items()
            for n, (_, _, text) in enumerate(langs["en"], 1)}


def restore_tracked(dest: pathlib.Path, fix: bool) -> list[str]:
    """Class A. Copy, then prove the copy equals its tracked source."""
    notes = []
    for rel, src_rel in sorted(TRACKED.items()):
        src, out = REPO / src_rel, dest / rel
        if not src.exists():
            notes.append(f"  MISSING SOURCE  {rel}  <- {src_rel} is not in the repo")
            continue
        if out.exists():
            if sha(out) == sha(src):
                continue
            # Both exist and differ. Never silently overwrite: on this tree that
            # means the gallery was regenerated after the films were cut, and a
            # film now quotes an image the site no longer ships. Say so.
            notes.append(f"  DIVERGED         {rel}\n"
                         f"                     differs from {src_rel}; the film and "
                         f"the gallery no longer show the same image. Decide, do not guess.")
            continue
        if not fix:
            notes.append(f"  would restore    {rel}  <- {src_rel}")
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)
        if sha(out) != sha(src):
            notes.append(f"  COPY MISMATCH    {rel}")
        else:
            notes.append(f"  restored         {rel}  <- {src_rel}")
    return notes


def restore_voice(dest: pathlib.Path, fix: bool) -> list[str]:
    """Class B. Resynthesize the 17 lines with the same voice and speed.

    Kokoro is deterministic: on hyperframes 0.8.60 this returns the exact bytes
    of the original WAVs, checked file by file, so make_captions.py's hard-coded
    durations stay true and the subtitles do not need a pass. Treat that as
    pinned to the version, not as a property of TTS — a model update can move
    the output, and build_films.py re-measures with ffprobe at build time
    (`vo_duration`) precisely so a shift cannot silently desync the films.
    """
    notes = []
    for stem, text in narration().items():
        out = dest / f"vo-{stem}.wav"
        if out.exists():
            continue
        if not fix:
            shown = text if len(text) <= 48 else text[:47] + "…"
            notes.append(f"  would synthesize vo-{stem}.wav  \"{shown}\"")
            continue
        cmd = ["npx", "hyperframes", "tts", text, "--voice", VOICE,
               "--speed", SPEED, "-o", str(out)]
        done = subprocess.run(cmd, capture_output=True, text=True)
        if done.returncode != 0 or not out.exists():
            notes.append(f"  TTS FAILED       vo-{stem}.wav  ({done.stderr.strip()[:120]})")
        else:
            notes.append(f"  synthesized      vo-{stem}.wav")
    if notes and fix:
        notes.append("  check: `cmp` a resynthesized WAV against the archive before trusting "
                     "make_captions.py's durations — they are hard-coded")
    return notes


def restore_derived(dest: pathlib.Path, fix: bool) -> list[str]:
    """Class B, the rest: the 512px logo and the four vision simulations."""
    notes = []
    logo_src, logo_out = REPO / "web/img/logo.png", dest / "logo-512.png"
    if not logo_out.exists():
        if not fix:
            notes.append("  would resize     logo-512.png  <- web/img/logo.png at 512x512")
        else:
            done = subprocess.run(["sips", "-z", "512", "512", str(logo_src),
                                   "--out", str(logo_out)], capture_output=True, text=True)
            notes.append(("  resized          logo-512.png" if logo_out.exists()
                          else f"  RESIZE FAILED    logo-512.png ({done.stderr.strip()[:90]})"))

    sim = pathlib.Path.home() / "sprezzature-colors/scripts/simulate_cvd.py"
    missing = [n for n in CVD if not (dest / "figures/cvd" / n).exists()]
    if missing:
        if not sim.exists():
            notes.append(f"  NO TOOL          figures/cvd/ ({len(missing)} files): {sim} absent")
        else:
            notes.append(f"  run by hand      figures/cvd/ ({len(missing)} files): "
                         f"{sim} on bar-grouped.svg rasterized — Machado matrices")
    return notes


def restore_seed(dest: pathlib.Path, seed: pathlib.Path | None, fix: bool) -> list[str]:
    """Restore everything the archive holds that this tree lacks.

    Runs before A and B deliberately. A backup that only hands back the files
    nothing else can produce is a worse backup than one that hands back all of
    them: resynthesizing the voice costs minutes and shifts every duration, so
    when the archive has a WAV, the archive wins. A and B then fill the gaps.

    With no archive, the class C entries are the ones worth naming — the rest is
    reproducible, and SEED_ONLY says why each of these is not.
    """
    if seed is None:
        return [f"  NO SEED          {r}\n                     why: {SEED_ONLY[r]}"
                for r in sorted(SEED_ONLY) if not (dest / r).exists()]

    if seed.is_dir():
        tars = sorted(seed.rglob("*.tar.gz"))
        if not tars:
            return [f"  no .tar.gz under {seed}"]
        seed = tars[-1]

    notes, taken = [], 0
    with tarfile.open(seed) as tf:
        for m in tf.getmembers():
            name = pathlib.PurePosixPath(m.name).name
            # macOS tar stores xattrs as AppleDouble "._x" siblings. Not assets.
            if (not m.isfile() or name.startswith("._") or name == ".DS_Store"
                    or "_assets/" not in m.name):
                continue
            rel = m.name.split("_assets/", 1)[1]
            out = dest / rel
            if out.exists():
                continue
            if not fix:
                notes.append(f"  would extract    {rel}  <- {seed.name}")
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            with tf.extractfile(m) as fh:
                out.write_bytes(fh.read())
            taken += 1
    if taken:
        notes.append(f"  extracted {taken} files from {seed.name}")
    for rel in sorted(SEED_ONLY):
        if not (dest / rel).exists():
            notes.append(f"  NOT IN SEED      {rel}\n                     why: {SEED_ONLY[rel]}")
    return notes


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fix", action="store_true", help="actually write; default is report only")
    ap.add_argument("--seed", type=pathlib.Path, help="off-repo archive, or a directory of them")
    ap.add_argument("--into", type=pathlib.Path, help="target tree (default _assets/)")
    args = ap.parse_args()

    dest = (args.into or ROOT / "_assets").resolve()
    dest.mkdir(parents=True, exist_ok=True)
    print(f"target: {dest}\n")

    # Seed first: it can supply any class, and a restored WAV beats a resynthesized one.
    for title, notes in (
        ("seed archive", restore_seed(dest, args.seed, args.fix)),
        ("A. copies of tracked files", restore_tracked(dest, args.fix)),
        ("B. Kokoro narration", restore_voice(dest, args.fix)),
        ("B. derived assets", restore_derived(dest, args.fix)),
    ):
        print(title)
        print("\n".join(notes) if notes else "  all present")
        print()

    have = sum(1 for f in dest.rglob("*")
           if f.is_file() and f.name != ".DS_Store" and not f.name.startswith("._"))
    want = len(TRACKED) + 17 + 1 + len(CVD) + len(SEED_ONLY)
    print(f"{have}/{want} files present" + ("" if args.fix else "   (report only; pass --fix)"))


if __name__ == "__main__":
    main()
