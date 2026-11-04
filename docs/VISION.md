# Alt text (local artificial intelligence, AI) — `sprezzature-accessibility`

Draft World Wide Web Consortium (W3C)-compliant alt text from images with a local Ollama vision model: a per-image decision tree (informative / decorative / functional / text / complex / group), any detected language, surrounding-text and project-vocabulary biasing, cached on disk. Local, no SaaS.

> **Work in progress.** Output is a *draft requiring human review*, not finished alt text; a person confirms each one before it ships. A `deepeval` suite that measures the "context-aware, W3C-guided" claim exists as an opt-in local run (`pytest -m eval`, needs Ollama); CI does not run it.

Two ways in: `sprezzature-accessibility-alt <image>` for one image, and `sprezzature-accessibility-lint --fix-alt <page>` for every `<img>` with no `alt` in a page, drafted from the text around it. `sprezzature-accessibility-install-alt` installs Ollama and pulls `qwen3-vl:8b`. Over HTTP and MCP the same engine is `POST /v1/alt` / `draft_alt_text`.

This is the human landing page. It points to the three places that hold the
detail; nothing is duplicated here.

- **What it is & what activates it:** [`sprezzature-accessibility/SKILL.md`](../sprezzature-accessibility/SKILL.md)
  (the agent-facing spec: purpose, trigger phrases, full flag surface).
- **Run it:** [`EXAMPLES.md`](../EXAMPLES.md) has a copy-paste recipe for
  `sprezzature-accessibility`.
- **Go deeper:** [`sprezzature-accessibility/references/`](../sprezzature-accessibility/references/): the decision tree and caching.
