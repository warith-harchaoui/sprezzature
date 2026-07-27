// Shared theme toggle — 🌞 light / 🌛 dark, persisted in localStorage.
// The no-flash attribute is set inline in <head>; this only wires the button.
(function () {
  var root = document.documentElement, KEY = 'sprezzature-theme';
  function current() { return root.getAttribute('data-color-scheme') === 'dark' ? 'dark' : 'light'; }
  function paint() {
    var dark = current() === 'dark', b = document.getElementById('theme-toggle');
    if (!b) return;
    b.textContent = dark ? '🌛' : '🌞';
    b.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
    b.setAttribute('aria-pressed', String(dark));
  }
  function wire() {
    var b = document.getElementById('theme-toggle');
    if (!b) return;
    paint();
    b.addEventListener('click', function () {
      var next = current() === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-color-scheme', next);
      try { localStorage.setItem(KEY, next); } catch (e) {}
      paint();
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wire);
  else wire();
})();
