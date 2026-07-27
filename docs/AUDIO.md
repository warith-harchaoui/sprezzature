# Captions & diarization (local artificial intelligence, AI) — `sprezzature-audio`

Draft WebVTT / SubRip subtitle format (SRT) captions from a local whisper.cpp build, then add who-spoke-when (NeMo Sortformer) and who-is-who (TitaNet, or a transcript rule + a local Ollama pass). Bilingual, local, never a SaaS.

> **Work in progress.** The caption backend (vocal-helper) is still settling, and per-language accuracy baselines are being collected; treat captions as drafts to review, not turnkey output.

This is the human landing page. It points to the three places that hold the
detail; nothing is duplicated here.

- **What it is & what activates it:** [`sprezzature-audio/SKILL.md`](../sprezzature-audio/SKILL.md)
  (the agent-facing spec: purpose, trigger phrases, full flag surface).
- **Run it:** [`EXAMPLES.md`](../EXAMPLES.md) has a copy-paste recipe for
  `sprezzature-audio`.
- **Go deeper:** [`sprezzature-audio/references/`](../sprezzature-audio/references/): captions, diarization, speaker naming.
