// Click a gallery image (a .zoom button) to view it large in a native <dialog>.
// The dialog gives Escape-to-close, a focus trap and a backdrop for free.
(function () {
  var dlg = document.getElementById('lightbox');
  if (!dlg) return;
  var img = dlg.querySelector('[data-lb-img]');
  var cap = dlg.querySelector('[data-lb-cap]');
  function open(src, alt) {
    img.src = src; img.alt = alt; cap.textContent = alt;
    if (typeof dlg.showModal === 'function') dlg.showModal(); else dlg.setAttribute('open', '');
  }
  function close() {
    if (typeof dlg.close === 'function') dlg.close(); else dlg.removeAttribute('open');
    img.removeAttribute('src');
  }
  document.addEventListener('click', function (e) {
    var z = e.target.closest && e.target.closest('.zoom');
    if (z) { e.preventDefault(); open(z.getAttribute('data-src'), z.getAttribute('data-alt')); return; }
    if (!dlg.open) return;
    if (e.target.closest('[data-lb-close]')) { close(); return; }          // ✕ button
    if (dlg.contains(e.target) && !e.target.closest('figure')) close();    // click outside the image
  });
})();
