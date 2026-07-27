# Accessibility lint — `sprezzature-accessibility`

A fast, deterministic pre-commit gate for static HyperText Markup Language (HTML): fourteen source-decidable accessibility (a11y) rules (missing alt, unlabelled inputs, heading order, color-only state, motion guards). Not a browser audit: the continuous integration (CI)-friendly first line before axe-core / Lighthouse.

## Two layers, on purpose

Accessibility checking has two complementary layers, and `sprezzature-accessibility`
is deliberately only the first:

1. **Static lint (this skill).** Fourteen rules decidable from the HTML source
   alone, with no browser and no rendered Document Object Model (DOM). Fast and
   deterministic, so it runs as a pre-commit and CI gate on every change. It
   catches structural defects: missing `alt`, unlabelled inputs, bad heading
   order, a clickable `div`, a dialog with no close, color-only state.

2. **Browser audit (optional, separate).** A runtime pass with
   [axe-core](https://github.com/dequelabs/axe-core),
   [Pa11y](https://pa11y.org/), or
   [Lighthouse](https://developer.chrome.com/docs/lighthouse/) drives a real
   browser and inspects the computed DOM. It catches what a static parser
   cannot: rendered color contrast, focus order in the live tab sequence,
   computed Accessible Rich Internet Applications (ARIA) roles, dynamic state. Run it in a browser or headless Chrome
   as a second, heavier stage, **after** the static gate is green, not instead
   of it.

`sprezzature-accessibility` does **not** wrap or bundle the browser layer; it is a
distinct, optional tool you add when you want runtime coverage. The static gate
is the cheap first line; the browser audit is the thorough second.

This is the human landing page. It points to the three places that hold the
detail; nothing is duplicated here.

- **What it is & what activates it:** [`sprezzature-accessibility/SKILL.md`](../sprezzature-accessibility/SKILL.md)
  (the agent-facing spec: purpose, trigger phrases, full flag surface).
- **Run it:** [`EXAMPLES.md`](../EXAMPLES.md) has a copy-paste recipe for
  `sprezzature-accessibility`.
- **Go deeper:** [`sprezzature-accessibility/references/`](../sprezzature-accessibility/references/): the rule catalogue and false-positive notes.
