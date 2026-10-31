/* Two facets over the map gallery: where the plate is, and what it shows.
 *
 * The page used to carry its plates in generator order under two headings,
 * which answers "what did you build" and not "what have you got on Africa".
 * Every card declares data-region and data-kind; the chips below the heading
 * are two independent toggles over those, and the pair ANDs.
 *
 * Progressive enhancement: with JavaScript off every card is visible and the
 * chips do nothing, which is the same page the site shipped before.
 */
(function () {
  'use strict';
  var gallery = document.querySelector('[data-plate-gallery]');
  if (!gallery) return;

  var grid = gallery.querySelector('#plate-grid');
  var cards = Array.prototype.slice.call(grid.querySelectorAll('figure'));
  var chips = Array.prototype.slice.call(gallery.querySelectorAll('[data-facet]'));
  var count = gallery.querySelector('#plate-count');
  var empty = gallery.querySelector('#plate-empty');
  var template = count ? count.getAttribute('data-template') : '';
  var state = { region: '', kind: '' };

  function apply() {
    var shown = 0;
    cards.forEach(function (card) {
      var ok =
        (!state.region || card.getAttribute('data-region') === state.region) &&
        (!state.kind || card.getAttribute('data-kind') === state.kind);
      card.hidden = !ok;
      if (ok) shown++;
    });
    chips.forEach(function (chip) {
      var facet = chip.getAttribute('data-facet');
      chip.setAttribute('aria-pressed', String(state[facet] === chip.getAttribute('data-value')));
    });
    if (count && template) {
      count.textContent = template
        .replace('{n}', String(shown))
        .replace('{total}', String(cards.length));
    }
    if (empty) empty.hidden = shown !== 0;
  }

  chips.forEach(function (chip) {
    chip.addEventListener('click', function () {
      var facet = chip.getAttribute('data-facet');
      var value = chip.getAttribute('data-value');
      /* Clicking the chip that is already on clears that facet, so a reader
         never has to hunt for the "All" chip to get back. */
      state[facet] = state[facet] === value ? '' : value;
      apply();
    });
  });

  apply();
})();
