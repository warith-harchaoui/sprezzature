/* The gallery's two ways in: a name search, and the ten families as chips.
 *
 * 160 figures under ten headings is a catalogue you can only read top to
 * bottom. The search answers "where is the sankey"; it does not answer "what
 * have you got for a distribution", because the headings that would answer
 * that are a screen apart and carry no counts. The chips put those ten
 * families, and how many each holds, in one row above the grid.
 *
 * The two compose: a chip narrows to one family, the search narrows inside it.
 * With JavaScript off, every section is visible and nothing is lost.
 */
(function () {
  'use strict';
  var input = document.getElementById('fig-search');
  var sections = Array.prototype.slice.call(document.querySelectorAll('[data-fig-section]'));
  if (!sections.length) return;

  var empty = document.getElementById('fig-empty');
  var count = document.getElementById('fig-count');
  var chipRow = document.getElementById('fig-families');
  var figures = [];

  sections.forEach(function (s) {
    Array.prototype.slice.call(s.querySelectorAll('figure')).forEach(function (f) {
      var img = f.querySelector('img');
      var alt = f.querySelector('[data-alt]');
      f._t = (f.textContent + ' ' +
        (alt ? alt.getAttribute('data-alt') : '') + ' ' +
        (img ? img.getAttribute('src') : '')).toLowerCase();
      f._section = s.id;
      figures.push(f);
    });
  });

  var family = '';

  function apply() {
    var q = input ? input.value.trim().toLowerCase() : '';
    var shown = 0;
    figures.forEach(function (f) {
      var match = (!q || f._t.indexOf(q) !== -1) && (!family || f._section === family);
      f.hidden = !match;
      if (match) shown++;
    });
    sections.forEach(function (s) {
      s.hidden = !s.querySelector('figure:not([hidden])');
    });
    if (chipRow) {
      Array.prototype.slice.call(chipRow.querySelectorAll('[data-family]')).forEach(function (chip) {
        chip.setAttribute('aria-pressed', String(chip.getAttribute('data-family') === family));
      });
    }
    if (empty) empty.hidden = shown !== 0;
    if (count) {
      count.textContent = (q || family)
        ? count.getAttribute('data-template')
            .replace('{n}', String(shown))
            .replace('{total}', String(figures.length))
        : '';
    }
  }

  if (input) input.addEventListener('input', apply);

  if (chipRow) {
    chipRow.addEventListener('click', function (event) {
      var chip = event.target.closest('[data-family]');
      if (!chip) return;
      var value = chip.getAttribute('data-family');
      /* Clicking the active chip clears it, so "back to everything" is
         always one click on whatever is already under the cursor. */
      family = family === value ? '' : value;
      apply();
    });
  }

  apply();
})();
