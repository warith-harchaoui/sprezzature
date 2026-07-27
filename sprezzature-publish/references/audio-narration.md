# Audio narration — long-form posts → optional MP3 / WAV

`sprezzature-publish` ships an opt-in pipeline that turns a Markdown post
into a narrated audio file. The use case is **editorial enhancement**,
not WCAG compliance; screen readers already cover the strict a11y
baseline for long-form text. The cases where this earns its keep:

- Multitasking audience (commute, cooking, exercise).
- Cognitive-accessibility "alternative format" (WAI-COGA direction,
  not yet normative in WCAG 2.x but emerging in WCAG 3.0 drafts).
- Podcast positioning of an existing blog (Substack, NYT, Bloomberg,
  The Economist do this; the pipeline lets you do it without their
  SaaS price tag).

## What this is not

- A WCAG 2.x requirement. SC 1.2.x covers text-for-media (captions,
  transcripts), not media-for-text.
- A replacement for `<track>` elements on audio/video. The
  captions pipeline (`sprezzature-audio/scripts/captions_from_whisper.py`)
  is the WCAG-mandated direction.
- A substitute for human-narrated content where the author's voice
  matters editorially (memoir, opinion, performance writing: record
  yourself instead).

## Quick start

```bash
# 1. Install one engine (both are MIT for code AND weights)
pip install -r sprezzature-publish/scripts/requirements-narrate-chatterbox.txt
python3 sprezzature-publish/scripts/install_narrate.py --engine chatterbox

# 2. Pick a built-in voice (or skip to clone a custom voice below)
python3 sprezzature-publish/scripts/pick_voice.py --engine chatterbox --sample
# Listen to out/voice-samples/chatterbox/*.wav, decide.

# 3. Narrate a post
python3 sprezzature-publish/scripts/narrate_post.py \
    --engine chatterbox \
    --voice default \
    posts/2026-06-21-hello.md

# 4. The result + a sha256-keyed manifest land under
#    out/audio/narration.wav + out/audio/manifest.json
```

## Cloning your own voice

For when the author wants the narration in their own voice. **Only
clone voices you own** or have explicit written consent for; this is
the OSS-professional line and the legal one in most jurisdictions
(GDPR-recital-26 personal-data territory in the EU; right-of-publicity
patchwork in the US; explicit "biometric data" classification under
Illinois BIPA and similar laws).

```bash
# 1. Record 6-30 s of clean speech (read any neutral paragraph).
#    Mono, 16-44 kHz, no background music, no other voices.
arecord -d 20 -f cd -r 24000 -c 1 my-voice.wav   # Linux
# Or: any QuickTime / Voice Memos / Audacity export to WAV.

# 2. Pass it as --voice-sample to narrate_post.py
python3 sprezzature-publish/scripts/narrate_post.py \
    --engine chatterbox \
    --voice-sample my-voice.wav \
    posts/2026-06-21-hello.md
```

ChatterboxTTS and OpenVoice v2 both support zero-shot cloning from
a 6–30 s sample. OpenVoice's tone-converter does a better job of
preserving accent and prosody; ChatterboxTTS produces more
expressive output but is more sensitive to noise in the reference.

## Engine matrix

| Engine | Code lic. | Weights lic. | Built-in voices | Clone | Strength |
|---|---|---|---|---|---|
| **OpenVoice v2** (MyShell) | MIT | MIT | 5+, multi-lang | Yes | Cross-lingual, preserves accent of the sample. |
| **ChatterboxTTS** (Resemble) | MIT | MIT | 1 default, lib via WAV files | Yes | More expressive (continuous `exaggeration` dial). |
| ~~F5-TTS~~ | MIT | **CC-BY-NC-4.0** | — | Yes | Excluded: non-commercial weights. |
| ~~XTTS-v2~~ (Coqui) | MIT | **CPML non-commercial** | — | Yes | Excluded: non-commercial + project shut down 2024-01. |
| ElevenLabs | proprietary | proprietary | many | Yes | API-only, paid. Not shipped; documented as a hook for those who accept SaaS. |

**Rule of thumb:** pick **OpenVoice v2** for multi-lingual content
where you want the cloned voice to sound consistent across languages.
Pick **ChatterboxTTS** for English-only content where expressiveness
matters (essays with mood swings, opinion pieces). Both are
acceptable defaults; the narration manifest records which one
produced each clip so you can A/B.

### Installation gotcha — OpenVoice package rename

Between mid-2025 and mid-2026 the upstream `myshell-ai/OpenVoice`
repo renamed the `pyproject.toml` package name from `openvoice` to
`myshell-openvoice` without changing the import path. Modern pip
rejects the mismatch:

```text
Requested myshell-openvoice from git+https://github.com/myshell-ai/OpenVoice.git@main
has inconsistent name: expected 'openvoice', but metadata has 'myshell-openvoice'.
ERROR: No matching distribution found for openvoice (unavailable)
```

The pinned requirement in
`sprezzature-publish/scripts/requirements-narrate-openvoice.txt` still uses
the old name. Two workable fixes locally:

1. **Pin a pre-rename commit.** Replace `@main` in the requirements
   file with a commit SHA from before the rename (any commit on the
   `main` branch tagged `v2.x.x` works). This is the reproducible
   path; the SECURITY.md "Supply-chain notes" line about pinning
   minor versions applies here too.
2. **Use the upstream package name.** Edit the requirements file
   line to `myshell-openvoice @ git+…@main`. Pip then accepts the
   install. The import path inside `narrate_openvoice.py` (`import
   openvoice` / `from openvoice import ...`) is unchanged.

The skill's `install_narrate.py` script does **not** call pip; it
only downloads the v2 checkpoint files into the expected layout, so
it's unaffected. The pip-install step is on you (or your
requirements pin) until the OpenVoice maintainers republish under a
stable name.

## Hints derived from structure

`_narrate.extract_segments` reads the Markdown tree and assigns
default narration hints per segment. The pipeline honors:

| Markdown construct | Narration hint |
|---|---|
| `# H1` heading | 1500 ms pause before + after, announced as "Section: ..." |
| `## H2` heading | 1000 ms pause |
| `### H3+` heading | 700 ms pause |
| Paragraph | 800 ms pause after |
| List item (non-last) | 400 ms pause after |
| List item (last) | 800 ms pause after |
| Blockquote | Wrapped with "Quote: ... End quote." + lower intensity |
| Code fence | Skipped (sigil-heavy; rarely reads well) |
| Image (`![alt](…)`) | Alt text only (URL dropped) |
| Link (`[text](…)`) | Link text only (URL dropped) |
| Inline code `` `x` `` | Backticks stripped, content kept |
| Emoji `⚠️ 💡 🎉 🔥 …` | Emotion baseline set per emoji (see lookup table in `_narrate.EMOJI_EMOTION`) |
| Frontmatter `narration.tone` | Project-wide baseline emotion |
| Frontmatter `narration.pace` | Project-wide baseline pace |
| Inline `[emotion: cheerful]` | Override emotion for the segment that follows |
| Inline `[emotion: default]` | Reset to structural baseline |

## Hints enriched by a local LLM (opt-in)

Pass `--ai-hints` to call the same local Ollama daemon
`alt_from_ollama.py` and `meta_from_ollama.py` already use (default
model: `qwen3-vl:8b`). The LLM classifies each segment in context
(prev / next segment, section title) and returns:

```json
{
  "emotion": "cautious",
  "intensity": 0.7,
  "pace": "slow",
  "pause_before_ms": 600,
  "pause_after_ms": 1200,
  "emphasis_word": "actually",
  "rationale": "punchline of a comparison — needs a beat before"
}
```

Structural baselines are the source of truth; LLM hints override on
specific fields only and are clamped to safe bounds. If Ollama is
unreachable, the call fails soft and narration continues on the
structural defaults; the pipeline never crashes on a missing daemon.

**Inspect the enriched plan before committing GPU time:**

```bash
python3 sprezzature-publish/scripts/narrate_post.py \
    --ai-hints --ai-hints-only \
    posts/2026-06-21-hello.md | jq
```

This prints the segment list with merged hints and exits without
invoking the TTS engine; useful for reviewing the LLM's calls when
the narration sounds off.

## Project-wide pronunciation overrides

Drop a `pronunciation.yaml` next to the post or at the project root:

```yaml
# Brand / acronym pronunciation. Token → spoken form.
# Whole-word, case-sensitive. Longer tokens win when they overlap.
WCAG: "wuh-cag"
SKILL.md: "skill dot M D"
pywhispercpp: "pie-whisper-c-p-p"
OKLCH: "oh-K-L-C-H"
sprezzature-cli-gui: "sprezzature C L I G U I"
```

The narrator loads it once per post; substitutions apply to every
segment before it reaches the engine.

## Placement in the rendered page

The convention every major publisher converged on (NYT Audio,
Substack, The Economist, Bloomberg, BeyondWords clients):

```html
<header class="post-header">
  <h1>Post title</h1>
  <p class="post-meta">Warith Harchaoui · 2026-06-21 · 8 min read</p>

  <!--
    Audio player goes RIGHT HERE — between the title/meta and the
    first paragraph. People who want to listen want to decide before
    they start reading.
  -->
  <figure class="post-audio">
    <figcaption>🎧 Listen · 12 min</figcaption>
    <audio controls preload="none" src="/audio/2026-06-21-hello.mp3">
      Your browser does not support the audio element.
      <a href="/audio/2026-06-21-hello.mp3">Download MP3</a>
    </audio>
  </figure>
</header>

<article>
  …first paragraph…
</article>
```

Always provide:

- **A visible duration estimate.** People decide on it.
- **A download link** as fallback for browsers / contexts where
  inline playback fails.
- **`preload="none"`** so the audio is not fetched until the user
  presses play (network + battery courtesy).

## RSS / Atom enclosure

`site_indexes.py` injects `<enclosure>` rows into the feed when an
audio manifest is supplied (`--audio-manifest out/audio/manifest.json`).
That single addition turns the blog feed into a podcast feed any
podcast app can subscribe to, with zero extra hosting.

```xml
<!-- One entry in the RSS feed -->
<item>
  <title>Post title</title>
  <link>https://example.com/posts/2026-06-21-hello.html</link>
  <pubDate>Sun, 21 Jun 2026 09:00:00 +0000</pubDate>
  <enclosure url="https://example.com/audio/2026-06-21-hello.mp3"
             length="9876543"
             type="audio/mpeg" />
  <description>…post summary…</description>
</item>
```

## Schema.org + OpenGraph metadata

Add to the page `<head>`:

```html
<!-- OpenGraph: Slack/iMessage/etc. show the audio in the share card. -->
<meta property="og:audio" content="https://example.com/audio/2026-06-21-hello.mp3">
<meta property="og:audio:type" content="audio/mpeg">

<!-- Schema.org: Google et al. expose the audio in rich results. -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "Post title",
  "audio": {
    "@type": "AudioObject",
    "contentUrl": "https://example.com/audio/2026-06-21-hello.mp3",
    "encodingFormat": "audio/mpeg",
    "duration": "PT12M"
  }
}
</script>
```

The narration manifest carries `duration_seconds` per post; convert
to ISO-8601 (`PT{minutes}M{seconds}S`) when emitting the JSON-LD.

## Voice cloning ethics

OSS does not exempt you from consent law. Before cloning a voice
that isn't yours:

1. **Get written consent** scoped to the specific use case (blog
   narration, language, distribution channels). A signed
   one-paragraph email is fine; a verbal "sure go ahead" is not.
2. **Don't deepfake.** Cloning a public figure or a colleague
   without explicit consent for the specific output is at best a
   reputational disaster, at worst illegal (BIPA in Illinois,
   biometric-data classification under GDPR Article 9, right-of-
   publicity in California / NY / Tennessee).
3. **Watermark / label.** Either embed an audible "narrated by
   AI in [voice owner]'s voice" intro, or include a textual
   disclosure next to the player. The project doesn't enforce this
   automatically; it's an editorial choice you make per post.
4. **Don't ship reference samples.** If the project repo has a
   `voices/` folder, gitignore it. Reference clips are personal data;
   committing them to public source control is a privacy regression.

## When to outgrow this pipeline

- **Human narrator quality matters** (memoir, opinion that depends
  on the author's vocal performance): record yourself or hire a
  narrator. No TTS engine produces convincing irony.
- **You need real-time / streaming TTS** (live transcription,
  interactive avatars): out of scope. ElevenLabs / Cartesia have
  streaming APIs.
- **You need per-paragraph dialogue with multiple voices**: out of
  scope. Possible by chunking with different engines per chunk, but
  stitching artefacts at the seams are audible and the architecture
  becomes painful to maintain.

## What CI does not do here

The narration pipeline is **not exercised in CI** because it requires
~1 GB of model weights and minutes of CPU/GPU per post. The
deterministic tests cover the pure-Python parts (segment extraction,
pronunciation overrides, manifest cache, RSS enclosure injection,
emotion→engine-dial mapping). Engine wrappers are smoke-tested via
the orchestrator's mock-subprocess path; actual synthesis is a local
developer / production task.

Concretely, `.github/workflows/ci.yml` installs every per-skill
`requirements-*.txt` so the Ollama-backed scripts import cleanly
during collection, **except**
`requirements-narrate-openvoice.txt` and
`requirements-narrate-chatterbox.txt`, which are skipped explicitly.
Both engine wrappers use `importlib` for lazy imports inside the
synthesis path, so collection succeeds without the heavy ML
dependencies. Skipping them also avoids the upstream OpenVoice
package-rename trap (see "Installation gotcha" above) blocking
unrelated CI runs.
