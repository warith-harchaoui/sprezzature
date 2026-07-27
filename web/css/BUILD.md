# Building the site stylesheet

`app.css` is a real, self-hosted Tailwind build — it replaces the dev-only
Play CDN (`cdn.tailwindcss.com`), which is not meant for production. It is
content-scanned, so it ships only the utility classes the pages actually
use (~20 KB).

## Rebuild after changing any page's classes

From `web/`:

```sh
npx tailwindcss@3 -c tailwind.config.js -i css/tailwind-input.css -o css/app.css --minify
```

- `tailwind.config.js` — the theme (Roboto fonts, `brand-*` colours) and the
  `data-color-scheme="dark"` dark-mode strategy that used to live inline in
  every page's `<script>tailwind.config = …</script>`.
- `css/tailwind-input.css` — just the three `@tailwind` layers.
- Output `css/app.css` is committed so the site needs no build step to serve.

Every page links it with `<link rel="stylesheet" href="css/app.css">`
(root pages) or `href="../css/app.css">` (pages under `fr/`).

If a class only ever appears in JavaScript-generated markup that the scanner
can't see, add it to a `safelist` in `tailwind.config.js` and rebuild.
