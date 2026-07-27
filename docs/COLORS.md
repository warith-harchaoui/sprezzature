# Color tooling — `sprezzature-colors`

Web Content Accessibility Guidelines (WCAG) contrast audit with fixes suggested from neighbours in the perceptual OKLCH color space (Lightness, Chroma, Hue of the OKLab model), color-vision-deficiency simulation, a curated Apple-inspired palette with semantic projections, perceptual lighten / darken, and a Tailwind theme emitter. Deterministic: no model, no network.

## Scope: design tokens, not image editing

`sprezzature-colors` is about a **design system's colour tokens**, the small named
set of brand and semantic colours a UI is built from, and turning them into an
accessible, colour-vision-safe Tailwind theme. It reads and writes a palette
CSV, checks contrast between token pairs, and emits `theme.extend.colors`. It is
**not** a general image colour-grading or photo-editing tool: the
colour-vision-deficiency simulation runs on a screenshot only to *preview* how
your tokens land for those readers, not to process arbitrary imagery.

This is the human landing page. It points to the three places that hold the
detail; nothing is duplicated here.

- **What it is & what activates it:** [`sprezzature-colors/SKILL.md`](../sprezzature-colors/SKILL.md)
  (the agent-facing spec: purpose, trigger phrases, full flag surface).
- **Run it:** [`EXAMPLES.md`](../EXAMPLES.md) has a copy-paste recipe for
  `sprezzature-colors`.
- **Go deeper:** [`sprezzature-colors/references/`](../sprezzature-colors/references/): the palette comma-separated values (CSV) file, color-vision deficiency (CVD), semantic color.
