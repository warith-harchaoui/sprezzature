---
name: sprezzature-audio
description: >-
  Local-AI speech both ways: captions out of recorded speech, narration out
  of written text. WebVTT / SRT captions from a local whisper.cpp build; who
  spoke when via NeMo Sortformer; who is who via TitaNet or the transcript;
  speaker-labelled VTT, caption translation, readability audit, WER / DER.
  The other way: Kokoro, OpenVoice and Chatterbox, each
  writing the timed track beside the audio; speaker-helper's router picks
  the engine. Never sends audio away. Use it when you are holding
  recorded speech somebody needs as text, or text somebody needs as speech.
  Trigger phrases: "captions", "transcribe video", "WebVTT", "SRT",
  "subtitles", "diarization", "who spoke when", "identify speakers",
  "translate captions", "text to speech", "TTS", "narrate", "read this
  aloud", "which voice". Not this one when: the job is to wire a narration
  into a page (sprezzature-publish, which calls this one for the voice) or
  the words describe an image (sprezzature-accessibility). The catalogue is
  in `references/triggers.md`.
license: BSD-3-Clause
compatibility: >-
  Runtime: Claude.ai, Claude Code, OpenCode. Python 3.10 to 3.13. One
  ``pip install sprezzature-audio`` brings every tool (vocal-helper,
  nemo_toolkit[asr], speaker-helper with Kokoro, Chatterbox and OpenVoice,
  FastAPI, fastapi-mcp); no feature extras. System: ``ffmpeg``,
  ``espeak-ng``. Weights via ``sprezzature-audio-install``,
  ``-install-diarize``, ``-install-voice``. Translation and the optional
  naming pass need a local Ollama. No network at inference after install.
metadata:
  author: Warith HARCHAOUI
  version: 1.8.4
---

> The deterministic tools below ship as the standalone package [`sprezzature-audio`](https://github.com/warith-harchaoui/sprezzature-audio) (`pip install sprezzature-audio`), invoked as `sprezzature-audio …`. The `scripts/` folder has moved out of this monorepo; the SKILL.md here stays as the agentic contract.

# sprezzature-audio: local AI captions, transcripts and narration

## Audience and positioning

Solo developers and small teams who:

- Need **WebVTT / SRT captions** on every `<video>` and `<audio>` they
  ship, drafted at commit time rather than via a hosted service.
- Want **AI that runs locally**: no SaaS bill, no audio exfiltration, no
  per-minute pricing. Apple-silicon Macs get Metal acceleration via
  ``whisper.cpp`` automatically.
- Want **vocabulary biasing** so the model knows the project's
  technical terms, product names and people's names before it
  hallucinates a near-miss spelling.
- Want **bilingual** captions: the language is auto-detected by
  whisper.cpp unless `--lang` is given.
- Want a page **read aloud** with a timed track, in the voice that speaks
  the page's language.

This skill is **not** a substitute for a human review pass. Each draft
should be read and corrected; automatic captions miss proper nouns,
mishear similar words, and drop punctuation. For real-time captions
(live streams, video calls), use **Deepgram** or **AssemblyAI**; this
skill is for static media that gets committed to a repo.

## Status: WiP

The tools and tests ship today; what is still being collected:

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
``tests/fixtures/audio/README.md`` in this repository.

## Two modes: make and audit

Fifteen tools, each its own console script and each a sub-command of the
front door `sprezzature-audio` (alias `make-audio`).

| Mode | Tool | Purpose |
|---|---|---|
| **Make**: draft captions / transcripts | `sprezzature-audio-captions` (`captions`) | WebVTT / SRT / plain-text captions via local whisper.cpp, with project-vocab biasing. |
| **Make**: speaker diarization ("who spoke when") | `sprezzature-audio-diarize` (`diarize`) | NeMo Sortformer end-to-end diarizer → RTTM + `.diarization.json`. Up to 4 concurrent speakers with the default checkpoint. |
| **Make**: speaker identification via **reference clips** | `sprezzature-audio-identify` (`identify`) | NeMo TitaNet speaker embeddings + cosine matching against a directory of known WAVs (filename stem = display name). |
| **Make**: speaker identification via the **transcript itself** | `sprezzature-audio-name` (`name`) | Rule pass over self-introductions ("I'm Alice") and vocatives ("Hey Mary, ..."). Optional `--ollama` refinement through a local Ollama daemon. |
| **Make**: merge captions + diarization | `sprezzature-audio-pipeline` (`pipeline`) | Speaker-labelled VTT (`<v Name>` cues), SRT (`Name: text` prefix), or plain text. Takes two files already on disk, no media. |
| **Make**: translate captions → second track | `sprezzature-audio-translate` (`translate`) | Translates an existing `.vtt`/`.srt` into the **surrounding-text language** via the local model (`qwen3-vl:8b`) and prints a two-`<track>` snippet. Captions in, captions out, no audio. |
| **Make**: text into speech | `sprezzature-audio-narrate-kokoro` (`narrate`), `sprezzature-audio-narrate-openvoice`, `sprezzature-audio-narrate-chatterbox` | `--segments <json> --out-dir <dir>` → `narration.wav` (or `--audio-format mp3`) + `narration.vtt`, and a one-line JSON report on stdout. Kokoro: 54 voices across eight languages, ONNX. OpenVoice clones from a short `--voice-sample`; Chatterbox takes emotion hints. Leave `--voice` empty and the text's language picks the voice. |
| **Make**: hear the voices first | `sprezzature-audio-voice` (`voice`) | Lists each engine's built-in voices; `--sample` writes one demo clip per voice; `--measure` ranks them by pitch movement. |
| **Make**: prepare the machine | `sprezzature-audio-install`, `-install-diarize`, `-install-voice` | GGML Whisper weights; a NeMo check + Sortformer and TitaNet checkpoints; a narration engine's weights plus an espeak-ng check. |
| **Audit**: can the captions be read at the speed they go by | `sprezzature-audio-audit` (`audit`) | Eight static rules: reversed, overlapping or empty cues, reading speed, minimum and maximum duration, line width, line count. Defaults follow the Netflix Timed Text Style Guide (17 cps, 5/6 s, 7 s, 42 characters) and the two-line convention BBC and Netflix share; each is a flag. Exit 1 on any finding. No model, no network. |
| **Audit**: how wrong is it against a reference | `sprezzature-audio-benchmark` (`benchmark`) | WER with its substitution / deletion / insertion split, DER on 10 ms frames with the standard 250 ms collar, and real-time factor of a timed command. |
| **Audit**: gate the presence of `<track>` _(borrowed, not shipped here)_ | _(see `sprezzature-accessibility-lint`)_ | Static lint catches `<video>` / `<audio>` without a `<track kind="captions">` child. |

Pair with `sprezzature-accessibility` to close the loop: this skill drafts
the file; the a11y lint verifies a `<track>` element references it.

**Who picks the voice engine.** Neither this skill nor its caller.
`speaker-helper`'s router decides; `sprezzature-publish` asks it and runs
the matching wrapper. When the user names no engine, ask the router
(`speaker-helper --language <lang> route --condition offline`) and run the
wrapper it names; `narrate` is Kokoro's front-door name, not a default.

## Honest framing of what the tool covers

| Tool | Catches | Misses |
|---|---|---|
| `captions` | WebVTT / SRT / plain-text captions from a local whisper.cpp build; vocab biasing via ``--prompt`` / ``--vocab`` / ``--vocab-from`` / ``--auto-project``; language auto-detection with ``--lang`` override; result cache on the audio hash | not real-time; model-quality drafts: proper nouns, similar-sounding words and quiet passages need a review pass. |
| `install` | Pre-downloads a GGML model (``--model``, default ``large-v3-turbo``) so the captioner runs offline. Idempotent. | does not install ``ffmpeg``; does not auto-update an installed model; does not pin GPU / Metal acceleration. |
| `diarize` | Speaker diarization via NeMo **Sortformer**: RTTM + a JSON turn list, cached on the extracted-audio hash. Default checkpoint `nvidia/diar_sortformer_4spk-v1` (up to 4 speakers); `--model` swaps it. CUDA / MPS auto-selected. | not real-time; struggles with heavy overlap; see WhisperX + pyannote for word-level attribution. |
| `identify` | Speaker identification against reference clips with **TitaNet-Large** embeddings + cosine matching (`--threshold`, default 0.55). Writes `<stem>.speakers.json`. | needs one clean reference WAV per known speaker; cross-lingual matching needs a higher threshold; not built for open-set identification with dozens of candidates. |
| `name` | Names from the transcript itself: self-introductions ("I'm Alice", "je m'appelle Bob") and vocatives ("Hey Mary, ...", "Thanks, Sam"). `--ollama` adds a local-model pass. | conversations without introductions or direct address give no evidence; the ids stay anonymous. |
| `pipeline` | Attributes every caption cue to the diarization turn with the largest overlap. | boundaries around overlap remain approximate; one speaker per cue by construction. |
| `translate` | Second-track translation via local Ollama (`qwen3-vl:8b`); batches cues for cross-cue context and re-attaches translations to the original timestamps 1:1; writes `<stem>.<lang>.vtt` and prints a two-`<track>` snippet. | an 8B model's **draft**: verify before shipping; needs a reachable Ollama daemon. |
| `install-diarize` | Checks that NeMo imports (`nemo_toolkit[asr]` is a base dependency; it is pip-installed only when missing, and `--no-install` skips even that) and pre-downloads Sortformer + TitaNet (`--only` for one). Idempotent. | does not install torch for a specific CUDA / ROCm build; does not install `ffmpeg`. |
| `narrate*` | Narration with a timed track through `speaker-helper`; `--lexicon` fixes how acronyms are said; `--check` exits 0 when the engine can synthesise here. | it reads a JSON list of blocks, not a Markdown or HTML page: turning a page into blocks is `sprezzature-publish`'s job. |

## Decision tree

| Trigger | Tool | Run |
|---|---|---|
| "captions" / "transcribe video" / "transcribe audio" / "subtitle file" | `captions` | `sprezzature-audio-install` then `sprezzature-audio-captions <audio-or-video> [--format vtt\|srt\|text] [--lang fr] [--vocab-from DIR] [--auto-project]`. Writes `<stem>.vtt` / `.srt` / `.txt`. Always emit `<track kind="captions">` on `<video>` / `<audio>`. |
| "diarization" / "who spoke when" / "speaker turns" / "Sortformer" | `diarize` | `sprezzature-audio-install-diarize` then `sprezzature-audio-diarize <audio-or-video> [--max-speakers N] [--device cuda\|mps\|cpu]`. Writes `<stem>.rttm` + `<stem>.diarization.json`. |
| "identify speakers" / "match voices" / "who is who" / "TitaNet" | `identify` | `sprezzature-audio-identify <stem>.diarization.json --audio <stem>.wav --refs ./voices/`. Writes `<stem>.speakers.json`, the shape `pipeline` consumes. |
| "name the speakers from the transcript" / "vocative naming" / "self-introduction" | `name` | `sprezzature-audio-name <stem>.speakers.vtt --out <stem>.speakers.json [--ollama]`. Without `--out` the file is `<transcript stem>.speakers.json`. |
| "speaker VTT" / "labelled captions" / "merge captions with diarization" | `pipeline` | `sprezzature-audio-pipeline --captions <stem>.vtt --diarization <stem>.diarization.json [--speakers <stem>.speakers.json] [--format vtt\|srt\|text]`. Writes `<stem>.speakers.vtt` by default. |
| "translate captions" / "translated subtitles" / "two-track captions" | `translate` | `sprezzature-audio-translate <stem>.vtt [--lang fr] [--in page.html] [--media clip.mp4]`. Target = `--lang`, else detected from `--in` / `--context`. |
| "can these captions be read" / "reading speed" / "caption audit" | `audit` | `sprezzature-audio-audit <track.vtt\|.srt> [--cps N] [--format json]`. Exit 1 on any finding. |
| "narrate" / "read this aloud" / "text to speech" / "TTS" | `narrate` | `sprezzature-audio-install-voice --engine kokoro` then `sprezzature-audio-narrate-kokoro --segments <segments.json> --out-dir <dir>`. Segments are `[{"text": "..."}, ...]`. For a whole page (player, read-along highlighting, the site), go through `sprezzature-publish-narrate`, which calls this. |
| "clone this voice" / "voice sample" / "sound like me" | `narrate-openvoice` | `pip install -r scripts/requirements-narrate-openvoice.txt` (from a clone: OpenVoice has no wheel), `sprezzature-audio-install-voice --engine openvoice`, then `sprezzature-audio-narrate-openvoice --segments ... --out-dir ... --voice-sample me.wav`. |
| "which voice" / "pick a voice" / "this voice is flat" | `voice` | `sprezzature-audio-voice --engine kokoro [--sample] [--measure]`. |
| "how good is this transcript" / "WER" / "DER" / "is it faster" | `benchmark` | `sprezzature-audio-benchmark --reference truth.vtt --hypothesis whisper.vtt`, or `--reference-rttm` / `--hypothesis-rttm`, or `--audio a.mp4 --time-command '...'`. A metric needs a reference; without one there is no number to give. |
| "which tools work here" | `tools` | `sprezzature-audio tools`. A tool's own flags: `sprezzature-audio <tool> --help` or `sprezzature-audio-<tool> --help`; the front door hands `--help` to the tool. |

## Output contract

`captions` writes a sibling ``<stem>.vtt`` (the default), ``<stem>.srt``
or ``<stem>.txt`` next to the source media and prints the path it wrote.
The `<track>` element is the caller's to emit:

```html
<video src="podcast.mp4" controls>
  <track kind="captions" srclang="en" src="podcast.vtt" default>
</video>
```

`translate` is the tool that prints a ready two-track snippet. The
narration commands print one JSON line (audio path, duration, cue path,
voice, language, detected language) and nothing after it.

## Vocabulary biasing

The captioner accepts a prompt-bias string ahead of decoding:

- ``--prompt "<text>"``: text passed verbatim to whisper.cpp as the
  initial prompt.
- Vocabulary terms, first non-empty source wins: ``--vocab <file>`` (a
  glossary, one term per line, ``#`` starts a comment), then
  ``--vocab-from <file-or-dir>`` (mined for proper nouns and identifiers),
  then ``--auto-project`` (walk upward from the media file to the project
  root and collect from the whole tree), then a sibling source detected
  automatically.

Biasing helps domain spellings (product names, people, technical
terms) survive transcription. It does not improve general accuracy;
for that, switch model.

## Models

The captioner defaults to ``large-v3-turbo``. Override it with:

1. ``SPREZZATURE_WHISPER_MODEL=<path-or-alias>``, which wins over everything.
2. ``--model <alias>`` (e.g. ``small``, ``large-v3``).
3. The pre-downloaded ``ggml-<alias>.bin`` under
   ``$SPREZZATURE_CACHE_DIR/whisper/`` (default
   ``~/.cache/sprezzature-skill/whisper/``), written by
   ``sprezzature-audio-install --model <alias>``.

Diarization: ``nvidia/diar_sortformer_4spk-v1``. Identification:
``nvidia/speakerverification_en_titanet_large``. Translation and the
naming pass: ``qwen3-vl:8b`` through best-engine-ai-helper, on the Ollama
server named by ``--url`` (default ``OLLAMA_URL``). Narration: Kokoro,
OpenVoice, Chatterbox, through speaker-helper, whose router picks the engine.

## Surfaces

| Surface | How |
|---|---|
| Library | `import sprezzature_audio as audio`: `parse`, `write_vtt`, `write_srt`, `audit_cues`, `attribute_speakers`, `word_error_rate`, `diarization_error_rate`, `describe_device` load no model; `transcribe`, `diarize`, `match_speakers`, `translate_cues`, `narrate` resolve on first use. |
| CLI | The fifteen console scripts above, and the front door `sprezzature-audio` / `make-audio` (click). |
| HTTP API | `uvicorn sprezzature_audio.api:app`: `GET /health`, `GET /v1/device`, `POST /v1/captions/convert`, `POST /v1/captions/merge`, `POST /v1/metrics/wer`, `POST /v1/metrics/der`. The Docker image and `docker compose up` run `sprezzature-audio-mcp`, which serves this app and `/mcp` on port 8000. No transcription, diarization or narration route: those are minutes-long jobs. |
| MCP | `sprezzature-audio-mcp` mounts `/mcp` on the same app (default `127.0.0.1:8000`, or `--host` / `--port`). Tools = `operation_id`s: `health`, `get_device`, `convert_captions`, `merge_speakers`, `measure_wer`, `measure_der`. Audio in → CLI; text in → MCP tool. |
| Skill | This file. |

## Tool composition

When emitting ``<video>`` or ``<audio>`` in a deliverable:

```bash
sprezzature-audio-captions --auto-project <media>
```

Always emit ``<track kind="captions" srclang="…" default>`` on the
element. For a **second, translated track**, run
``sprezzature-audio-translate`` on the produced ``.vtt``: it writes
``<stem>.<lang>.vtt`` in the surrounding-text language and prints the
two-track snippet. Then run ``sprezzature-audio-audit`` on both tracks.
Add ``<track kind="descriptions">`` for audio descriptions,
``<track kind="chapters">`` for navigation when chapters exist.

## When NOT to use this skill

- You need **real-time captions** (live streams, video calls) → use
  **Deepgram** or **AssemblyAI**; the cache and disk-bound shape of
  this skill assume static input.
- You need **top-quality accuracy and don't care about local-only /
  cost** → hosted services (Deepgram, AssemblyAI) are noticeably
  better on noisy or accented audio.
- You need a **human-grade** translation → `translate` drafts a second
  subtitle track with the local ``qwen3-vl:8b`` model: fine as a starting
  point, not a substitute for a professional subtitler on published work.
- You need to cut, resample or clean the signal → `audio-helper`.

## References

- ``references/captions-ai.md``: local vocal-helper (whisper.cpp)
  captions / transcripts for video and audio, with vocabulary biasing.
- ``references/diarization.md``: Sortformer / TitaNet /
  transcript-based naming pipeline; reference-clip layout; merger
  rule; output formats (WebVTT `<v Name>` cues, SRT prefix, plain
  text). Prior art the transcript-naming rule pass is modelled on
  (Bäuml et al. 2013, Nagrani et al. 2017).
- The brick's own ``TRIGGERS.md``: every tool, the request it answers,
  and what to call on every surface.

## Scripts

Shipped by the standalone [`sprezzature-audio`](https://github.com/warith-harchaoui/sprezzature-audio)
package, not by this monorepo. One `pip install sprezzature-audio`
installs all of them; `[dev]` is the only extra, and it is the test
toolchain.

| Script | Console script | Front door | Purpose |
|---|---|---|---|
| ``captions_from_whisper.py`` *(WiP)* | ``sprezzature-audio-captions`` | ``captions`` | WebVTT / SRT / plain-text captions via local whisper.cpp. |
| ``diarize_from_nemo.py`` | ``sprezzature-audio-diarize`` | ``diarize`` | Speaker diarization via NeMo Sortformer; RTTM + turn JSON. |
| ``identify_from_titanet.py`` | ``sprezzature-audio-identify`` | ``identify`` | Speaker identification via TitaNet against reference clips. |
| ``caption_diarize.py`` | ``sprezzature-audio-pipeline`` | ``pipeline`` | Captions + diarization (+ speakers.json) → speaker-labelled track. |
| ``name_from_transcript.py`` | ``sprezzature-audio-name`` | ``name`` | Speaker names from the transcript; optional `--ollama` pass. |
| ``translate_captions.py`` | ``sprezzature-audio-translate`` | ``translate`` | Translated second track + two-`<track>` snippet. |
| ``audit_captions.py`` | ``sprezzature-audio-audit`` | ``audit`` | Caption readability audit, eight rules. |
| ``benchmark_stt.py`` | ``sprezzature-audio-benchmark`` | ``benchmark`` | WER, DER, RTF. |
| ``narrate_kokoro.py`` | ``sprezzature-audio-narrate-kokoro`` | ``narrate`` | Narration with Kokoro. |
| ``narrate_openvoice.py`` | ``sprezzature-audio-narrate-openvoice`` | ``narrate-openvoice`` | Narration with OpenVoice (voice cloning). |
| ``narrate_chatterbox.py`` | ``sprezzature-audio-narrate-chatterbox`` | ``narrate-chatterbox`` | Narration with Chatterbox. |
| ``pick_voice.py`` | ``sprezzature-audio-voice`` | ``voice`` | List, sample and measure voices. |
| ``install_captions.py`` | ``sprezzature-audio-install`` | ``install`` | Pre-download a GGML Whisper model. |
| ``install_diarize.py`` | ``sprezzature-audio-install-diarize`` | ``install-diarize`` | Install NeMo and pre-download Sortformer + TitaNet. |
| ``install_narrate.py`` | ``sprezzature-audio-install-voice`` | ``install-voice`` | Pre-download a narration engine's weights; check espeak-ng. |

Environment: ``SPREZZATURE_WHISPER_MODEL``, ``SPREZZATURE_CACHE_DIR``,
``SPREZZATURE_NO_CACHE``, ``OLLAMA_URL``, ``SPREZZATURE_LLM_TIMEOUT`` (read
by best-engine-ai-helper; the backend, server and model are passed
explicitly, so its other ``SPREZZATURE_LLM_*`` variables do not apply), ``SPREZZATURE_AUDIO_HOST`` /
``SPREZZATURE_AUDIO_PORT`` (the MCP server).

## Companion skills

| You also need… | Install |
|---|---|
| Static HTML a11y lint | ``sprezzature-accessibility`` |
| W3C alt text via local Ollama vision | ``sprezzature-accessibility`` |
| WCAG contrast audit, CVD simulation, curated palette | ``sprezzature-colors`` |
| Vanilla-JS + Tailwind UI generation | ``sprezzature-ui`` |
| Wrap a CLI in a GUI | ``sprezzature-cli-gui`` |
| Markdown → website + meta + favicons + indexes + narration | ``sprezzature-publish`` |
