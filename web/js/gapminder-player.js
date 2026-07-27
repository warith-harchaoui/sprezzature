// Playback + follow controls for the Hans Rosling tribute. Talks to the player
// embedded in each SVG (make_gapminder.py) over postMessage, so it works over
// http and from file://. Multi-instance: every figure marked [data-gm-fig] gets
// its own independent controller, and inbound messages are routed by source
// window so a tick from one chart never touches another chart's controls.
// A page with no [data-gm-fig] (or a figure without [data-gm-controls]) still
// gets the SVG's own default looping animation.
(function () {
  // One controller per figure. The controller owns its own <object>, its own
  // control bar, and its own playback state; nothing is shared between charts.
  function initFigure(fig) {
    var obj = fig.querySelector('object');
    if (!obj) return;
    // Controls live next to the figure. Prefer an explicitly linked bar
    // ([data-gm-controls] inside the same block wrapper), else the immediate
    // sibling control bar.
    var block = fig.closest('[data-gm-block]') || fig.parentElement;
    var ctl = block ? block.querySelector('[data-gm-controls]') : null;

    function send(m) { try { if (obj.contentWindow) obj.contentWindow.postMessage(m, '*'); } catch (e) {} }

    var scrubbing = false, playing = true, greeted = false;
    var toggleBtn = ctl && ctl.querySelector('[data-gm="toggle"]');
    var yearOut = ctl && ctl.querySelector('[data-gm-year]');
    var scrub = ctl && ctl.querySelector('[data-gm-scrub]');
    var followSel = ctl && ctl.querySelector('[data-gm-follow]');
    var readout = ctl && ctl.querySelector('[data-gm-readout]');

    function setPlay() {
      if (!toggleBtn) return;
      toggleBtn.textContent = playing ? (toggleBtn.dataset.pause || 'Pause') : (toggleBtn.dataset.play || 'Play');
      toggleBtn.setAttribute('aria-pressed', String(playing));
    }
    function fmtPop(p) { return p >= 1e6 ? (p / 1e6).toFixed(1) + 'M' : p.toLocaleString(); }

    // Route inbound messages: only handle those from THIS figure's SVG window.
    window.addEventListener('message', function (e) {
      if (!obj.contentWindow || e.source !== obj.contentWindow) return;
      var m = e.data;
      if (!m || !m.gm) return;
      if (m.gm === 'ready') {
        greeted = true;
        playing = !m.reduced;
        if (scrub) { scrub.min = m.y0; scrub.max = m.y1; scrub.value = m.reduced ? m.y1 : m.y0; }
        if (yearOut) yearOut.textContent = m.reduced ? m.y1 : m.y0;
        if (followSel && !followSel.dataset.filled) {
          m.countries.forEach(function (c) {
            var o = document.createElement('option'); o.value = c; o.textContent = c; followSel.appendChild(o);
          });
          followSel.dataset.filled = '1';
        }
        setPlay();
      } else if (m.gm === 'tick') {
        playing = m.playing;
        if (yearOut) yearOut.textContent = m.year;
        if (scrub && !scrubbing) scrub.value = m.year;
        setPlay();
      } else if (m.gm === 'follow') {
        if (!readout) return;
        readout.hidden = false;
        if (m.exists === false) { readout.innerHTML = '<strong>' + m.name + '</strong>'; }
        else {
          // The original chart posts {income, life}; the variant charts post
          // raw {x, y} for their own axes. Handle both so no chart shows "undefined".
          var vals;
          if (m.income !== undefined) { vals = '$' + m.income.toLocaleString() + ' · ' + m.life; }
          else if (m.x !== undefined) { vals = (Math.round(m.x * 100) / 100) + ' · ' + (Math.round(m.y * 100) / 100); }
          else { vals = ''; }
          readout.innerHTML = '<strong>' + m.name + '</strong> · ' + m.year +
            (vals ? ' · ' + vals : '') + ' · ' + fmtPop(m.pop);
        }
      } else if (m.gm === 'picked') {
        if (followSel) followSel.value = m.name;
      }
    });

    // Handshake: the SVG posts 'ready' on load, but our listener may attach
    // after that, so keep saying hello until we've received the country list.
    var tries = 0;
    var hi = setInterval(function () {
      if (greeted || tries++ > 40) { clearInterval(hi); return; }
      send({ gm: 'hello' });
    }, 200);
    obj.addEventListener('load', function () { send({ gm: 'hello' }); });
    send({ gm: 'hello' });

    if (!ctl) return;
    ctl.addEventListener('click', function (e) {
      var b = e.target.closest('button');
      if (!b) return;
      if (b.dataset.gm === 'toggle') { send({ gm: 'toggle' }); playing = !playing; setPlay(); }
      else if (b.dataset.gm === 'restart') { send({ gm: 'restart' }); playing = true; setPlay(); }
      else if (b.dataset.gm === 'prev') { send({ gm: 'step', d: -1 }); playing = false; setPlay(); }
      else if (b.dataset.gm === 'next') { send({ gm: 'step', d: 1 }); playing = false; setPlay(); }
      else if (b.dataset.gmSpeed) {
        send({ gm: 'speed', v: parseFloat(b.dataset.gmSpeed) });
        ctl.querySelectorAll('[data-gm-speed]').forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
      } else if (b.dataset.gmYearJump) {
        var y = parseInt(b.dataset.gmYearJump, 10);
        send({ gm: 'seekYear', year: y }); send({ gm: 'pause' });
        playing = false; setPlay();
        if (scrub) scrub.value = y; if (yearOut) yearOut.textContent = y;
      }
    });
    if (scrub) {
      scrub.addEventListener('input', function () {
        scrubbing = true; send({ gm: 'seekYear', year: parseInt(scrub.value, 10) }); send({ gm: 'pause' });
        playing = false; setPlay(); if (yearOut) yearOut.textContent = scrub.value;
      });
      scrub.addEventListener('change', function () { scrubbing = false; });
    }
    if (followSel) followSel.addEventListener('change', function () {
      send({ gm: 'follow', name: followSel.value || null });
      if (!followSel.value && readout) readout.hidden = true;
    });
  }

  // Initialise every figure on the page. Fall back to the legacy single #gm-fig
  // so an un-migrated page keeps working.
  var figs = document.querySelectorAll('[data-gm-fig]');
  if (!figs.length) { var legacy = document.getElementById('gm-fig'); if (legacy) figs = [legacy]; }
  Array.prototype.forEach.call(figs, initFigure);
})();
