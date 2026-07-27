# Foundations — App Icons (favicon, PWA, touch icon)

## When to consult this file

- Designing or replacing the favicon, PWA icons, or any "app icon" surface
- Generating manifest icons for installable web apps

## Core principles

- **One subject, instantly readable.** An app icon should communicate its purpose at a glance, even at the smallest size.
- **Use a single, focused element.** Resist combining multiple shapes or words; they become noise at small sizes.
- **No text inside the icon** (the wordmark belongs to the OS-level label, not the artwork).
- **Avoid photo-realism.** Stylized, simple shapes scale better and feel native across themes.
- **Design for the smallest size first** (16–32 px favicon). If the silhouette fails there, redesign.
- **Provide both light and dark backgrounds** that work — test on white and black.
- **Use a consistent grid** so the subject feels centered and balanced.
- **Avoid transparency at canvas edges**: the OS applies its own mask/rounded corner.

## Web concrete rules

- **Favicon**: ship a 32×32 PNG, 16×16 PNG, and an SVG for modern browsers.
- **Touch icon**: 180×180 PNG, no transparency, no rounded corners (the OS adds them).
- **PWA / manifest**: at minimum 192×192 and 512×512 PNG; mark one `"purpose": "maskable"` so Android can crop.
- **Theme-color meta**: `<meta name="theme-color" content="#…">` matches the dominant background so the chrome blends in.

## Generate the set from a logo

The skill ships a Pillow-based generator. From a single logo PNG (or SVG + `--raster` fallback):

```bash
pip install -r sprezzature-publish/scripts/requirements-favicons.txt
python sprezzature-publish/scripts/favicons.py path/to/logo.png \
       --out public \
       --name "Site name" --short-name "Site" \
       --bg "#FFFFFF" \
       --theme-light "#FFFFFF" --theme-dark "#000000"
```

Produces under `public/`:

```text
favicon.svg              (when the input is SVG)
favicon.ico              multi-resolution (16, 32, 48)
favicon-16.png  favicon-32.png  favicon-48.png
apple-touch-icon.png     180×180, opaque, no rounded corners (OS adds them)
icon-192.png  icon-512.png
icon-maskable-512.png    PWA maskable, content in the central 80%
site.webmanifest
head.html                <link> and <meta> tags ready to paste into <head>
```

See `references/meta-tags.md` for the full meta-tag set this fits into.

## HTML head boilerplate

```html
<link rel="icon" href="/favicon.svg" type="image/svg+xml" />
<link rel="icon" href="/favicon-32.png" sizes="32x32" type="image/png" />
<link rel="icon" href="/favicon-16.png" sizes="16x16" type="image/png" />
<link rel="icon" href="/touch-icon-180.png" sizes="180x180" type="image/png" />
<link rel="manifest" href="/site.webmanifest" />
<meta name="theme-color" content="#FFFFFF" media="(prefers-color-scheme: light)" />
<meta name="theme-color" content="#000000" media="(prefers-color-scheme: dark)" />
```

## Manifest sketch

```json
{
  "name": "Sprezzature",
  "short_name": "Sprezzature",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ],
  "background_color": "#FFFFFF",
  "theme_color": "#007AFF",
  "display": "standalone"
}
```

## Checklist

- [ ] Recognizable at 16 px.
- [ ] Single subject, no text.
- [ ] Works on both light and dark UI chrome.
- [ ] Maskable icon provided for PWA installs.
- [ ] No transparency at canvas edges.
- [ ] `theme-color` set for both color schemes.
