#!/usr/bin/env python3
"""
name_from_transcript
====================

Guess **who is who** from a speaker-diarized transcript. Two passes:

1. **Rule pass** — regex over the transcript picks up two well-studied
   patterns:

   * **Self-introduction** — the current speaker names themselves
     ("I'm Alice", "my name is Bob", "this is Charlie speaking",
     "je suis Alice", "je m'appelle Bob").
   * **Vocative addressing** — the current speaker addresses the
     *other* speaker by name at the beginning or end of a turn
     ("Hey Mary, …", "Thanks, John.", "…, don't you think, Sam?").

   Each candidate carries a confidence score (higher = more direct
   evidence). Multiple speakers, the same name, or contradictory
   evidence within one conversation are all resolved by picking the
   highest-confidence attribution per speaker id.

2. **LLM pass** — optional; runs only when ``--ollama`` is passed or
   ``OLLAMA_URL`` is reachable. Sends a compact JSON prompt to a local
   Ollama daemon and expects a JSON mapping in return. Same fixed
   model / URL as :mod:`alt_from_ollama` (``qwen3-vl:8b``, the one
   authorized LLM, + ``http://localhost:11434``). The model is not
   selectable; ``OLLAMA_MODEL`` remains only as a test seam.

Whichever pass returns the higher-confidence label per speaker wins.

Prior art
---------

Speaker-naming from dialogue text is a small but real subfield:

* Bäuml, Tapaswi, & Stiefelhagen — *Person naming with automatically
  discovered contextual clues* (CVPR 2013). Combines face, audio,
  and subtitle patterns very similar to the rule pass here.
* Nagrani, Cole, Zisserman — *"From Benedict Cumberbatch to Sherlock
  Holmes": Character identification in TV series without a script*
  (BMVC 2017).
* Vocative detection is a first-class task in modern dialogue NLP —
  see e.g. Zhang et al. 2022, *Vocative case prediction in conversational
  agents*.

The pipeline here is the same idea, minus faces and any hosted call.

Inputs
------

* A **speaker-attributed** transcript. Either:

  * a ``*.speakers.vtt`` / ``*.speakers.srt`` from :mod:`caption_diarize`, or
  * a WebVTT / SRT emitted by :mod:`captions_from_whisper` **plus** a
    ``diarization.json`` from :mod:`diarize_from_nemo` (the script
    merges them in-memory using the same rule as ``caption_diarize``).

Output
------

* ``*.speakers.json`` — the same shape :mod:`identify_from_titanet`
  writes, so :mod:`caption_diarize` picks it up unchanged.

Usage
-----
::

    # Rule pass only (fast, offline, no LLM required)
    python name_from_transcript.py interview.speakers.vtt \\
        --out interview.speakers.json

    # Rule pass + LLM refinement via local Ollama
    python name_from_transcript.py interview.speakers.vtt --ollama \\
        --out interview.speakers.json

    # From an un-merged pair (captions + diarization)
    python name_from_transcript.py interview.vtt \\
        --diarization interview.diarization.json \\
        --ollama --out interview.speakers.json

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from pathlib import Path as _PathHelper
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(_PathHelper(__file__).resolve().parent))
from _click import sprezzature_command, run_command  # noqa: E402
from caption_diarize import (  # noqa: E402
    attribute_speakers,
    parse_caption_cues,
)

import click
from sprezzature_local.llm import chat as _llm_chat


# ── Configuration ──────────────────────────────────────────────────────────

#: Default local Ollama endpoint (same as :mod:`alt_from_ollama`).
DEFAULT_OLLAMA_URL: str = os.environ.get("OLLAMA_URL", "http://localhost:11434")

#: Default vision/text-friendly Ollama base tag.
#: The one authorized model: qwen3-vl:8b (via Ollama). No other tag, no MLX.
DEFAULT_OLLAMA_MODEL: str = "qwen3-vl:8b"

#: Names shorter than this are usually stopwords (Al, Ed, Jo). Not banned
#: outright — the rule pass just requires stronger evidence.
SHORT_NAME_LEN: int = 3

#: Explicit stoplist of frequent capitalised English + French non-names
#: that trip the vocative regex.
STOPWORDS: frozenset[str] = frozenset({
    "I", "You", "He", "She", "We", "They", "It",
    "The", "A", "An", "Yes", "No", "OK", "Okay", "So", "Well", "Now",
    "Hi", "Hey", "Hello", "Thanks", "Thank", "Sorry", "Please",
    "God", "Jesus", "Christ", "Lord",
    "January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
    "Saturday", "Sunday",
    # French leakage
    "Je", "Tu", "Il", "Elle", "Nous", "Vous", "Ils", "Elles", "On",
    "Le", "La", "Les", "Un", "Une", "Des", "Bonjour", "Merci", "Oui", "Non",
})

# Confidence buckets (larger = stronger evidence).
CONF_SELF_INTRO: float = 0.95
CONF_VOCATIVE_START: float = 0.75
CONF_VOCATIVE_END: float = 0.65
CONF_LLM_HIGH: float = 0.90
CONF_LLM_LOW: float = 0.60


# ── Rule pass ──────────────────────────────────────────────────────────────

# "I'm Alice", "I am Alice", "my name is Alice", "this is Alice", "je suis Alice",
# "je m'appelle Alice", "moi c'est Alice"
_SELF_INTRO_RE = re.compile(
    r"(?:"
    r"\b(?:I am|I'm|my name is|this is|it's|call me|the name is)\s+"
    r"|\bje\s+suis\s+|\bje\s+m['’]appelle\s+|\bmoi\s+c['’]est\s+"
    r")"
    r"(?P<name>[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ]+(?:\s+[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ]+)?)",
    re.IGNORECASE,
)

# Turn-initial vocative: "Hey Mary", "Hi John,", "Thanks, Sam", "Bonjour Marie"
_VOCATIVE_START_RE = re.compile(
    r"^\s*(?:hey|hi|hello|thanks?|thank you|sorry|please|listen|look|well|so|"
    r"bonjour|salut|merci|s[’']il\s+te\s+pla[iî]t|dis|écoute|regarde)[,!\s]+"
    r"(?P<name>[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ]+(?:\s+[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ]+)?)"
    r"[,.!?…]",
    re.IGNORECASE,
)

# Turn-final vocative: "..., don't you think, Sam?"
_VOCATIVE_END_RE = re.compile(
    r",\s+(?P<name>[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ]+(?:\s+[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ]+)?)\s*[.!?…]?\s*$"
)


def _clean_name(raw: str) -> Optional[str]:
    """Strip stopwords / trailing punctuation; return None if unusable."""
    name = raw.strip(" .,;:!?…\"'").split()[0]  # keep first word for a Firstname bias
    if not name or name.title() in STOPWORDS:
        return None
    if len(name) < SHORT_NAME_LEN:
        return None
    return name[:1].upper() + name[1:]


def _run_rule_pass(cues: List[Dict[str, Any]]) -> Dict[str, List[Tuple[str, float]]]:
    """Score name candidates from self-introductions and vocatives.

    Parameters
    ----------
    cues : list of dict
        Speaker-attributed caption cues (from
        :func:`caption_diarize.attribute_speakers`).

    Returns
    -------
    dict of str to list of (str, float)
        For each anonymous speaker id, a list of ``(name, confidence)``
        candidates. Ready for :func:`_pick_best`.
    """
    candidates: Dict[str, List[Tuple[str, float]]] = {}

    def add(spk: str, name: Optional[str], conf: float) -> None:
        """Append a ``(name, confidence)`` candidate for a speaker, skipping empties."""
        if not name:
            return
        candidates.setdefault(spk, []).append((name, conf))

    for i, cue in enumerate(cues):
        text = cue["text"]
        spk = str(cue.get("speaker_id", cue.get("speaker")))

        # Self-introduction: current speaker names themselves.
        for m in _SELF_INTRO_RE.finditer(text):
            add(spk, _clean_name(m.group("name")), CONF_SELF_INTRO)

        # Turn-initial vocative: addressed to the OTHER speaker.
        # We attribute to the previous non-self speaker id when present;
        # otherwise the next different speaker id.
        vm = _VOCATIVE_START_RE.match(text)
        if vm:
            target = _find_other_speaker(cues, i, spk)
            add(target, _clean_name(vm.group("name")), CONF_VOCATIVE_START)

        # Turn-final vocative: also addressed to the OTHER speaker.
        em = _VOCATIVE_END_RE.search(text)
        if em:
            target = _find_other_speaker(cues, i, spk)
            add(target, _clean_name(em.group("name")), CONF_VOCATIVE_END)

    return candidates


def _find_other_speaker(cues: List[Dict[str, Any]], idx: int, current: str) -> str:
    """Return the id of the nearest OTHER speaker around cue ``idx``.

    Vocatives address the interlocutor, so we look forward first (the
    next speaker after this turn), then backward.

    Parameters
    ----------
    cues : list of dict
        Speaker-attributed cues.
    idx : int
        Index of the vocative-carrying cue.
    current : str
        The current speaker id (the one uttering the vocative).

    Returns
    -------
    str
        Nearest other speaker id, or ``current`` if the transcript has
        no other speakers within the window.
    """
    for j in range(idx + 1, min(len(cues), idx + 4)):
        spk = str(cues[j].get("speaker_id", cues[j].get("speaker")))
        if spk != current:
            return spk
    for j in range(idx - 1, max(-1, idx - 4), -1):
        spk = str(cues[j].get("speaker_id", cues[j].get("speaker")))
        if spk != current:
            return spk
    return current


def _pick_best(candidates: Dict[str, List[Tuple[str, float]]]) -> Dict[str, Tuple[str, float]]:
    """Collapse candidate lists into one ``(name, confidence)`` per speaker.

    Strategy: sum confidences per (speaker, name) so recurrences boost
    the score; keep the highest.

    Parameters
    ----------
    candidates : dict of str to list of (str, float)
        Output of :func:`_run_rule_pass` or the LLM pass.

    Returns
    -------
    dict of str to (str, float)
        One winning name per speaker id.
    """
    picked: Dict[str, Tuple[str, float]] = {}
    for spk, items in candidates.items():
        scores: Dict[str, float] = {}
        for name, conf in items:
            scores[name] = scores.get(name, 0.0) + conf
        best_name, best_score = max(scores.items(), key=lambda kv: kv[1])
        picked[spk] = (best_name, best_score)
    return picked


# ── LLM pass (local Ollama, optional) ──────────────────────────────────────

def _reachable(url: str) -> bool:
    """Return True when the Ollama daemon responds to ``/api/tags``."""
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/api/tags", timeout=1.5) as fh:
            return fh.status == 200
    except Exception:  # noqa: BLE001
        return False


def _resolve_ollama_model(base: str) -> str:
    """Return the model tag to send: the ``OLLAMA_MODEL`` override, else ``base``.

    ``base`` defaults to the registry-standard ``qwen3-vl:8b`` (pullable on any
    box). No ``-mlx`` auto-suffix — that only named a maintainer-local build.
    """
    return os.environ.get("OLLAMA_MODEL", "").strip() or base


def _build_transcript_excerpt(cues: List[Dict[str, Any]], max_cues: int = 120) -> str:
    """Render a compact transcript for the LLM prompt.

    Parameters
    ----------
    cues : list of dict
        Speaker-attributed cues.
    max_cues : int, optional
        Cap to keep the prompt under the model's context window. The
        first ``max_cues`` cues usually contain the introductions;
        vocatives that come later are also common but rarer.

    Returns
    -------
    str
        A ``"Speaker X: text"`` transcript, one turn per line.
    """
    slice_ = cues[:max_cues]
    lines: List[str] = []
    for cue in slice_:
        if not cue["text"]:
            continue
        spk = cue.get("speaker_id", cue.get("speaker"))
        lines.append(f"Speaker {spk}: {cue['text']}")
    return "\n".join(lines)


def _llm_pass(
    cues: List[Dict[str, Any]],
    *,
    url: str,
    model: str,
    seed_names: Dict[str, Tuple[str, float]],
) -> Dict[str, Tuple[str, float]]:
    """Ask a local Ollama model to name the speakers.

    Parameters
    ----------
    cues : list of dict
        Speaker-attributed cues.
    url : str
        Ollama endpoint (``http://localhost:11434``).
    model : str
        Model tag to send.
    seed_names : dict of str to (str, float)
        Rule-pass output. Passed as a hint so the model biases toward
        the same names when they are already plausible.

    Returns
    -------
    dict of str to (str, float)
        LLM-derived candidates.
    """
    speaker_ids = sorted({str(c.get("speaker_id", c.get("speaker"))) for c in cues})
    transcript = _build_transcript_excerpt(cues)

    system = (
        "You infer speaker names from a diarized conversation transcript. "
        "Look for self-introductions (\"I'm Alice\", \"my name is Bob\", "
        "\"je m'appelle Sam\") and vocatives (\"Hey Mary, ...\", "
        "\"Thanks, John\"). Return STRICT JSON only — no prose, no markdown. "
        "Return an object where each key is a speaker id from the input and "
        "each value is either the inferred human first name (title-cased) "
        "or the speaker id verbatim when the transcript has no clear "
        "evidence. Never invent a name."
    )
    user_payload = {
        "speakers": speaker_ids,
        "rule_pass_hint": {spk: name for spk, (name, _) in seed_names.items()},
        "transcript": transcript,
    }
    body = {
        "model": model,
        "system": system,
        "prompt": json.dumps(user_payload, ensure_ascii=False),
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.0, "num_ctx": 8192},
    }
    try:
        raw = str(_llm_chat(
            json.dumps(user_payload, ensure_ascii=False),
            system=system,
            model=model,
        )).strip()
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] Ollama call failed: {exc}", file=sys.stderr)
        return {}
    try:
        mapping = json.loads(raw)
    except json.JSONDecodeError:
        # Some Ollama backends still wrap the JSON in ``\n\n``; be forgiving.
        m = re.search(r"\{[^{}]+\}", raw, re.DOTALL)
        if not m:
            return {}
        try:
            mapping = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {}

    picked: Dict[str, Tuple[str, float]] = {}
    for spk in speaker_ids:
        name = mapping.get(spk, "")
        if not isinstance(name, str) or not name.strip() or name.strip() == spk:
            continue
        clean = _clean_name(name)
        if clean is None:
            continue
        # Confidence: high if the LLM agrees with the rule pass; low otherwise.
        conf = CONF_LLM_HIGH if seed_names.get(spk, ("", 0.0))[0] == clean else CONF_LLM_LOW
        picked[spk] = (clean, conf)
    return picked


# ── Merge passes ───────────────────────────────────────────────────────────

def _merge(*passes: Dict[str, Tuple[str, float]]) -> Dict[str, str]:
    """Pick the highest-confidence name per speaker across passes.

    Parameters
    ----------
    *passes : dict of str to (str, float)
        Any number of ``{speaker_id: (name, confidence)}`` maps.

    Returns
    -------
    dict of str to str
        Speaker id → final name (or the id itself when no pass supplied
        a name).
    """
    all_speakers: set[str] = set()
    for p in passes:
        all_speakers.update(p.keys())

    final: Dict[str, str] = {}
    for spk in all_speakers:
        best_name = spk
        best_conf = -1.0
        for p in passes:
            if spk in p:
                name, conf = p[spk]
                if conf > best_conf:
                    best_name = name
                    best_conf = conf
        final[spk] = best_name
    return final


# ── CLI ────────────────────────────────────────────────────────────────────

@sprezzature_command(
    "sprezzature-audio-name",
    help=(
        "Guess speaker names from a diarized transcript using self-"
        "introduction + vocative patterns and, optionally, a local "
        "Ollama pass. Writes the same speakers.json identify_from_titanet "
        "produces, so caption_diarize consumes it unchanged."
    ),
    epilog=(
        "Examples:\n"
        "  sprezzature-audio-name interview.speakers.vtt --out interview.speakers.json\n"
        "  sprezzature-audio-name interview.vtt --diarization interview.diarization.json --ollama\n"
    ),
)
@click.argument("transcript", type=click.Path(path_type=Path))
@click.option("--diarization", "diarization_path", type=click.Path(path_type=Path), default=None,
              help="Diarization JSON. Only needed when the transcript is not already "
                   "speaker-attributed (i.e. not a *.speakers.vtt from caption_diarize).")
@click.option("--out", type=click.Path(path_type=Path), default=None,
              help="Output speakers.json. Default: sibling '<stem>.speakers.json'.")
@click.option("--ollama", "use_ollama", is_flag=True, default=False,
              help="Run the LLM refinement pass via local Ollama.")
@click.option("--url", "ollama_url", default=DEFAULT_OLLAMA_URL, show_default=True,
              help="Ollama endpoint URL.")
def _cli(
    transcript: Path,
    diarization_path: Optional[Path],
    out: Optional[Path],
    use_ollama: bool,
    ollama_url: str,
) -> int:
    """Click command body; returns an int exit code."""
    if not transcript.is_file():
        click.echo(f"No such file: {transcript}", err=True)
        return 1

    cues = parse_caption_cues(transcript.read_text(encoding="utf-8"))

    if diarization_path is not None:
        if not diarization_path.is_file():
            click.echo(f"No such file: {diarization_path}", err=True)
            return 1
        turns = json.loads(diarization_path.read_text(encoding="utf-8"))
        cues = attribute_speakers(cues, turns)
    else:
        # If the caller passed an already-speaker-attributed VTT
        # (from caption_diarize) the ``<v Name>`` tag has been stripped
        # by parse_caption_cues — we need to re-attach it as speaker_id.
        # The lightweight assumption: whatever was in the <v ...> tag
        # in the original text is the speaker.
        raw = transcript.read_text(encoding="utf-8")
        cues = _repopulate_speaker_ids(cues, raw)

    rule_candidates = _run_rule_pass(cues)
    rule_final = _pick_best(rule_candidates)

    llm_final: Dict[str, Tuple[str, float]] = {}
    if use_ollama and _reachable(ollama_url):
        # The model is fixed at qwen3-vl:8b (the one authorized LLM); not a CLI
        # knob. ``OLLAMA_MODEL`` remains only as a test seam.
        resolved_model = _resolve_ollama_model(DEFAULT_OLLAMA_MODEL)
        print(f"→ Refining with Ollama ({resolved_model} @ {ollama_url})…", file=sys.stderr)
        llm_final = _llm_pass(cues, url=ollama_url, model=resolved_model, seed_names=rule_final)
    elif use_ollama:
        print(f"[warn] Ollama not reachable at {ollama_url}; skipping LLM pass.", file=sys.stderr)

    final = _merge(rule_final, llm_final)

    # Any speaker not touched by either pass keeps its anonymous id.
    for spk in {str(c.get("speaker_id", c.get("speaker"))) for c in cues}:
        final.setdefault(spk, spk)

    out_path = out or Path(str(transcript.with_suffix("")) + ".speakers.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(final, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    click.echo(f"→ Wrote {out_path}")
    for spk, name in sorted(final.items()):
        marker = "✓" if name != spk else "•"
        click.echo(f"  {marker} {spk} → {name}")
    return 0


_VOICE_TAG_RE = re.compile(r"<v\s+(?P<name>[^>]+)>")


def _repopulate_speaker_ids(cues: List[Dict[str, Any]], raw_text: str) -> List[Dict[str, Any]]:
    """Best-effort recovery of speaker ids from a ``*.speakers.vtt`` file.

    Parameters
    ----------
    cues : list of dict
        Parsed cues (voice tags already stripped by
        :func:`caption_diarize.parse_caption_cues`).
    raw_text : str
        The original VTT text — we scan it for the ``<v ...>`` tags in
        cue order and re-attach the name as both ``speaker`` and
        ``speaker_id``.

    Returns
    -------
    list of dict
        Cues with ``speaker_id`` / ``speaker`` restored where possible.
    """
    names_in_order = [m.group("name").strip() for m in _VOICE_TAG_RE.finditer(raw_text)]
    if not names_in_order:
        # Fall back to a single-speaker attribution.
        return [{**c, "speaker_id": "0", "speaker": "0"} for c in cues]
    # Distinct names as ids in first-seen order → "0", "1", ...
    id_map: Dict[str, str] = {}
    for name in names_in_order:
        if name not in id_map:
            id_map[name] = str(len(id_map))
    out: List[Dict[str, Any]] = []
    for cue, name in zip(cues, names_in_order):
        sid = id_map[name]
        out.append({**cue, "speaker_id": sid, "speaker": name})
    # If the caption has more cues than voice tags (rare), pad with the last.
    if len(cues) > len(out):
        last_id = out[-1]["speaker_id"] if out else "0"
        last_name = out[-1]["speaker"] if out else "0"
        for cue in cues[len(out):]:
            out.append({**cue, "speaker_id": last_id, "speaker": last_name})
    return out


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point. Writes ``<stem>.speakers.json`` next to the input."""
    return run_command(_cli, argv)


if __name__ == "__main__":
    sys.exit(main())
