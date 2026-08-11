// Gallery figure re-theming — swaps each figures.html card's thumbnail (<img
// src>) and lightbox source (<button data-src>) between the corporate
// (img/figures/<kind>.*) and academic (img/figures/academic/<kind>.*) asset,
// driven by the same [data-color-mode] the site-wide 🏫/🏭 toggle sets
// (js/color-mode.js). The academic path is the source of truth (declared in
// figures.html as data-src-academic); the corporate path is derived by
// stripping "academic/" from it, so no second data attribute is needed.
(function () {
  function corporatePath(academicPath) {
    return academicPath.replace('img/figures/academic/', 'img/figures/');
  }

  function apply() {
    var academic = document.documentElement.getAttribute('data-color-mode') !== 'corporate';
    var nodes = document.querySelectorAll('[data-src-academic]');
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      var acad = el.getAttribute('data-src-academic');
      var target = academic ? acad : corporatePath(acad);
      if (el.tagName === 'IMG') {
        if (el.getAttribute('src') !== target) el.setAttribute('src', target);
      } else if (el.getAttribute('data-src') !== target) {
        el.setAttribute('data-src', target);
      }
    }
  }

  function wire() {
    apply();
    var toggle = document.getElementById('color-mode-toggle');
    // setTimeout: run after color-mode.js's own click handler has updated
    // data-color-mode, regardless of listener attachment order.
    if (toggle) toggle.addEventListener('click', function () { setTimeout(apply, 0); });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wire);
  else wire();
})();
