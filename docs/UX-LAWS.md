# Laws of user experience (UX) — `sprezzature-ux-laws`

A shared vocabulary for user interface (UI) decisions plus a pre-commit auditor that flags the eight Laws-of-UX violations decidable from HTML source: Hick and Jakob as errors; Choice Overload, Miller, Fitts, Aesthetic-Usability, Selective Attention and Tesler as warnings. `--fix` repairs Fitts, Aesthetic-Usability, Miller and Jakob. The Doherty threshold is not checked: response time is not a fact about source. The reference holds thirty laws, each with a trigger / action / Tailwind hook.

One `pip install sprezzature-ux-laws` brings the library, the commands `sprezzature-ux-laws` and `sprezzature-ux-laws-audit`, the HTTP API, and the MCP server `sprezzature-ux-laws-mcp` with the tools `health`, `list_laws` and `audit_interface`.

This is the human landing page. It points to the three places that hold the
detail; nothing is duplicated here.

- **What it is & what activates it:** [`sprezzature-ux-laws/SKILL.md`](../sprezzature-ux-laws/SKILL.md)
  (the agent-facing spec: purpose, trigger phrases, full flag surface).
- **Run it:** [`EXAMPLES.md`](../EXAMPLES.md) has a copy-paste recipe for
  `sprezzature-ux-laws`.
- **Go deeper:** [`sprezzature-ux-laws/references/`](../sprezzature-ux-laws/references/): the 30-law playbook and auditor rules.
