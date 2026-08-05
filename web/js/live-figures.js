// Upgrade animated figure cards from a flat <img> to a live <object> when they
// scroll into view, so their SVG's hover tooltips and animation work inline.
// An <img>-embedded SVG is a frozen picture; an <object type="image/svg+xml">
// is a real document.
//
// The card object is pointer-events:auto so native :hover/:focus isolation and
// <title> tooltips fire right on the card (an <object> is an isolated document,
// so a click inside it can never bubble out to the page's .zoom button click
// handler). Click-to-fullscreen instead runs through a postMessage bridge: the
// SVG's own injected script (scripts/_interactive.py, sprezzature-figures repo)
// posts {szFig:1,type:'open-fullscreen'} on a background click, and
// lightbox.js listens for it and opens the dialog. Static figures stay <img>.
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
    obj.style.pointerEvents = 'auto';             // hover/<title> tooltips fire; click uses the postMessage bridge
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
