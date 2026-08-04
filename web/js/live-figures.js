// Upgrade interactive figure cards from a flat <img> to a live <object> when
// they scroll into view. An <img>-embedded SVG is a static picture: its CSS
// :hover / :focus isolation, native <title> tooltips and animations never fire.
// An <object type="image/svg+xml"> renders the SVG as a real document, so all
// of that works inline in the card — matching what the fullscreen lightbox does.
//
// Only figures whose SVG actually carries interactivity/animation are tagged
// (data-live in the HTML), and the swap is lazy (IntersectionObserver) so the
// page never holds 100+ live SVG documents at once. Static figures stay <img>
// and keep click-to-zoom via the lightbox.
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
