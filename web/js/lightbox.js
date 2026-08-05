// Click a gallery figure (a .zoom button) to view it large in a native <dialog>.
// The dialog gives Escape-to-close, a focus trap and a backdrop for free.
//
// SVG figures are embedded as a live <object> (not <img>) so their built-in
// interactivity works at full size: CSS :hover / :focus isolation, native
// <title> tooltips and any SVG animation all fire, because an <object> renders
// the SVG as a real document rather than a flat picture. Raster figures (PNG)
// stay as <img>. This is the fullscreen half of the gallery's "figures are
// genuinely interactive" contract; the cards do the same inline.
(function () {
  var dlg = document.getElementById('lightbox');
  if (!dlg) return;
  var fig = dlg.querySelector('figure');
  var img = dlg.querySelector('[data-lb-img]');
  var cap = dlg.querySelector('[data-lb-cap]');
  var VIEW = 'h-[85vh] w-[92vw] rounded-lg bg-white object-contain shadow-2xl';

  function clearObject() {
    var o = fig.querySelector('object[data-lb-obj]');
    if (o) o.remove();
  }

  function open(src, alt) {
    cap.textContent = alt;
    clearObject();
    if (/\.svg(\?|#|$)/i.test(src)) {
      img.style.display = 'none';
      img.removeAttribute('src');
      var obj = document.createElement('object');
      obj.setAttribute('data-lb-obj', '');
      obj.type = 'image/svg+xml';
      obj.setAttribute('aria-label', alt);
      obj.className = VIEW;
      obj.data = src;                 // set data last so it loads once attached
      img.insertAdjacentElement('afterend', obj);
    } else {
      img.style.display = '';
      img.src = src;
      img.alt = alt;
    }
    if (typeof dlg.showModal === 'function') dlg.showModal(); else dlg.setAttribute('open', '');
  }

  function close() {
    if (typeof dlg.close === 'function') dlg.close(); else dlg.removeAttribute('open');
    img.removeAttribute('src');
    clearObject();
  }

  document.addEventListener('click', function (e) {
    var z = e.target.closest && e.target.closest('.zoom');
    if (z) { e.preventDefault(); open(z.getAttribute('data-src'), z.getAttribute('data-alt')); return; }
    if (!dlg.open) return;
    if (e.target.closest('[data-lb-close]')) { close(); return; }          // ✕ button
    if (dlg.contains(e.target) && !e.target.closest('figure')) close();    // click outside the figure
  });

  // Live <object> cards are pointer-events:auto (so native hover/<title>
  // tooltips work), which means a click inside one never bubbles to the
  // document click handler above — it's an isolated document. The card's own
  // injected script (scripts/_interactive.py, sprezzature-figures repo) posts
  // this message instead; find which <object> sent it via its contentWindow
  // and open the lightbox with the same data-src/data-alt the .zoom wrapper
  // would have supplied.
  window.addEventListener('message', function (e) {
    if (!e.data || e.data.szFig !== 1 || e.data.type !== 'open-fullscreen') return;
    var objs = document.querySelectorAll('object');
    for (var i = 0; i < objs.length; i++) {
      if (objs[i].contentWindow === e.source) {
        var z = objs[i].closest('.zoom');
        if (z) open(z.getAttribute('data-src'), z.getAttribute('data-alt'));
        return;
      }
    }
  });
})();
