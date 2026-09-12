/**
 * nav.js — the phone half of the primary navigation.
 *
 * Above Tailwind's `sm` breakpoint the links live in the bar and this file has
 * nothing to do: the button and the panel are both `sm:hidden`, so the only
 * state it touches is invisible. Below it, the button is the sole way in.
 *
 * The panel's open/closed state is the `hidden` attribute rather than a class,
 * so the markup reads correctly with JavaScript off: no script, no button, and
 * the panel stays closed instead of hanging open under every page.
 */
(function () {
  var toggle = document.getElementById('nav-toggle');
  var panel = document.getElementById('nav-mobile');
  if (!toggle || !panel) return;

  function setOpen(open) {
    panel.hidden = !open;
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  }

  toggle.addEventListener('click', function () {
    setOpen(panel.hidden);
  });

  // Escape closes and hands focus back to the control that opened it, so a
  // keyboard reader is never left stranded inside a dismissed panel.
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && !panel.hidden) {
      setOpen(false);
      toggle.focus();
    }
  });

  // An in-page link (#skills) navigates without a reload: close so the anchor
  // it jumps to is not hidden behind the panel.
  panel.addEventListener('click', function (event) {
    if (event.target.closest('a')) setOpen(false);
  });

  // Rotating a phone to landscape can cross the breakpoint, which un-hides the
  // bar links; leaving the panel open would show both sets at once.
  if (window.matchMedia) {
    var wide = window.matchMedia('(min-width: 640px)');
    var onChange = function (event) {
      if (event.matches) setOpen(false);
    };
    if (wide.addEventListener) wide.addEventListener('change', onChange);
    else if (wide.addListener) wide.addListener(onChange);
  }
})();
