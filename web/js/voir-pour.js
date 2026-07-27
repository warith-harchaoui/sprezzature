/*
 * voir-pour.js — the gallery "See it for… / Voir pour…" colour-vision viewer.
 *
 * Honest demo, not a mode the reader must pick: it applies a live SVG
 * feColorMatrix filter (Machado et al. 2009, the same matrices as
 * sprezzature-colors/scripts/simulate_cvd.py) to every gallery figure, so a viewer
 * can SEE what a colour-blind reader sees of the DEFAULT figure. The point is
 * that the default holds up. Choice is remembered in localStorage.
 *
 * Contract: a <select id="voir-pour"> with values
 *   normal | deuteranopia | protanopia | tritanopia | grayscale
 * and the filter <defs> both live inside <main id="main">. The value is written
 * to `#main[data-voir-pour]`, and CSS maps it to `filter: url(#fig-sim-…)` on the
 * figure images and objects.
 */
(function () {
  "use strict";
  var main = document.getElementById("main");
  var sel = document.getElementById("voir-pour");
  if (!main || !sel) return;

  function apply(v) {
    if (v && v !== "normal") main.setAttribute("data-voir-pour", v);
    else main.removeAttribute("data-voir-pour");
  }

  var saved = null;
  try { saved = localStorage.getItem("sprezzature-voir-pour"); } catch (e) { /* private mode */ }
  if (saved) { sel.value = saved; apply(saved); }

  sel.addEventListener("change", function () {
    apply(sel.value);
    try { localStorage.setItem("sprezzature-voir-pour", sel.value); } catch (e) { /* ignore */ }
  });
})();
