# Foundations — Images


## When to consult this file

- Inserting product imagery, illustrations, photos, screenshots
- Building a media-heavy surface (hero, gallery, marketing page)

## Core principles

- **Crisp at every density.** Ship at native resolution and let CSS scale down; never let the browser upscale.
- **One purpose per image.** Decorative vs. informative: assistive tech handles them differently.
- **Respect aspect ratio.** Use `aspect-ratio` to reserve space and prevent layout shift.
- **Mind both color schemes.** Pure white backgrounds shock in dark mode; provide a dark variant or a subtle plate.
- **Don't override system content with overlay text** that fails contrast.
- **Honor reduced-data preferences** — defer non-critical imagery on `prefers-reduced-data: reduce`.

## Concrete rules — web

1. **Use `<img>` with `width` and `height`** so the browser reserves space (no CLS).
2. **Decorative images**: `alt=""` and `role="presentation"`.
3. **Informative images**: `alt="…"` describes the content, not the file (`alt="Person walking a dog"` not `alt="dog.png"`).
4. **Responsive sources**: `srcset` + `sizes`, or `<picture>` for art direction / theme switching.
5. **Lazy-load below the fold**: `loading="lazy" decoding="async"`.
6. **Use modern formats** with fallback: AVIF → WebP → JPEG/PNG.
7. **Theme-aware images**: `<picture>` with `media="(prefers-color-scheme: dark)"`.
8. **Aspect ratio**: Tailwind `aspect-video`, `aspect-square`, or `aspect-[4/3]`.

## Patterns

### Responsive theme-aware image

```html
<picture>
  <source srcset="/hero-dark.avif" media="(prefers-color-scheme: dark)" type="image/avif">
  <source srcset="/hero.avif" type="image/avif">
  <source srcset="/hero.webp" type="image/webp">
  <img src="/hero.jpg" alt="Living room with warm sunset light"
       width="1600" height="900" class="aspect-video w-full rounded-2xl object-cover"
       loading="lazy" decoding="async">
</picture>
```

### Decorative image

```html
<img src="/pattern.svg" alt="" role="presentation" aria-hidden="true"
     class="pointer-events-none absolute inset-0 -z-10 h-full w-full object-cover opacity-20">
```

### Avatar with fallback

```html
<span class="grid h-10 w-10 place-items-center overflow-hidden rounded-full bg-surface-secondary text-sm font-medium text-label-secondary">
  <img src="/u/123.jpg" alt="" class="h-full w-full object-cover" onerror="this.replaceWith(this.nextElementSibling)">
  <span aria-hidden="true">WH</span>
</span>
```

## AI-drafted alt text

When the author has not supplied `alt`, the skill drafts it with a **local vision model running on Ollama** (`qwen3-vl:8b`). Local-only: nothing leaves the machine. Runtime is Python 3.9+.

Install once (cross-platform):

```bash
pip install -r sprezzature-vision/scripts/requirements-alt-text.txt
python sprezzature-vision/scripts/install_alt_ai.py
```

Generate alt for an image, per the W3C / WAI decision tree:

```bash
# informative (default)
python sprezzature-vision/scripts/alt_from_ollama.py ./public/hero.jpg

# functional (inside <a> or <button>)
python sprezzature-vision/scripts/alt_from_ollama.py --kind functional --context "Submit form" ./public/icons/check.png

# complex (chart, diagram) — pair with a long description in <figcaption>
python sprezzature-vision/scripts/alt_from_ollama.py --kind complex --context "Weekly active users" ./public/chart.png
```

Output is one line ≤ 150 characters at a word boundary (no trailing `…`). For decorative images, emit `alt=""` directly (the script returns empty when called with `--kind decorative`). Do **not** add `role="presentation"` or `aria-hidden="true"`; `alt=""` alone is the WAI-recommended signal.

Full guidance (W3C decision tree, prompt rules, server-side proxy pattern for browser calls, review workflow, failure modes) in `references/alt-text-ai.md`.

## Checklist

- [ ] Every `<img>` has explicit `width` and `height`.
- [ ] `alt` reflects meaning, or empty for decoration.
- [ ] Modern format with fallback.
- [ ] Lazy-loaded below the fold.
- [ ] Dark-mode variant where needed.
- [ ] No layout shift on load.
- [ ] AI-drafted `alt` tagged with `data-alt-source="ai"` until a human reviews.
