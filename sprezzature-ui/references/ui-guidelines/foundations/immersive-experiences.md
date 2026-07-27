# Foundations — Immersive Experiences


## When to consult this file

- Full-bleed, full-screen, or "kiosk-mode" web experiences
- 3D / WebXR / AR Quick Look surfaces
- Video-first players, slideshows, and presentation modes

## Core principles

- **Stay in flow.** Hide chrome, fade controls, let content breathe.
- **Provide an obvious exit.** Always show an unambiguous way out: a close button, an Escape hotkey announcement, or a tap target.
- **Treat motion with care.** Smooth, slow, predictable. Honor `prefers-reduced-motion`.
- **Audio is opt-in.** Never auto-play sound. Mute by default with a clear unmute affordance.
- **Comfort first in 3D/XR.** Avoid jarring camera moves; let the user lead.
- **Respect device boundaries.** Don't lock orientation or block system gestures unless content truly requires it.

## Concrete rules — web

1. **Fullscreen API**: use `requestFullscreen()` only on direct user gesture.
2. **`document.fullscreenElement`** drives UI; never assume fullscreen state from your own code.
3. **Show a persistent or hover-revealed close (`Escape` also closes).**
4. **Disable text selection** only inside the immersive area, not the whole page (`select-none` Tailwind utility).
5. **Idle hide** controls after ~3 s of no pointer motion; reveal on motion or key press.
6. **Preserve scroll position** when entering/exiting.
7. **WebXR / 3D**: provide a 2D fallback for users without supported hardware.

## Pattern — fullscreen slideshow with idle-hide chrome

```html
<section id="show" class="relative h-screen w-screen overflow-hidden bg-black text-white select-none">
  <img id="slide" src="" alt="" class="absolute inset-0 h-full w-full object-contain">
  <div id="chrome" class="absolute inset-x-0 top-0 flex items-center justify-end gap-2 p-4 transition-opacity duration-300">
    <button id="exit" aria-label="Exit fullscreen" class="grid h-11 w-11 place-items-center rounded-full bg-white/10 backdrop-blur hover:bg-white/20">
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 6l12 12M18 6L6 18" stroke-linecap="round"/></svg>
    </button>
  </div>
</section>
<script type="module">
  const show = document.getElementById('show');
  const chrome = document.getElementById('chrome');
  let timer;
  const reveal = () => { chrome.style.opacity = '1'; clearTimeout(timer); timer = setTimeout(() => chrome.style.opacity = '0', 3000); };
  show.addEventListener('pointermove', reveal);
  show.addEventListener('keydown', reveal);
  document.getElementById('exit').addEventListener('click', () => document.exitFullscreen?.());
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') document.exitFullscreen?.(); });
  reveal();
</script>
```

## Checklist

- [ ] Exit is always reachable.
- [ ] `Escape` closes immersive mode.
- [ ] Idle hide ≥ 2 s, reveal on motion.
- [ ] No auto-play audio.
- [ ] Reduced-motion honored.
- [ ] Fallback for unsupported hardware (no WebXR, no fullscreen API).
