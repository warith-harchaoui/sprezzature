# Stack: Vanilla JavaScript

This skill emits browser-native JavaScript only. No bundler is required to read the output, though one is welcome for production.

## Module loading

Always use ES modules. Drop the file at any URL and import directly.

```html
<script type="module" src="/app.js"></script>
```

```js
// app.js
import { mountDialog } from './ui/dialog.js';
import { i18n }        from './i18n.js';

mountDialog(document.querySelector('#confirm'));
```

No CommonJS, no AMD, no global `window.X = …` polluters except deliberate debug hooks behind a `__dev` flag.

## File layout (recommended)

```text
src/
├── index.html
├── styles/
│   └── app.css                 # Tailwind directives + @import './fonts.css'
├── fonts/                      # ship the three Roboto families here (mirror of assets/fonts/roboto*/)
├── app.js                      # entry
├── ui/
│   ├── dialog.js
│   ├── menu.js
│   ├── theme.js
│   └── form.js
├── i18n.js
└── data/                       # static JSON or fetch wrappers
```

## Custom elements (use sparingly)

Only define a custom element when the widget is **truly reusable** (used in 3+ places) and has internal state worth encapsulating. Otherwise, a plain function + template is enough.

```js
class CopyButton extends HTMLElement {
  static observedAttributes = ['data-value'];
  connectedCallback() {
    this.innerHTML = `<button class="rounded-full bg-brand-blue px-4 py-2 text-white">Copy</button>`;
    this.querySelector('button').addEventListener('click', () => {
      navigator.clipboard.writeText(this.dataset.value || '');
    });
  }
}
customElements.define('copy-button', CopyButton);
```

```html
<copy-button data-value="hello"></copy-button>
```

## Templates

For repeated DOM fragments, use `<template>`:

```html
<template id="row">
  <li class="flex items-center justify-between px-4 py-3 border-b border-separator/50">
    <span data-slot="label"></span>
    <span data-slot="value" class="text-label-secondary"></span>
  </li>
</template>
```

```js
const tpl = document.getElementById('row');
function renderRow({ label, value }) {
  const node = tpl.content.firstElementChild.cloneNode(true);
  node.querySelector('[data-slot="label"]').textContent = label;
  node.querySelector('[data-slot="value"]').textContent = value;
  return node;
}
```

## Event delegation

Bind one listener high in the tree, route by `target.closest(selector)`.

```js
document.addEventListener('click', (e) => {
  const btn = e.target.closest('[data-action]');
  if (!btn) return;
  switch (btn.dataset.action) {
    case 'open-cart': openCart(); break;
    case 'close':     closeNearestDialog(btn); break;
  }
});
```

## State

For most pages, a small store object is enough:

```js
const store = {
  state: { count: 0 },
  subs: new Set(),
  set(patch) {
    Object.assign(this.state, patch);
    this.subs.forEach(fn => fn(this.state));
  },
  subscribe(fn) { this.subs.add(fn); fn(this.state); return () => this.subs.delete(fn); },
};
```

For larger apps, consider a tiny library (Zustand-vanilla, nanostores). Avoid Redux-scale machinery.

## Dialogs (native)

```js
export function mountDialog(dlg) {
  dlg.addEventListener('click', (e) => { if (e.target === dlg) dlg.close('cancel'); });
  // Escape closes natively.
}
```

```html
<dialog id="confirm" class="w-full max-w-sm rounded-2xl bg-surface-primary p-5 backdrop:bg-black/40 dark:bg-surface-primary-dark">
  …
</dialog>
```

`<dialog>.showModal()` is the right API. It traps focus, restores it on close, and supports `Escape` natively.

## Forms

Trust the platform:

```html
<form id="signin" class="space-y-3" novalidate>
  <label class="block">
    <span class="text-sm font-medium">Email</span>
    <input name="email" type="email" autocomplete="email" required
           class="mt-1 w-full rounded-xl border border-separator bg-surface-secondary px-3 py-2.5 dark:bg-surface-secondary-dark" />
  </label>
  <button class="min-h-11 w-full rounded-full bg-brand-blue px-4 font-semibold text-white">Sign in</button>
</form>
```

```js
const form = document.getElementById('signin');
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(form));
  if (!form.checkValidity()) { form.reportValidity(); return; }
  await fetch('/api/signin', { method: 'POST', body: JSON.stringify(data), headers: { 'Content-Type': 'application/json' } });
});
```

## Theme switching

```js
// theme.js
const KEY = 'color-scheme';
export function applyTheme(mode = localStorage.getItem(KEY) ?? 'auto') {
  const sys = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  document.documentElement.dataset.colorScheme = mode === 'auto' ? sys : mode;
  localStorage.setItem(KEY, mode);
}
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
  if ((localStorage.getItem(KEY) ?? 'auto') === 'auto') applyTheme('auto');
});
applyTheme();
```

### Toggle UI control: 🌞 Light / 🌚 Dark / 🌗 Auto

Every page that ships dark-mode peers also ships a visible toggle.
**Auto is the default** so a fresh visitor inherits the OS choice and
never gets surprised by a hard-coded scheme.

**Canonical placement, in priority order:**

1. **Top-right of any sticky header**, immediately before the primary
   action (Sign in / Get started). Standard placement across the major
   docs sites and developer tools, so users look there first.
2. **Footer**, far-right column: for content-only sites with no
   sticky chrome (long-form docs that opt out of the header).
3. **Fixed bottom-right corner** with `safe-area-inset` padding: for
   single-card pages, embedded widgets, and the `cli-gui-demo` log
   viewer that have no global chrome at all.

**Control shape:**

- **Segmented control (3 radios)** when there is space (≥ `sm`
  breakpoint, ~640 px). One button per mode, emoji glyph + text label
  side by side, `role="radiogroup"` / `role="radio"` /
  `aria-checked`, arrow-key roving focus.
- **Icon-only cycle button** (`Auto → Light → Dark → Auto`) on
  narrower viewports. The visible glyph reflects the *current* mode;
  the *next* mode is announced via `aria-label`.

Both variants and the full vanilla-JS wiring (clicks, keyboard,
sync-across-instances, system-change pass-through) live in
[`sprezzature-ui/assets/components/theme-toggle.html`](../assets/components/theme-toggle.html).
Drop the block, import `applyTheme` from `theme.js`, and it works,
with no other state to wire.

## i18n (EN / FR)

```js
// i18n.js
const dict = {
  en: { signIn: 'Sign in', delete: 'Delete', cancel: 'Cancel' },
  fr: { signIn: 'Se connecter', delete: 'Supprimer', cancel: 'Annuler' },
};
const lang = (navigator.language || 'en').startsWith('fr') ? 'fr' : 'en';
document.documentElement.lang = lang;
export const t = (k) => dict[lang][k] ?? dict.en[k] ?? k;
```

## Accessibility helpers

```js
// Live region for ad-hoc status announcements.
const live = Object.assign(document.createElement('p'), {
  className: 'sr-only', role: 'status',
});
live.setAttribute('aria-live', 'polite');
document.body.appendChild(live);
export const announce = (msg) => { live.textContent = ''; setTimeout(() => live.textContent = msg, 50); };
```

## Performance hygiene

- Defer non-critical scripts (`<script type="module" defer src="…">`).
- Use `IntersectionObserver` to lazy-mount components.
- Use `requestIdleCallback` for non-urgent setup.
- Never block first paint with synchronous JSON fetches.

## Anti-patterns (never emit)

- `document.write`
- Inline `onclick="…"` on HTML (use `addEventListener` from a module).
- Reading layout in a loop (causes thrash): batch reads, then writes.
- `eval`, `new Function`.
- Globally mutating `Array.prototype` etc.
