# Captions / transcripts: `captions_from_whisper.py`

Generate WebVTT captions, SRT subtitles, or plain transcripts from any audio or video file through **[vocal-helper](https://github.com/warith-harchaoui/vocal-helper)**, the project author's whisper.cpp over-layer. It wraps **[pywhispercpp](https://github.com/absadiki/pywhispercpp)** (the whisper.cpp binding) and owns the model defaults, the word-timestamp wiring, the `min_segment_ms` hallucination guard, and the vocabulary-biasing `initial_prompt` lever (a domain-aligned prompt cut WER by 15–25 pp in the author's AMI sweep). The captions tier drives its `WhisperStage` on the whole file as a single segment: no VAD, no diarization (that lives in the `diarize` tier). The default model is **`large-v3-turbo`**: small enough to run on a laptop and accurate enough for production captions.

The script handles both video (caption track for a `<video>`) and audio-only files (transcript for a podcast or interview).

## Why it matters

WCAG SC 1.2.2 (Captions, Prerecorded) is a Level A requirement and is almost universally skipped on small-team and indie sites. The same setup as the rest of the skill's helpers (local-only, no API, no cost per minute) makes shipping captions cheap.

## Install

Single command, `pip install` plus a pre-download of the GGML weights:

```bash
pip install -r scripts/requirements-captions.txt
python scripts/install_captions.py
```

The installer:

| Step | Behavior |
|---|---|
| Probe `import vocal_helper` | Skips re-install if already importable. |
| Install via pip | `pip install --upgrade` the pinned `vocal-helper@v0.3.1` git spec in the active interpreter. It pulls `pywhispercpp` (pre-compiled wheels for macOS / Linux / Windows) as a dependency. |
| Pre-download the GGML model | Via `pywhispercpp.utils.download_model` (available through vocal-helper) into `~/.cache/sprezzature-skill/whisper/`. |

`--model` accepts every pywhispercpp alias: `tiny[.en]`, `base[.en]`, `small[.en]`, `medium[.en]`, `large-v1`, `large-v2`, `large-v3`, `large-v3-turbo` (default). Smaller models are faster but noticeably less accurate on accents / overlapping speech.

## Generate

```bash
# Captions for a video → input.vtt next to the file
python scripts/captions_from_whisper.py talk.mp4

# Plain transcript for an audio-only file
python scripts/captions_from_whisper.py podcast.mp3 --format text

# Specific language + SRT
python scripts/captions_from_whisper.py interview.wav --lang fr --format srt

# Smaller model for a quick draft
python scripts/captions_from_whisper.py call.m4a --model small
```

`--out PATH` overrides the default sibling-file destination. `--no-cache` bypasses the on-disk cache for a single run.

## Audio extraction

whisper.cpp needs 16 kHz mono WAV. The script tries, in order:

1. **`video-helper`** (<https://github.com/warith-harchaoui/video-helper>) for video sources.
2. **`audio-helper`** (<https://github.com/warith-harchaoui/audio-helper>) for audio sources.
3. **`ffmpeg`** subprocess as a fallback.

Install the helpers if you want a Python-native extraction path:

```bash
pip install audio-helper   # PyPI, >=1.6.0
pip install video-helper   # PyPI, >=1.7.0
```

The extraction path uses `audio_helper.sound_converter` and
`video_helper.extract_audio_track` (16 kHz mono WAV); both are exported by
the PyPI releases above.

If neither helper nor `ffmpeg` is available, the script exits with a list of install hints.

## Cache

Same shape as the alt-text and meta helpers:

- Location: `~/.cache/sprezzature-skill/captions/`.
- Key: SHA-256 of the extracted-audio bytes + model + lang + format, truncated to 32 hex characters.
- Bypass: `--no-cache` for one run, `SPREZZATURE_NO_CACHE=1` globally.
- Clear: delete the directory.

The cache stores the final WebVTT / SRT / text body; re-runs of the same input are near-instant.

## Vocabulary biasing

Whisper's accuracy on proper nouns and jargon drops sharply without domain context. The script accepts four shapes; the first non-empty source wins:

| Flag | Meaning |
|---|---|
| `--prompt "<text>"` | Verbatim `initial_prompt` for whisper.cpp. Highest precedence. |
| `--vocab path/to/glossary.txt` | Glossary file, one term per line, `#` starts a comment. |
| `--vocab-from path` | File OR directory. Directory → walked as a project root (top-level README / SKILL.md / manifests + `.md` files under `docs/`, `references/`, `src/`, …). |
| `--auto-project` | Walk upward from the source to discover the project root, then mine the whole tree. |

Beyond those flags, the resolver looks for a **sibling subtitle file** (`<stem>.vtt` / `.srt` / `.txt`); for re-captioning runs, the prior transcript is the strongest signal. Then it looks for a sibling README / `index.html`. Pass nothing to use those defaults.

The composed `initial_prompt` is in natural prose, not a comma list; Whisper was trained on continuous text, so `"The following terms may appear in the audio: Tailwind, Montserrat, OKLCH."` outperforms `"Tailwind, Montserrat, OKLCH"`. The opener is selected from a per-language template.

## Integration in the page

For `<video>`, ALWAYS emit `<track kind="captions">`. Add the other kinds when they apply.

```html
<video controls preload="metadata">
  <source src="/talk.mp4" type="video/mp4">

  <!-- Speech + sound effects in the source language. Required. -->
  <track kind="captions" src="/talk.vtt" srclang="en" label="English" default>

  <!-- Translation of dialogue. -->
  <track kind="subtitles" src="/talk.fr.vtt" srclang="fr" label="Français">

  <!-- Narration of visuals for blind users.
       Out of scope for whisper — separate workflow. -->
  <track kind="descriptions" src="/talk.descriptions.vtt" srclang="en" label="Audio descriptions">

  <!-- Navigation markers. Emit when the source has chapters. -->
  <track kind="chapters" src="/talk.chapters.vtt" srclang="en" label="Chapters">
</video>
```

For `<audio>`, captions don't render in the player, so pair the file with an expandable transcript:

```html
<audio controls preload="metadata">
  <source src="/podcast.mp3" type="audio/mpeg">
</audio>
<details>
  <summary>Transcript</summary>
  <article id="transcript">…paste transcript here…</article>
</details>
```

The four `<track>` kinds:

| `kind` | Use | Source |
|---|---|---|
| `captions` | Speech + sound effects | `captions_from_whisper.py` (this script) |
| `subtitles` | Dialogue translation | `translate_captions.py <stem>.vtt` translates the native `.vtt` into the surrounding-text language via local `qwen3-vl:8b` and emits the second `<track>`. See "Translated second track" below. |
| `descriptions` | Visual narration for blind users | Out of scope for an audio model: frame extraction + Qwen3-VL vision. Documented as a future helper. |
| `chapters` | Navigation markers | Heuristic on long segment pauses; documented as a future helper. |

## Translated second track

`translate_captions.py` turns one caption file into **two tracks**: the
native-language `captions` (what `captions_from_whisper.py` produced) plus a
translated `subtitles` track in the language of the **surrounding text**, the
same signal `sprezzature-vision` uses to pick the alt-text language. The translation
runs on the already-produced `.vtt`/`.srt`, so it never touches audio and is
decoupled from the caption backend.

```bash
# Target language auto-detected from the page that embeds the media
python scripts/translate_captions.py talk.vtt --in article.html --media talk.mp4

# …or state it explicitly
python scripts/translate_captions.py talk.vtt --lang fr --media talk.mp4
```

How it stays faithful and correctly timed:

- **Language.** `--lang` wins; otherwise the target language is detected from
  the `--in` document body (or `--context`). It **skips** when that language is
  already the audio's language: no redundant track.
- **Batched translation.** Cues are translated in windows of several at a time
  (default 8) in one Ollama call, so a sentence split across cue boundaries
  translates as one thought. The reply is numbered; each translated line is
  re-attached to its **original cue's timestamps** 1:1. On a count mismatch the
  window is retried one cue at a time (which cannot misalign); an unrecoverable
  mismatch aborts loudly rather than shift subtitles.
- **One model.** `qwen3-vl:8b` via local Ollama, the one authorized LLM, not
  selectable. Needs the daemon running (`ollama serve`, `ollama pull qwen3-vl:8b`).
- **Draft.** Machine translation from an 8B model: verify before shipping.

It prints the ready-to-paste two-`<track>` snippet (native `captions` +
translated `subtitles`) so you can wire both at once.

`meta-tags.md` covers the social-preview tags that pair with these surfaces.

## Failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `No module named vocal_helper` (or `pywhispercpp`) | install skipped | `python scripts/install_captions.py`. |
| `Model … not found` on first transcribe | Pre-download skipped; whisper.cpp falls back to its own download but may fail offline | Run `install_captions.py --model <alias>` to pre-fetch, or set `SPREZZATURE_WHISPER_MODEL=/path/to/ggml-model.bin`. |
| `Neither audio-helper / video-helper nor ffmpeg is available` | No extractor on the host | Install one of the helper packages or `ffmpeg`. |
| Output is empty | Source has no audio track | Re-check the source; for video, confirm `ffprobe` finds an audio stream. |
| Bad accents or hallucinated text | Model too small for difficult audio | Use `large-v3-turbo` (default) or `large-v3`. |
| French in, English out | Language auto-detection misfired | Pass `--lang fr` explicitly. |

## Standards

- WCAG SC 1.2.2: Captions (Prerecorded), Level A.
- WCAG SC 1.2.5: Audio Description (Prerecorded), Level AA. (Captions alone do not satisfy this; audio descriptions need a separate workflow.)
- whisper.cpp licensing: MIT. Bundled GGML model files keep their original licenses (also MIT for the official OpenAI releases).

## Checklist

- [ ] Captions exist for every prerecorded video.
- [ ] Transcript exists for every prerecorded audio.
- [ ] `<track kind="captions" srclang="…" label="…">` matches the language.
- [ ] `--lang` set explicitly when the source's language is known.
- [ ] Reviewer pass before publishing; whisper makes occasional substitutions that the cache happily reuses.
