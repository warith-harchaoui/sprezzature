/*
 * fullscreen.js — the shared sprezzature figure-fullscreen module (convention copy).
 *
 * Canonical source: sprezzature-ui/assets/components/figure-fullscreen.html (‹JS›).
 * Keep this file in sync with it. Framework-free, multi-instance.
 *
 * Contract (data attributes):
 *   [data-fs]         a button that toggles fullscreen for its figure
 *   [data-fs-target]  the element that goes fullscreen (falls back to the
 *                     button's closest <figure>)
 *   [data-fs-follow]  a node (e.g. a cursor tooltip) re-homed INTO the
 *                     fullscreen element while fullscreen is active, then
 *                     restored, because the browser paints only the top-layer
 *                     element so a tooltip left on <body> would be invisible.
 *
 * Two non-obvious parts, both verified in Chrome: (1) Safari on iPhone and iPad has no element
 * Fullscreen API, so fall back to a fixed CSS overlay ([data-fs-pseudo] plus a
 * .fs-locked scroll lock on <html>); (2) the top-layer tooltip re-homing above.
 *
 * Each page styles its own fullscreen content via `:fullscreen` (native) and
 * `[data-fs-pseudo]` (iPhone/iPad) selectors; this module only drives the mechanism.
 */
(function () {
  "use strict";

  function host() {
    return document.fullscreenElement || document.webkitFullscreenElement
        || document.querySelector("[data-fs-pseudo]") || document.body;
  }

  var followers = Array.prototype.slice.call(document.querySelectorAll("[data-fs-follow]"));
  function rehome(into) {
    followers.forEach(function (n) {
      if (!n._home) n._home = n.parentNode;
      (into || n._home).appendChild(n);
    });
  }

  function targetOf(btn) { return btn.closest("[data-fs-target]") || btn.closest("figure"); }

  function enter(card) {
    var req = card.requestFullscreen || card.webkitRequestFullscreen;
    if (req) { req.call(card); return; }                 // native path (fullscreenchange fires)
    card.setAttribute("data-fs-pseudo", "");             // iPhone/iPad: no element Fullscreen API
    card.classList.add("is-fs");
    document.documentElement.classList.add("fs-locked");
    rehome(card);
    card.dispatchEvent(new CustomEvent("sprezzature:fullscreenchange", { bubbles: true, detail: { on: true, host: card } }));
  }
  function exitPseudo(card) {
    card.removeAttribute("data-fs-pseudo");
    card.classList.remove("is-fs");
    document.documentElement.classList.remove("fs-locked");
    rehome(null);
    card.dispatchEvent(new CustomEvent("sprezzature:fullscreenchange", { bubbles: true, detail: { on: false, host: document.body } }));
  }

  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-fs]"); if (!btn) return;
    var card = targetOf(btn); if (!card) return;
    e.stopPropagation();
    var pseudo = document.querySelector("[data-fs-pseudo]");
    if (pseudo) { exitPseudo(pseudo); return; }
    if (document.fullscreenElement || document.webkitFullscreenElement)
      (document.exitFullscreen || document.webkitExitFullscreen).call(document);
    else enter(card);
  });

  function onNativeChange() {
    var fsEl = document.fullscreenElement || document.webkitFullscreenElement;
    document.querySelectorAll("[data-fs-target]").forEach(function (c) { c.classList.toggle("is-fs", c === fsEl); });
    rehome(fsEl || null);
    (fsEl || document).dispatchEvent(new CustomEvent("sprezzature:fullscreenchange", { bubbles: true, detail: { on: !!fsEl, host: fsEl || document.body } }));
  }
  document.addEventListener("fullscreenchange", onNativeChange);
  document.addEventListener("webkitfullscreenchange", onNativeChange);
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    var pseudo = document.querySelector("[data-fs-pseudo]"); if (pseudo) exitPseudo(pseudo);
  });

  /* Optional shared cursor tooltip, driven by .hit[data-tip]. Active only when a
     page provides a #fig-tip element (dashboards). The figure gallery keeps its
     hover inside the SVG, so this block stays dormant there. */
  var tip = document.getElementById("fig-tip");
  if (tip) {
    var esc = function (s) { return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); };
    var show = function (hit, x, y) {
      var raw = hit.getAttribute("data-tip"); if (!raw) return;
      var lines = raw.split("|");
      tip.innerHTML = "<b>" + esc(lines[0]) + "</b>" + lines.slice(1).map(esc).join("<br>");
      var h = host(); if (tip.parentNode !== h) h.appendChild(tip);
      tip.hidden = false;
      var pad = 14, w = tip.offsetWidth, ht = tip.offsetHeight;
      var left = x + pad, top = y + pad;
      if (left + w > window.innerWidth - 8) left = x - w - pad;
      if (top + ht > window.innerHeight - 8) top = y - ht - pad;
      tip.style.left = Math.max(8, left) + "px";
      tip.style.top = Math.max(8, top) + "px";
    };
    document.addEventListener("pointermove", function (e) {
      if (e.pointerType === "touch") return;
      var hit = e.target.closest && e.target.closest(".hit");
      if (hit) show(hit, e.clientX, e.clientY); else if (!tip.hidden) tip.hidden = true;
    });
    document.addEventListener("pointerdown", function (e) {
      var hit = e.target.closest && e.target.closest(".hit");
      if (hit) { show(hit, e.clientX, e.clientY); e.preventDefault(); } else tip.hidden = true;
    });
    document.addEventListener("focusin", function (e) {
      var hit = e.target.closest && e.target.closest(".hit"); if (!hit) return;
      var r = hit.getBoundingClientRect(); show(hit, r.left + r.width / 2, r.top);
    });
    document.addEventListener("focusout", function () { tip.hidden = true; });
  }
})();
