/*
 * financial-markets.js — the two behaviours specific to the markets dashboard.
 * Theme toggle and fullscreen come from the shared theme.js / fullscreen.js.
 *
 *   1. KPI count-up — the headline figures animate from 0 (locale-aware).
 *   2. Rich tooltip — hover (or tap) a .hit mark inside a panel SVG and a
 *      floating tooltip follows the cursor with figures useful to a reader.
 *      The tooltip node carries data-fs-follow, so fullscreen.js re-homes it
 *      into the fullscreen element while a panel is fullscreen.
 */
(function () {
  "use strict";
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---- 1. KPI count-up ---- */
  function countUp(el) {
    var target = parseFloat(el.getAttribute("data-count"));
    if (isNaN(target)) return;
    var dec = parseInt(el.getAttribute("data-decimals") || "0", 10);
    var pre = el.getAttribute("data-prefix") || "", suf = el.getAttribute("data-suffix") || "";
    var fr = document.documentElement.lang === "fr";
    function render(v) { el.textContent = (v < 0 ? "-" : pre) + Math.abs(v).toFixed(dec).replace(".", fr ? "," : ".") + suf; }
    if (reduce) { render(target); return; }
    var dur = 900, start = null;
    (function frame(t) {
      if (start === null) start = t;
      var p = Math.min(1, (t - start) / dur), e = 1 - Math.pow(1 - p, 3);
      render(target * e);
      if (p < 1) requestAnimationFrame(frame); else render(target);
    })(performance.now());
  }
  function startKpis() {
    Array.prototype.forEach.call(document.querySelectorAll("[data-count]"), countUp);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", startKpis);
  else startKpis();

  /* ---- 2. rich tooltip driven by data-tip ---- */
  var tip = document.getElementById("fmtip");
  if (!tip) return;
  function esc(s) { return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
  function place(x, y) {
    var pad = 14, w = tip.offsetWidth, h = tip.offsetHeight;
    var left = x + pad, top = y + pad;
    if (left + w > window.innerWidth - 8) left = x - w - pad;
    if (top + h > window.innerHeight - 8) top = y - h - pad;
    tip.style.left = Math.max(8, left) + "px";
    tip.style.top = Math.max(8, top) + "px";
  }
  function show(hit, x, y) {
    var raw = hit.getAttribute("data-tip");
    if (!raw) return;
    var lines = raw.split("|");
    var html = '<div class="h">' + esc(lines[0]) + "</div>";
    for (var i = 1; i < lines.length; i++) html += '<div class="r">' + esc(lines[i]) + "</div>";
    tip.innerHTML = html;
    tip.hidden = false;
    place(x, y);
  }
  function hide() { tip.hidden = true; }

  // Mouse: hover. Touch: on tap (a finger emits no pointermove without a drag).
  document.addEventListener("pointermove", function (e) {
    if (e.pointerType === "touch") return;
    var hit = e.target.closest && e.target.closest(".hit");
    if (hit) show(hit, e.clientX, e.clientY);
    else if (!tip.hidden) hide();
  });
  document.addEventListener("pointerdown", function (e) {
    var hit = e.target.closest && e.target.closest(".hit");
    if (hit) { show(hit, e.clientX, e.clientY); e.preventDefault(); }
    else hide();
  });
  // Keyboard: focusing a .hit mark shows its tooltip near it.
  document.addEventListener("focusin", function (e) {
    var hit = e.target.closest && e.target.closest(".hit");
    if (!hit || !hit.getBoundingClientRect) return;
    var r = hit.getBoundingClientRect();
    show(hit, r.left + r.width / 2, r.top);
  });
  document.addEventListener("focusout", hide);
})();
