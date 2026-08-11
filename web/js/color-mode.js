// Shared color-mode toggle — 🏫 academic (Okabe-Ito, CVD-safe) / 🏭 corporate (Apple palette),
// persisted in localStorage. The no-flash attribute is set inline in <head>; this only wires the button.
(function () {
  var root = document.documentElement, KEY = 'sprezzature-color-mode';
  function current() { return root.getAttribute('data-color-mode') === 'corporate' ? 'corporate' : 'academic'; }
  function paint() {
    var corporate = current() === 'corporate', b = document.getElementById('color-mode-toggle');
    if (!b) return;
    b.textContent = corporate ? '🏭' : '🏫';
    b.setAttribute('aria-label', corporate ? 'Switch to academic colors' : 'Switch to corporate colors');
    b.setAttribute('aria-pressed', String(corporate));
  }
  function wire() {
    var b = document.getElementById('color-mode-toggle');
    if (!b) return;
    paint();
    b.addEventListener('click', function () {
      var next = current() === 'corporate' ? 'academic' : 'corporate';
      root.setAttribute('data-color-mode', next);
      try { localStorage.setItem(KEY, next); } catch (e) {}
      paint();
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wire);
  else wire();
})();
