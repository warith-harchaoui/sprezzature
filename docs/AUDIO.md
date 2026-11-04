# Speech both ways (local artificial intelligence, AI): `sprezzature-audio`

Recorded speech into text, and text into speech, on your own machine. WebVTT / SubRip subtitle format (SRT) captions from a local whisper.cpp build; who spoke when (NeMo Sortformer); who is who (TitaNet against reference clips, or patterns in the transcript plus an optional local Ollama pass); speaker-labelled tracks; caption translation; a readability audit; word and diarization error rates. The other way, narration with its timed track: Kokoro by default, OpenVoice and Chatterbox, with the engine chosen by speaker-helper's router rather than by the caller. Fifteen tools, one `pip install sprezzature-audio`, never a SaaS.

> **Work in progress.** Per-language accuracy baselines are still being collected; treat captions as drafts to review, not turnkey output.

This is the human landing page. It points to the places that hold the
detail; nothing is duplicated here.

- **What it is & what activates it:** [`sprezzature-audio/SKILL.md`](../sprezzature-audio/SKILL.md)
  (the agent-facing spec: purpose, trigger phrases, every tool, the five surfaces).
- **Run it:** [`EXAMPLES.md`](../EXAMPLES.md) has a copy-paste recipe for
  `sprezzature-audio`; the package's own README and EXAMPLES list every command with the files it writes.
- **Route a request:** the package's `TRIGGERS.md` says which tool answers which request, and what to call on the library, the CLI, the HTTP API and MCP.
- **Go deeper:** [`sprezzature-audio/references/`](../sprezzature-audio/references/): captions, diarization, speaker naming.
