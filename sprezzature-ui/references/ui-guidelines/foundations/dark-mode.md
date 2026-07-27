# Foundations — Dark Mode


## Core principles

- **Design dark mode as a peer**, not an afterthought tinted darker.
- **Two palettes, one product.** Same visual hierarchy and meaning in both.
- **Lower contrast on big surfaces, keep contrast on text.** True black backgrounds make text shimmer on OLED; consider `#000000` only for chrome and `#1C1C1E`-ish for surfaces.
- **Soften pure white text**; the brain reads `#FFFFFF` on `#000000` as a strobe. `#F2F2F7` for body text is calmer.
- **Layered surfaces get lighter as they rise**, not darker. (Background `#000`, secondary `#1C1C1E`, tertiary `#2C2C2E`.)
- **Brand colors often need a darker-mode variant** to keep apparent brightness consistent.
- **Honor the system preference by default**, allow override.

## Implementation

Tailwind: `darkMode: 'media'` (system-driven) or `'class'` (user-override toggle). For both, add the `dark:` variant to every styled element. Recommended default: `darkMode: ['class', '[data-color-scheme="dark"]']` so you can also driven via a `data-color-scheme` attribute set by JS.

```html
<html data-color-scheme="auto"><!-- auto | light | dark --></html>
```

### Theme switcher (vanilla JS)

```js
function applyTheme(mode) {
  const html = document.documentElement;
  if (mode === 'auto') {
    const sys = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    html.dataset.colorScheme = sys;
  } else {
    html.dataset.colorScheme = mode;
  }
  localStorage.setItem('color-scheme', mode);
}

const saved = localStorage.getItem('color-scheme') ?? 'auto';
applyTheme(saved);
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
  if ((localStorage.getItem('color-scheme') ?? 'auto') === 'auto') applyTheme('auto');
});
```

## Concrete rules

1. **No `bg-white` / `bg-black` raw.** Use semantic tokens (`bg-surface-primary`, `bg-surface-secondary`).
2. **Every text class has a `dark:` peer.**
3. **Test imagery**: replace any white-background screenshots with dark-mode variants via `<picture>`.
4. **Inverted shadows**: pure-black shadows disappear; use lighter ambient halos for dark backgrounds, or skip shadows entirely.
5. **Translucent materials**: redo blur levels for dark; pure-black + blur loses contrast.

## Checklist

- [ ] Every interactive surface has a `dark:` variant.
- [ ] Body text not pure `#FFFFFF` on dark.
- [ ] Layered surfaces lighten as they rise.
- [ ] Imagery has dark-mode variant where needed.
- [ ] `theme-color` meta set for both schemes.
- [ ] User override available + persisted.
