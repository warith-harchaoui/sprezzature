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
        brand: {
          blue: '#007AFF',
          bluedark: '#0A84FF',
          bluelight: '#CCE4FF',
          navy: '#0A4DA0',
        },
      },
    },
  },
};
