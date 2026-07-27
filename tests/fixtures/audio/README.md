# Audio fixtures for `tests/eval/test_captions_eval.py`

Speech clips used by the captions eval (`pytest -m eval`). Not
auto-downloaded by CI; the eval suite is opt-in and developers populate
fixtures on demand.

The canonical source is **Common Voice 26.0** via the [Mozilla Data
Collective][mdc]. CC0 audio, real transcripts, rich speaker metadata
(age, gender, accent, regional variant), the right shape for a real
WER bench and for adding languages without rewriting anything.

Default per-language subset: **100 clips**, stratified-sampled across
gender / age / accent, capped at 3 clips per opaque speaker hash so no
single contributor dominates. Languages currently wired in the test:
`en`, `fr`, `es`.

[mdc]: https://mozilladatacollective.com/organization/cmfh0j9o10006ns07jq45h7xk

## Layout

```text
tests/fixtures/audio/
├── README.md                              this file
├── extract_cv_subset.py                   reusable extractor (stdlib + ffmpeg)
├── cv/
│   ├── en/
│   │   ├── MANIFEST.json                  per-clip source IDs, sha256, demographics
│   │   ├── STATS.json                     realised diversity breakdown
│   │   ├── clip-001.txt … clip-100.txt    verbatim transcripts  (committed)
│   │   └── clip-001.wav … clip-100.wav    16 kHz mono PCM       (gitignored)
│   ├── fr/                                same shape, French
│   ├── es/                                same shape, Spanish
│   └── <new-lang>/                        add languages here, same shape
├── vocab-biasing-clip.wav                 (gitignored — user-supplied)
├── vocab-biasing-clip.txt                 verbatim transcript
└── MANIFEST.json                          legacy single-clip manifest (LibriVox path)
```

**Why per-clip `.txt` + per-language `MANIFEST.json`?** The transcript
is what `jiwer` needs as the WER reference; keeping it next to the
clip makes per-clip failures easy to diff. The manifest records the
source CV clip ID, MP3 + WAV SHA256s, opaque speaker hash, and the
full demographic row so the subset is reproducible from the same seed
and you can rebalance later without re-listening to anything.

**Why a separate `STATS.json`?** Fast at-a-glance check that the
sampled subset actually hit the diversity target (e.g. "65 female /
35 male / 0 unknown" across "twenties / thirties / forties / …").
The extractor prints these to stdout too.

**Why gitignore the WAVs?** 100 clips × ~250 KB × 3 languages ≈ 75 MB
and we want headroom to add languages later without bloating the repo.
The manifest + transcripts + extractor + the same Common Voice release
let anyone rebuild the WAVs identically.

## Licensing

Common Voice clips are CC0 (public domain): redistributable, no
attribution required. Mozilla Data Collective's platform terms add one
binding rule: **don't try to identify speakers.** Manifests store
Common Voice's opaque `client_id` hash for reproducibility, never raw
identifiers. Full compliance note in `LICENSE.md` § "Common Voice
audio clips."

## Recipe for one language

The Common Voice download is large (English 88 GB, French 29 GB,
Spanish ~25–40 GB depending on the release). The extractor keeps only
~25 MB of WAVs per language, so the workflow is
**download → extract → delete tarball**.

1. **Install `ffmpeg`** (used to transcode MP3 → 16 kHz mono PCM WAV).
   - macOS: `brew install ffmpeg`
   - Debian / Ubuntu: `sudo apt-get install ffmpeg`
   - Windows: `winget install Gyan.FFmpeg`

2. **Download the language tarball** to `/tmp` (or anywhere with
   enough free space).
   1. Visit https://mozilladatacollective.com/organization/cmfh0j9o10006ns07jq45h7xk
   2. Register an account if you haven't.
   3. Click the language you want (e.g. *Common Voice Scripted
      Speech 26.0 - French*).
   4. Accept the CC0 acknowledgement
      (*"By downloading this data you agree to not determine the
      identity of speakers in the dataset"*).
   5. Click **Download**. The file is named like
      `common-voice-scripted-speech-26-0-french-<hash>.tar.gz`.

3. **Run the extractor.** Two passes over the tarball: pass 1 reads
   `validated.tsv` + `clip_durations.tsv`, pass 2 extracts only the
   selected MP3s and transcodes each one.

   ```bash
   python3 tests/fixtures/audio/extract_cv_subset.py \
       --lang fr \
       --tarball /tmp/common-voice-scripted-speech-26-0-french-<hash>.tar.gz \
       --count 100 \
       --out tests/fixtures/audio/cv/fr/
   ```

   Useful flags:

   | Flag | Default | Why touch it |
   | --- | --- | --- |
   | `--count` | 100 | shrink for a quick smoke test (e.g. 20) |
   | `--max-per-speaker` | 3 | raise for languages with few contributors |
   | `--min-duration-ms` | 3000 | widen if the language ships shorter clips |
   | `--max-duration-ms` | 15000 | raise to include longer utterances |
   | `--seed` | 0 | change to redraw the subset; same seed reproduces it bit-for-bit |

   Expected timing: pass 1 takes several minutes on the larger
   languages (the whole tarball is gzipped, so it has to stream through
   to find the TSVs). Pass 2 is faster because we abort as soon as the
   final selected MP3 has been read.

4. **Delete the tarball** — `rm /tmp/common-voice-…tar.gz`. Free the
   disk; the extractor wrote the only bytes worth keeping.

5. **Commit the manifest + transcripts.** Verify the layout:

   ```bash
   ls tests/fixtures/audio/cv/fr/
   #   MANIFEST.json STATS.json
   #   clip-001.txt … clip-100.txt
   #   clip-001.wav … clip-100.wav    ← gitignored
   git add tests/fixtures/audio/cv/fr/MANIFEST.json \
           tests/fixtures/audio/cv/fr/STATS.json \
           tests/fixtures/audio/cv/fr/clip-*.txt
   git commit -m "test: add Common Voice FR captions eval subset (100 clips)"
   ```

6. **Sanity-check the diversity.** Open `STATS.json`. Expect:
   - `n_unique_speakers` close to `n_clips ÷ max_per_speaker` (e.g.
     ≥30 unique speakers on a 100-clip 3-cap subset).
   - `gender_counts` reasonably balanced; large skews (>80/20) usually
     mean the language's CV contributors skew demographically. Note it
     in the commit message rather than rebalancing artificially.
   - `accent_counts` shows multiple buckets when the language has them
     (e.g. EN gives "United States English", "England English", …).

## Adding a new language — full walk-through for contributors

This section is the canonical how-to. Everything else above is a
reference for the maintainer; this section is the recipe for a
contributor who wants to ship support for a language we haven't wired
yet.

### Prerequisites

- Python 3.10+ + `ffmpeg` on PATH.
- ~30–90 GB free disk for the temporary tarball (depends on language:
  ride-along languages like Welsh or Esperanto are < 5 GB; major
  languages are 25–88 GB).
- An account on https://mozilladatacollective.com (free).
- A clone of this repo, working tree clean.

### Steps

1. **Pick the BCP-47 code.** Use the same two-letter base tag Common
   Voice uses on the dataset page. Examples: `de` (German), `it`
   (Italian), `pt` (Portuguese), `nl` (Dutch), `pl` (Polish), `ja`
   (Japanese), `zh-CN` (Mandarin: Common Voice splits Mandarin into
   `zh-CN` / `zh-HK` / `zh-TW`; use whichever you want to wire and pick
   one).

2. **Download the tarball.** Follow steps 2.1–2.5 of "Recipe for one
   language" above. Note the path; you'll pass it to the extractor.

3. **Run the extractor with the language code.**

   ```bash
   python3 tests/fixtures/audio/extract_cv_subset.py \
       --lang <code> \
       --tarball /tmp/<your-tarball>.tar.gz \
       --count 100 \
       --out tests/fixtures/audio/cv/<code>/
   ```

   If the extractor warns that fewer than 100 clips satisfied the
   filters (small languages can have this), try `--max-per-speaker 5`
   or widen `--min-duration-ms` / `--max-duration-ms`. Document any
   non-default flags in your commit message; they affect
   reproducibility.

4. **Delete the tarball.** `rm /tmp/<your-tarball>.tar.gz`.

5. **Wire the language into the test.** Open
   `tests/eval/test_captions_eval.py` and find:

   ```python
   LANGUAGES = ("en", "fr", "es")
   ```

   Add your code:

   ```python
   LANGUAGES = ("en", "fr", "es", "de")
   ```

   That's the only code change; the test loops over `LANGUAGES` and
   runs the same per-clip WER assertion against each language's
   manifest.

6. **Add a line to `LICENSE.md`'s "Common Voice audio clips" section**
   if the new language has special licensing or attribution
   considerations. Usually unnecessary; CC0 covers the bulk case.

7. **Commit.** Manifest + STATS + transcripts + test diff in one
   commit; WAVs stay gitignored.

   ```bash
   git add tests/fixtures/audio/cv/<code>/MANIFEST.json \
           tests/fixtures/audio/cv/<code>/STATS.json \
           tests/fixtures/audio/cv/<code>/clip-*.txt \
           tests/eval/test_captions_eval.py
   git commit -m "test: add Common Voice <name> captions eval subset"
   ```

8. **Run the eval locally** (optional but recommended, proves the
   subset is sane before pushing):

   ```bash
   python3 -m pytest -m eval \
       tests/eval/test_captions_eval.py::test_per_language_wer \
       -k <code>
   ```

   You should see a median WER report per language. If your new
   language fails the gate, either the model genuinely struggles on
   that language at `large-v3-turbo` (note it in the commit) or you
   picked an unrepresentative subset (rerun with a different `--seed`).

### What to do when CV doesn't have your language

A handful of languages on Common Voice have < 100 validated clips.
For those:

- **Smaller subset.** Run with `--count 20` or whatever the language
  supports. The test parametrises over whatever the manifest contains.
- **Skip the per-language median assertion** by adding the code to
  `LANGUAGES_NO_WER_GATE` in the test (it still runs the structural
  validity check but doesn't fail on WER).
- **Or wait** for the next CV release; they ship roughly twice a year
  and small languages tend to grow.

## What ships in git vs not

| Path | In git? | Why |
| --- | --- | --- |
| `extract_cv_subset.py` | yes | the extractor itself |
| `cv/<lang>/MANIFEST.json` | yes | reproducibility — clip IDs, SHA256s, demographics, seed |
| `cv/<lang>/STATS.json` | yes | quick read on the diversity breakdown |
| `cv/<lang>/clip-*.txt` | yes | WER reference; tens of KB total per language |
| `cv/<lang>/clip-*.wav` | no (gitignored) | ~25 MB per language; rebuildable via the manifest |
| `vocab-biasing-clip.txt` | yes | reference for the vocab-biasing test |
| `vocab-biasing-clip.wav` | no (gitignored) | user-supplied; see below |

## The vocab-biasing clip is special

The glossary in `tests/fixtures/vocab/glossary.txt` contains
project-brand terms (`pywhispercpp`, `VisionCell`, `Acme Robotics`,
`Tailwind`, `WebVTT`, `Ollama`) that no Common Voice reader has
uttered. We can't source this clip from CV.

To populate `vocab-biasing-clip.wav`:

1. Record yourself saying a sentence containing at least one glossary
   term, e.g. *"I use pywhispercpp to transcribe meetings into WebVTT,
   piping them through Ollama for summarisation."*
2. Save it as `vocab-biasing-clip.wav` next to this file. Any format
   ffmpeg reads works; the test transcodes if needed.
3. Rewrite `vocab-biasing-clip.txt` with the verbatim words.

## Legacy LibriVox path (kept for reference)

`fetch.py` predates the Common Voice integration and pulls a single
30-second clip per language from LibriVox / archive.org. It still
works and is a reasonable fallback when the CV download is impractical
(low bandwidth, no laptop disk headroom). The Common Voice path
supersedes it for any real WER signal.

## Why CI doesn't fetch any of this

The eval suite (`pytest -m eval`) is opt-in. It needs a running Ollama
daemon for alt-text / meta / plain-language tests and a local
whisper.cpp build for captions. Auto-downloading audio for tests that
CI itself doesn't run is wasted bandwidth. Developers running the eval
suite locally populate the fixtures once and reuse them across runs.

## When a clip is missing

`tests/eval/test_captions_eval.py` calls `pytest.skip()` with a
message that points back at this README. The deterministic suite
(`pytest` without `-m eval`) is unaffected.
