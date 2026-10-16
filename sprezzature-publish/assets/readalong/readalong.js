/* readalong — follow the narration, sentence by sentence.
 *
 * The whole module is about forty lines of logic. That is the point: the
 * cues come from a WebVTT file the browser parses itself through `<track>`,
 * so there is no parser here, no timer polling `currentTime`, and no clock
 * of our own to drift away from the audio.
 *
 * Accessibility decisions, each deliberate
 * ----------------------------------------
 * - The highlight is visual only. No live region, no `aria-current`: this
 *   feature exists for readers who are *looking* at the page, and announcing
 *   every sentence would make the page hostile to anyone on a screen reader,
 *   who already has speech and does not need a second voice.
 * - Auto-scroll is instant under `prefers-reduced-motion`, not suppressed.
 *   Smooth scrolling is the vestibular trigger; a jump is not animation, and
 *   removing the scroll entirely would leave a reader hunting for the
 *   highlight they asked to follow.
 * - Scrolling happens only when the sentence is off screen, so a reader who
 *   has scrolled ahead is not dragged back on every cue.
 * - Sentences are focusable and activate on Enter or Space as well as click,
 *   so seeking by sentence is reachable without a mouse.
 */

const REDUCED_MOTION = window.matchMedia('(prefers-reduced-motion: reduce)');

function isOffScreen(element) {
  const box = element.getBoundingClientRect();
  return box.top < 0 || box.bottom > window.innerHeight;
}

function reveal(element) {
  if (!isOffScreen(element)) return;
  element.scrollIntoView({
    block: 'center',
    behavior: REDUCED_MOTION.matches ? 'auto' : 'smooth',
  });
}

function wire(root) {
  const audio = root.querySelector('[data-ra-audio]');
  const track = audio && audio.textTracks && audio.textTracks[0];
  if (!audio || !track) return;

  // `hidden` rather than `showing`: the cues drive a highlight, they are not
  // a caption overlay. A `metadata` track shown over an audio element would
  // be noise, but it still has to be non-`disabled` for `cuechange` to fire.
  track.mode = 'hidden';

  const sentences = document.querySelectorAll('.ra-s');
  let current = null;

  // The highlight is only ever *moved*, never cleared on the way past. Two
  // reasons, both of them things the narration does on purpose:
  //
  // - Between cues there is silence, because the timeline puts a pause after
  //   a heading and between list items. Clearing on `!cue` made the
  //   highlight blink off in every one of those gaps.
  // - Some cues have no sentence of their own. "End quote." is spoken and
  //   never written, so there is no `ra-N` to find; the reader is still
  //   inside the quotation, which is exactly where the highlight belongs.
  track.addEventListener('cuechange', () => {
    const cue = track.activeCues && track.activeCues[0];
    if (!cue) return;
    const next = document.getElementById(`ra-${cue.id}`);
    if (!next || next === current) return;
    if (current) current.classList.remove('is-reading');
    next.classList.add('is-reading');
    reveal(next);
    current = next;
  });

  // Click or keyboard on a sentence seeks the audio to it. `data-start` is
  // written by the generator from the same timeline that laid out the audio,
  // so this needs no lookup and cannot drift from the cue.
  const seek = (element) => {
    const start = Number.parseFloat(element.dataset.start);
    if (Number.isNaN(start)) return;
    audio.currentTime = start;
    if (audio.paused) audio.play();
  };

  sentences.forEach((sentence) => {
    sentence.tabIndex = 0;
    sentence.addEventListener('click', () => seek(sentence));
    sentence.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      event.preventDefault();  // Space would scroll the page
      seek(sentence);
    });
  });

  // Leaving the highlight behind when playback stops would say the reader is
  // still at a sentence they are not.
  audio.addEventListener('ended', () => {
    if (current) current.classList.remove('is-reading');
    current = null;
  });
}

document.querySelectorAll('[data-readalong]').forEach(wire);
