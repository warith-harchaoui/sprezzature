# Publication presets: not implemented yet

`SKILL.md`'s references list promises this file will document
"journal-ready presets (Nature single-column, Science two-column, PLOS
full-width, IEEE transactions)." Searching the standalone
`sprezzature-figures` package for anything matching that description,
the style module `_style.py`, every `make_*.py` generator, the CLI
argument parsers, and a repo-wide grep for "Nature," "PLOS," "IEEE," and
"journal" as code (not prose) found no implementation. No generator
accepts a `--preset` or `--journal` flag. `_style.py` defines dark-mode
matplotlib rcParams (`matplotlib_rc()`), corner-radius helpers, and the
polarity/palette machinery documented in
`references/polarity-and-color.md`, but no journal-specific column
widths, DPI targets, or font-size tables. The one hit for "IEEE" in the
codebase is a citation, `make_upset.py`'s docstring crediting an UpSet
plot paper published in *IEEE TVCG*, not a layout preset.

Following the same charter that governs every file in this directory,
clarify what exists and add no fact that is not verifiable: there is
nothing to document here yet. This mirrors how `SKILL.md` already
handles a comparable gap for `make_situation_map.py`, stating plainly
that a promised capability is not currently runnable rather than
describing it as if it worked.

## What exists today that is adjacent

Two house-style choices in `SKILL.md`'s own "House style" section touch
on print-readiness without amounting to a journal preset:

- **Typography.** "Roboto Serif for publication presets" is named as the
  intended font choice once presets exist; `sprezzature_figures.fonts`
  does expose a serif stack (`chrome_stack_for_theme`,
  `mono_stack_for_theme`, imported by generators like `make_bar.py`), so
  the font family a preset would need is already wired into the
  rendering path, only the preset's sizing and column-width logic around
  it is missing.
- **Vector output at exact physical dimensions.** `render_diagram.py`
  (documented in `references/ralph-eyeball-loop.md`) can already emit a
  Vega spec as SVG or PDF "at exact physical dimensions" by setting
  `width`/`height` in inches times DPI and passing `--ppi`. That is a
  general mechanism for print-accurate sizing, not a named journal
  preset, and it applies to the `render_diagram.py` path (diagram
  surfaces you supply), not to the 124-kind `make-figure` catalogue,
  which does not currently expose a DPI or physical-size argument at all
  (see `references/figure-catalog.md` for what that catalogue actually
  renders).

## What a real preset would need to specify, if built

For the record, so a future implementation has a concrete target rather
than a vague name: a journal preset conventionally fixes a column width
in inches or millimeters (a single-column figure and a two-column
figure are different widths at the same journal), a minimum font size at
that width so axis labels stay legible after the journal's own scaling,
and an output DPI or vector format the journal's production pipeline
accepts. None of those three numbers, for any of the four journals named
in `SKILL.md`'s promise, are sourced or verified anywhere in this
codebase; stating specific values here without a citation to each
journal's actual author guidelines would be exactly the kind of
unverifiable claim this file's own writing rules forbid. If you need
publication-accurate sizing today, get the target journal's current
figure specification directly from its author guidelines and set
`render_diagram.py`'s `width`/`height`/`--ppi` by hand; do not assume a
preset name here maps to correct numbers, because no such mapping has
been built.

## Recommendation

Either build this preset table for real, sourced from each journal's
current author guidelines, and update this file with citations, or
remove the "publication presets" bullet from `SKILL.md`'s House-style
section and its `references/` list once a decision is made not to build
it. Leaving the promise in `SKILL.md` while this file says "not
implemented" is the honest interim state, matching how the
`make_situation_map.py` gap is already handled elsewhere in the same
document, not a resolution either way.
