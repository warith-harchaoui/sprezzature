# Platforms — Tablet

## When to consult this file

- Viewports 768–1024 px
- Touch-first but with more room than a phone

## Defaults

- **Two-column where it adds value**, otherwise single column with wider margins.
- **Master/detail** works well (list on the start, detail on the end) at ≥ 1024 px.
- **Keep top nav**, not bottom tab bar (more space).
- **Hover may exist** (with trackpad) but design touch-first.

## Patterns

- Side sheet (`right-0 w-96`) instead of full-screen sheets when room allows.
- Two-column form: pair related fields side-by-side at `md:grid-cols-2`.

## Checklist

- [ ] Layout adapts to ≥ 768 px without just stretching mobile.
- [ ] Touch targets still 44 px.
- [ ] No hover-only essential info.
