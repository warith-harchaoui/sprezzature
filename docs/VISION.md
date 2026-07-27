# Alt text (local artificial intelligence, AI) — `sprezzature-vision`

Draft World Wide Web Consortium (W3C)-compliant alt text from images with a local Ollama vision model: a per-image decision tree (informative / decorative / functional / text / complex / group), any detected language, surrounding-text and project-vocabulary biasing, cached on disk. Local, no SaaS.

> **Work in progress.** Output is a *draft requiring human review*, not finished alt text; a person confirms each one before it ships. A `deepeval` layer to measure the "context-aware, W3C-guided" claim is still being built.

This is the human landing page. It points to the three places that hold the
detail; nothing is duplicated here.

- **What it is & what activates it:** [`sprezzature-vision/SKILL.md`](../sprezzature-vision/SKILL.md)
  (the agent-facing spec: purpose, trigger phrases, full flag surface).
- **Run it:** [`EXAMPLES.md`](../EXAMPLES.md) has a copy-paste recipe for
  `sprezzature-vision`.
- **Go deeper:** [`sprezzature-vision/references/`](../sprezzature-vision/references/): the decision tree and caching.
