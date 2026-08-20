---
name: sprezzature-audio
description: >-
  Local-AI captions, speaker diarization and speaker identification for video
  / audio. Trigger phrases: "captions", "transcribe video", "transcribe
  audio", "WebVTT", "SRT", "subtitle file", "VTT", "diarization", "who
  spoke when", "Sortformer", "TitaNet", "identify speakers", "name the
  speakers", "translate captions", "translated subtitles", "subtitles".
  Generates W3C WebVTT / SRT / plain-text captions from a local whisper.cpp
  build (vocal-helper), then adds "who spoke when" via NVIDIA NeMo Sortformer
  and "who is who" via NeMo TitaNet embeddings (against reference clips) OR a
  transcript-based rule + local Ollama pass that mines self-introductions
  ("I'm Alice") and vocatives ("Hey Mary, ..."). Merger emits speaker-
  labelled VTT with named voice cues. Project-vocab biasing on the caption
  path. Bilingual EN/FR default, auto-detected from context. Runs on your machine;
  never sends audio to a SaaS. Output is a captions / RTTM / speakers.json /
  speaker-VTT file on disk + a ready-to-paste snippet on stdout.
license: BSD-3-Clause
compatibility: >-
  Runtime: Claude.ai, Claude Code, OpenCode. Python 3.10+ stdlib +
  ``vocal-helper`` + ``audio-helper`` / ``video-helper`` (see
  ``requirements-captions.txt``); ``ffmpeg`` on PATH for non-WAV
  inputs. ``install_captions.py`` installs vocal-helper + a GGML model.
  Diarization (``requirements-diarize.txt``) adds ``nemo_toolkit[asr]``
  (pulls torch) + Sortformer/TitaNet via ``install_diarize.py``.
  Transcript naming is stdlib-only unless ``--ollama``. No network at
  inference after install.
metadata:
  author: Warith Harchaoui
  version: 1.0.1
---

> The deterministic tools below now ship as the standalone package [`sprezzature-audio`](https://github.com/warith-harchaoui/sprezzature-audio) (`pip install`), invoked as `sprezzature-audio …`. The `scripts/` folder has moved out of this monorepo; the SKILL.md here stays as the agentic contract.

# sprezzature-audio — local AI captions and transcripts

## Audience and positioning

Solo developers and small teams who:

- Need **WebVTT / SRT captions** on every `<video>` and `<audio>` they
  ship, drafted at commit time rather than via a hosted service.
- Want **AI that runs locally**: no SaaS bill, no audio exfiltration, no
  per-minute pricing. Apple-silicon Macs get Metal acceleration via
  ``whisper.cpp`` automatically.
- Want **vocabulary biasing** so the model knows the project's
  technical terms / product names / people's names before it
  hallucinates a near-miss spelling.
- Want **bilingual** captions: the language is auto-detected from the
  transcript / vocabulary (via `langdetect`); no flag, no configured default.

This skill is **not** a substitute for a human review pass. Each draft
should be read and corrected; automatic captions miss proper nouns,
mishear similar words, and drop punctuation. For real-time captions
(live streams, video calls), use **Deepgram** or **AssemblyAI**; this
skill is for static media that gets committed to a repo.

## Status — WiP

The script and tests ship today; what is still being collected:

- Per-language **WER baselines** for EN / FR / ES (the extractor that
  builds them is wired; the baselines themselves are pending). Without
  baselines, you can't know whether a given run's quality is in the
  expected band.
- A user-supplied **``vocab-biasing-clip.wav``** that exercises the
  prompt-biasing path end-to-end. The current tests check the
  prompt-string construction; an audio fixture would let us regress
  on the actual transcription behaviour.

A future revision will integrate **``pdbms``** (per the maintainer) to
improve the whisper.cpp integration. Track shape via
``tests/fixtures/audio/README.md``.

## Two modes: make and audit

This skill is **make-only** in the sprezzature-* duality, by design. The
make side has two tiers: a lightweight **captions** tier and a
heavier **diarization + speaker ID** tier that layers on top.

| Mode | Tool | Purpose |
|---|---|---|
| **Make** — draft captions / transcripts | `captions_from_whisper.py` + `install_captions.py` | WebVTT / SRT / plain-text captions via local whisper.cpp, with project-vocab biasing. |
| **Make** — speaker diarization ("who spoke when") | `diarize_from_nemo.py` + `install_diarize.py` | NeMo Sortformer end-to-end diarizer → RTTM + turn JSON. Up to 4 concurrent speakers with the default checkpoint. |
| **Make** — speaker identification via **reference clips** | `identify_from_titanet.py` | NeMo TitaNet 192-D speaker embeddings + cosine matching against a directory of known WAVs (filename stem = display name). |
| **Make** — speaker identification via the **transcript itself** | `name_from_transcript.py` | Rule pass over self-introductions ("I'm Alice") + turn-initial / turn-final vocatives ("Hey Mary, ..."). Optional `--ollama` refinement via a local Ollama daemon, the same daemon `alt_from_ollama.py` uses. |
| **Make** — merge captions + diarization | `caption_diarize.py` | Emits speaker-labelled VTT (`<v Name>` cues), SRT (`Name: text` prefix), or plain text with paragraph breaks per speaker turn. |
| **Make** — translate captions → second track | `translate_captions.py` | Translates an existing `.vtt`/`.srt` into the **surrounding-text language** via the local Ollama model (`qwen3-vl:8b`) and prints a two-`<track>` snippet (native `captions` + translated `subtitles`). Captions-only, no audio. |
| **Audit** — gate the presence of `<track>` | _(see `sprezzature-accessibility/scripts/lint_a11y.py`)_ | Static lint catches `<video>` / `<audio>` without a `<track kind="captions">` child. |

Pair with `sprezzature-accessibility` to close the loop: this skill drafts
the file; the a11y lint verifies a `<track>` element references it.

## Honest framing of what the tool covers

| Tool | Catches | Misses |
|---|---|---|
| `captions_from_whisper.py` | WebVTT / SRT / plain-text captions from a local whisper.cpp build; project-vocab biasing via ``--prompt`` / ``--vocab`` / ``--vocab-from`` / ``--auto-project``; language auto-detection with explicit override; cache on the audio hash | not real-time (hosted services like Deepgram / AssemblyAI are better for live captions); model-quality drafts: proper nouns, similar-sounding words and quiet passages need a review pass. |
| `install_captions.py` | Installs ``vocal-helper`` (the whisper.cpp over-layer, pulling ``pywhispercpp``) into the active Python env and pre-downloads a GGML model so the captioner runs offline. Idempotent, safe to re-run. | does not install ``ffmpeg`` for you; does not auto-update an already-installed model; does not pin GPU / Metal acceleration. |
| `diarize_from_nemo.py` | End-to-end speaker diarization via NVIDIA NeMo **Sortformer**: RTTM + a JSON turn list, cached on the extracted-audio hash. Up to 4 concurrent speakers with the default checkpoint (`nvidia/diar_sortformer_4spk-v1`); the streaming variant handles more. CUDA / MPS auto-selected. | not real-time (Sortformer's streaming variant helps but this script assumes static input); struggles with heavy overlap (multiple speakers talking simultaneously); see WhisperX + pyannote for word-level attribution. |
| `identify_from_titanet.py` | Speaker identification against reference clips using **TitaNet-Large** 192-D embeddings + cosine matching. Emits a `speakers.json` mapping the anonymous ids to display names. | requires a directory of clean reference clips (one WAV per known speaker); cross-lingual retrieval needs a higher threshold; not designed for open-set identification with dozens of candidates. |
| `name_from_transcript.py` | Guesses names from the transcript itself: a rule pass over self-introductions ("I'm Alice", "je m'appelle Bob") and vocatives ("Hey Mary, ...", "Thanks, Sam"). Optional `--ollama` refinement uses the same local daemon as `alt_from_ollama.py`. | conversations without introductions or direct address get no name evidence; falls back to anonymous ids. LLM pass is optional (rule-only mode is stdlib). |
| `caption_diarize.py` | Merger: attributes every Whisper caption cue to the diarization turn with the largest overlap. Emits WebVTT with `<v Name>` cues, SRT with `Name: text` prefix, or paragraph-broken plain text. | boundaries around overlap remain approximate; the merger picks *one* speaker per cue by construction. |
| `translate_captions.py` | Second-track translation of an existing `.vtt`/`.srt` into the surrounding-text language via local Ollama (`qwen3-vl:8b`); batches several cues per call for cross-cue context and re-attaches translations to the original timestamps 1:1; emits `<stem>.<lang>.vtt` + a two-`<track>` snippet. Decoupled from the caption backend (captions in → captions out, no audio). | machine translation from an 8B model, a **draft**, verify before shipping; skips when the surrounding language already equals the audio language; needs a reachable Ollama daemon. |
| `install_diarize.py` | Installs `nemo_toolkit[asr]` and pre-downloads both Sortformer + TitaNet checkpoints. Idempotent. | does not install torch with your specific CUDA / ROCm build (install torch first if you need a specific one); does not install `ffmpeg`. |

## Decision tree

| Trigger | Tool | Run |
|---|---|---|
| "captions" / "transcribe video" / "transcribe audio" / "subtitle file" | `captions_from_whisper.py` | `python -m sprezzature_audio_scripts.install_captions` then `sprezzature-audio-captions <audio-or-video> [--format vtt\|srt\|text] [--lang fr] [--vocab-from DIR] [--auto-project]`. Always emit `<track kind="captions">` on `<video>` / `<audio>`. |
| "diarization" / "who spoke when" / "speaker turns" / "Sortformer" | `diarize_from_nemo.py` | `python -m sprezzature_audio_scripts.install_diarize` then `sprezzature-audio-diarize <audio-or-video> [--max-speakers N] [--device cuda\|mps\|cpu]`. Emits `<stem>.rttm` + `<stem>.diarization.json`. |
| "identify speakers" / "match voices" / "who is who" / "TitaNet" | `identify_from_titanet.py` | `sprezzature-audio-identify <stem>.diarization.json --audio <stem>.wav --refs ./voices/`. Writes `<stem>.speakers.json`, the same shape `caption_diarize.py` consumes. |
| "name the speakers from the transcript" / "vocative naming" / "self-introduction" | `name_from_transcript.py` | `sprezzature-audio-name <stem>.speakers.vtt [--ollama]`. Rule pass over EN + FR self-introductions and vocatives; `--ollama` calls the local daemon `alt_from_ollama.py` uses for a JSON-formatted refinement. |
| "speaker VTT" / "labelled captions" / "merge captions with diarization" | `caption_diarize.py` | `sprezzature-audio-pipeline --captions <stem>.vtt --diarization <stem>.diarization.json --speakers <stem>.speakers.json --out <stem>.speakers.vtt`. Output has `<v Name>` voice cues. |
| "translate captions" / "translated subtitles" / "two-track captions" / "subtitles in another language" | `translate_captions.py` | `sprezzature-audio-translate <stem>.vtt [--lang fr] [--in page.html] [--media clip.mp4]`. Target language = `--lang` else detected from the surrounding text (`--in` / `--context`). Writes `<stem>.<lang>.vtt` and prints a `<track kind="captions"> + <track kind="subtitles">` snippet. Needs a local Ollama daemon (`qwen3-vl:8b`). |
| "Whisper not installed" / "first-time setup" (captions only) | `install_captions.py` | `python -m sprezzature_audio_scripts.install_captions`: pip-installs ``vocal-helper`` (pulling ``pywhispercpp``) and pre-downloads a GGML model so the captioner runs offline. |
| "NeMo not installed" / "first-time setup" (diarization) | `install_diarize.py` | `python -m sprezzature_audio_scripts.install_diarize`: pip-installs `nemo_toolkit[asr]` and pre-downloads Sortformer + TitaNet weights. Add `--only sortformer` / `--only titanet` to prefetch just one. |

## Output contract

For ``--format vtt`` (the default), the script writes a sibling
``<stem>.vtt`` next to the source media and prints a ready-to-paste
HTML snippet on stdout:

```html
<video src="podcast.mp4" controls>
  <track kind="captions" srclang="en" src="podcast.vtt" default>
</video>
```

For ``--format srt`` the file is ``<stem>.srt`` with the same snippet
shape (substitute ``.srt`` for ``.vtt``). For ``--format text`` the
file is ``<stem>.txt`` with one line per detected utterance; the
``<track>`` snippet is skipped.

## Vocabulary biasing

The captioner accepts a prompt-bias string ahead of decoding. Four
ways to supply it, in order of precedence:

1. ``--prompt "<text>"`` — literal prompt prefix.
2. ``--vocab "<term1>,<term2>,..."`` — comma-separated terms.
3. ``--vocab-from <DIR>`` — read every ``.txt`` / ``.md`` under
   ``<DIR>`` and use the surrounding text + extracted terms as bias.
4. ``--auto-project`` — walk the project root (current working
   directory), pull terms from ``package.json``, ``pyproject.toml``,
   ``README.md`` and any glossary / vocab file under
   ``docs/`` / ``content/``.

Biasing helps domain spellings (product names, people, technical
terms) survive transcription. It does not improve general accuracy;
for that, switch model.

## Models

The installer pulls a small GGML model by default (``ggml-base.en``
for English-leaning sets, ``ggml-medium`` for broader / multilingual sets). Override paths:

1. ``--model <path>`` on the command line (full path to a ``.bin``).
2. ``WHISPER_MODEL_PATH=<path>`` env var.
3. The pre-downloaded model from ``install_captions.py``.

Larger models (``ggml-large-v3``) give noticeably better WER on noisy
audio at ~1.5 GB on disk and ~3× the CPU time. Pull manually via
``install_captions.py --model large-v3`` when the smaller default is
under-serving you.

## Tool composition

When emitting ``<video>`` or ``<audio>`` in a deliverable:

```bash
sprezzature-audio-captions --auto-project <media>
```

Always emit ``<track kind="captions" srclang="…" default>`` on the
element. For a **second, translated track**, run
``translate_captions.py`` on the produced ``.vtt``: it writes a
``<track kind="subtitles" srclang="…">`` in the surrounding-text language
(via local ``qwen3-vl:8b``) and prints the two-track snippet. Add
``<track kind="descriptions">`` for audio descriptions,
``<track kind="chapters">`` for navigation when chapters exist.

## When NOT to use this skill

- You need **real-time captions** (live streams, video calls) → use
  **Deepgram** or **AssemblyAI**; the cache and disk-bound shape of
  this skill assume static input.
- You need **top-quality accuracy and don't care about local-only /
  cost** → hosted services (Deepgram, AssemblyAI, Whisper.com) are
  noticeably better on noisy or accented audio.
- You need a **human-grade** translation → ``translate_captions.py``
  drafts a second subtitle track with the local ``qwen3-vl:8b`` model, but
  it is machine translation from a small model: fine as a starting point,
  not a substitute for a professional subtitler on published work.

## References

- ``references/captions-ai.md`` — Local vocal-helper (whisper.cpp)
  captions / transcripts for video and audio, with vocabulary biasing.
- ``references/diarization.md`` — Sortformer / TitaNet /
  transcript-based naming pipeline; reference-clip layout; merger
  rule; output formats (WebVTT `<v Name>` cues, SRT prefix, plain
  text). Prior art the transcript-naming rule pass is modelled on
  (Bäuml et al. 2013, Nagrani et al. 2017).

## Scripts

Shipped by the standalone [`sprezzature-audio`](https://github.com/warith-harchaoui/sprezzature-audio)
package, not by this monorepo. The `Install` column below is the pip
extra that pulls the tier's dependencies (`pip install
"sprezzature-audio[captions|diarize|translate|all]"`); the `Console script`
column is the command that lands on `$PATH` once installed.

| Script | Install | Console script | Purpose |
|---|---|---|---|
| ``captions_from_whisper.py`` *(WiP)* | ``sprezzature-audio[captions]`` + ``ffmpeg`` on PATH | ``sprezzature-audio-captions`` | WebVTT / SRT / plain-text captions via local whisper.cpp. Per-language WER baselines + vocab-biasing reference clip still being collected. |
| ``install_captions.py`` | ``sprezzature-audio[captions]`` | (none; run as ``python -m sprezzature_audio_scripts.install_captions``) | Installs ``vocal-helper`` (pulling ``pywhispercpp``) and pre-downloads a GGML caption model. |
| ``diarize_from_nemo.py`` | ``sprezzature-audio[diarize]`` + Python 3.10+ | ``sprezzature-audio-diarize`` | Speaker diarization via NVIDIA NeMo **Sortformer** (``nvidia/diar_sortformer_4spk-v1``). Emits RTTM + turn JSON; caches on the extracted-audio hash. |
| ``identify_from_titanet.py`` | ``sprezzature-audio[diarize]`` | ``sprezzature-audio-identify`` | Speaker identification via NeMo **TitaNet-Large** embeddings; cosine matching against a directory of reference clips (one WAV per known speaker). Writes ``speakers.json``. |
| ``name_from_transcript.py`` | ``sprezzature-audio`` (core); optional local Ollama for the ``--ollama`` refinement | ``sprezzature-audio-name`` | Guesses speaker names from the diarized transcript itself: regex for self-introductions + vocatives, optional LLM refinement via the same daemon ``alt_from_ollama.py`` uses. |
| ``caption_diarize.py`` | ``sprezzature-audio`` (core) | ``sprezzature-audio-pipeline`` | Merges captions + diarization + speakers.json → speaker-labelled WebVTT (``<v Name>`` cues), SRT, or plain text. |
| ``translate_captions.py`` | ``sprezzature-audio[translate]``; a local Ollama daemon (``qwen3-vl:8b``) at runtime | ``sprezzature-audio-translate`` | Translates an existing ``.vtt``/``.srt`` into the surrounding-text language and emits a two-``<track>`` snippet (native ``captions`` + translated ``subtitles``). No audio dependency; decoupled from the caption backend. |
| ``install_diarize.py`` | ``sprezzature-audio[diarize]`` | (none; run as ``python -m sprezzature_audio_scripts.install_diarize``) | Installs ``nemo_toolkit[asr]`` and pre-downloads Sortformer + TitaNet checkpoints so the diarization scripts run offline. |
| ``_argparse.py``, ``_click.py``, ``_lang.py``, ``_vocab.py`` | (internal helpers) | (none) | Argparse / Click factory, language detection, project-vocab biasing. Duplicated per-skill so each skill stays self-contained. |

## Companion skills

| You also need… | Install |
|---|---|
| Static HTML a11y lint | ``sprezzature-accessibility`` |
| W3C alt text via local Ollama vision | ``sprezzature-vision`` |
| WCAG contrast audit, CVD simulation, curated palette | ``sprezzature-colors`` |
| Vanilla-JS + Tailwind UI generation | ``sprezzature-ui`` |
| Wrap a CLI in a GUI | ``sprezzature-cli-gui`` |
| Markdown → website + meta + favicons + indexes | ``sprezzature-publish`` |
