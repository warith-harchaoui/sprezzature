# User interface (UI) generation — `sprezzature-ui`

Vanilla JavaScript + Tailwind UI (components, pages, forms, dialogs, dashboards) for teams shipping internal tools without a designer. The three-Roboto type rule, dark-mode peers, focus rings, and reduced-motion guards come by default.

This is the human landing page. It points to the three places that hold the
detail; nothing is duplicated here.

- **What it is & what activates it:** [`sprezzature-ui/sprezzature_ui/skill/SKILL.md`](https://github.com/warith-harchaoui/sprezzature-ui/blob/main/sprezzature_ui/skill/SKILL.md))
  (the agent-facing spec: purpose, trigger phrases, the i18n tools and their flags).
- **The package:** [`sprezzature-ui`](https://github.com/warith-harchaoui/sprezzature-ui)
  (`pip install sprezzature-ui`). Two tools: `sprezzature-ui-i18n-audit` (rules
  `I18N001`, a translation table in JavaScript or HTML, and `I18N002`, a prompt
  constant in Python) and `sprezzature-ui-i18n-make` (scaffolds and compiles
  `locales/i18n.yaml`, emits the loaders). Surfaces: library, CLI (`make-ui` or
  `sprezzature-ui`), HTTP (`POST /v1/i18n-audit`), MCP (`sprezzature-ui-mcp`,
  tools `audit_i18n` and `health`), and this skill.
- **Run it:** [`EXAMPLES.md`](../EXAMPLES.md) has a copy-paste recipe for
  `sprezzature-ui`.
- **Go deeper:** [`sprezzature-ui/sprezzature_ui/skill/references/`](https://github.com/warith-harchaoui/sprezzature-ui/tree/main/sprezzature_ui/skill/references/)): tokens, components, dataviz, the design system, i18n.
