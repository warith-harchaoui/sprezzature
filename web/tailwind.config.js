/**
 * Tailwind config for the sprezzature-* website — replaces the dev-only Play CDN
 * (cdn.tailwindcss.com) with a real, self-hosted, content-scanned build.
 * Mirrors the theme that used to live in each page's inline `tailwind.config`.
 * Build: from web/, `npx tailwindcss@3 -i css/tailwind-input.css -o css/app.css --minify`
 * (see css/BUILD.md).
 */
module.exports = {
  content: ['./**/*.html'],
  // The theme toggle sets data-color-scheme="dark" on <html> (js/theme.js).
  darkMode: ['class', '[data-color-scheme="dark"]'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Roboto', 'system-ui', 'sans-serif'],
        serif: ['Roboto Serif', 'serif'],
        mono: ['Roboto Mono', 'ui-monospace', 'monospace'],
      },
      colors: {
        // rgb(var(--x) / <alpha-value>) so opacity modifiers (bg-brand-navy/20)
        // keep working while the underlying RGB triplet swaps with
        // [data-color-mode] (see css/tailwind-input.css) between the
        // academic (Okabe-Ito) and corporate (Apple) palettes.
        brand: {
          blue: 'rgb(var(--brand-blue-rgb) / <alpha-value>)',
          bluedark: 'rgb(var(--brand-bluedark-rgb) / <alpha-value>)',
          bluelight: 'rgb(var(--brand-bluelight-rgb) / <alpha-value>)',
          navy: 'rgb(var(--brand-navy-rgb) / <alpha-value>)',
          // Text-only accent (links, inline emphasis): same hue as brand-blue,
          // but with independent light/dark values so body text always clears
          // WCAG AA 4.5:1 against both the white and #0B0B0C page backgrounds.
          // See css/tailwind-input.css for the per-theme/per-scheme values.
          linktext: 'rgb(var(--brand-linktext-rgb) / <alpha-value>)',
        },
      },
    },
  },
};
