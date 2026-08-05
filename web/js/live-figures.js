// Upgrade animated figure cards from a flat <img> to a live <object> when they
// scroll into view, so their SVG animation plays inline. An <img>-embedded SVG
// is a frozen picture; an <object type="image/svg+xml"> is a real document.
//
// The card object is made pointer-events:none so a click passes THROUGH to the
// enclosing .zoom button and opens the fullscreen lightbox (click-to-fullscreen
// must keep working) — animation needs no pointer events, so it still plays.
// FULL interactivity (CSS :hover/:focus isolation, tooltips) then works at large
// size in the lightbox, whose object is fully live. Static figures stay <img>.
//
// Only figures whose SVG carries interactivity/animation are tagged (data-live),
// and the swap is lazy (IntersectionObserver) so the page never holds 100+ live
// SVG documents at once.
(function () {
  var imgs = Array.prototype.slice.call(document.querySelectorAll('img[data-live]'));
  if (!imgs.length) return;

  function upgrade(img) {
    var src = img.getAttribute('data-live');
    var obj = document.createElement('object');
    obj.type = 'image/svg+xml';
    obj.setAttribute('aria-label', img.getAttribute('alt') || '');
    obj.className = img.className;                 // keep w-full etc.
    obj.style.width = '100%';
    obj.style.display = 'block';
    obj.style.pointerEvents = 'none';             // let the click reach .zoom (fullscreen)
    obj.data = src;
    img.replaceWith(obj);
  }

  if (!('IntersectionObserver' in window)) {       // old browser: just upgrade all
    imgs.forEach(upgrade);
    return;
  }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      if (!en.isIntersecting) return;
      io.unobserve(en.target);
      upgrade(en.target);
    });
  }, { rootMargin: '400px 0px' });                 // upgrade a little before visible
  imgs.forEach(function (img) { io.observe(img); });
})();
