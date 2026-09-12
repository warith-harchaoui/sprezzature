/**
 * render_web_interact — the Ralph Eyeball Loop for things you have to click.
 *
 * `scripts/render_web.sh` photographs a page as it loads, which is the whole
 * story for a static layout and half of it for a disclosure: a closed menu
 * looks identical whether or not the button works. This drives headless Chrome
 * over the DevTools protocol instead — load, run a few steps, photograph after
 * each — so the screenshots show the states a reader actually reaches.
 *
 * Usage:
 *   node scripts/render_web_interact.js <page.html> <out-prefix> <width> <height> <step…>
 *
 * A step is one of:
 *   click:<selector>    dispatch a real click and wait for the page to settle
 *   key:<key>           dispatch a keydown/keyup (Escape, Enter, …)
 *   shot:<name>         write <out-prefix>-<name>.png
 *   eval:<expression>   run it and print the result, for assertions
 *
 * No npm dependency: Node's global WebSocket speaks CDP directly.
 */

'use strict';

const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');

const CHROME_CANDIDATES = [
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
];

function findChrome() {
  for (const candidate of CHROME_CANDIDATES) {
    if (fs.existsSync(candidate)) return candidate;
  }
  throw new Error('Chrome / Chromium not found.');
}

/** Poll the debugging port until Chrome answers with a target list. */
async function waitForTarget(port, timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/list`);
      const targets = await response.json();
      const page = targets.find((t) => t.type === 'page' && t.webSocketDebuggerUrl);
      if (page) return page;
    } catch {
      /* not listening yet */
    }
    if (Date.now() > deadline) throw new Error('Chrome never opened its debugging port.');
    await new Promise((r) => setTimeout(r, 120));
  }
}

/** Minimal CDP client: send(method, params) -> Promise<result>. */
function connect(url) {
  const socket = new WebSocket(url);
  const pending = new Map();
  let nextId = 0;
  const ready = new Promise((resolve, reject) => {
    socket.addEventListener('open', () => resolve());
    socket.addEventListener('error', (e) => reject(e));
  });
  socket.addEventListener('message', (event) => {
    const message = JSON.parse(event.data);
    const entry = pending.get(message.id);
    if (!entry) return;
    pending.delete(message.id);
    if (message.error) entry.reject(new Error(JSON.stringify(message.error)));
    else entry.resolve(message.result);
  });
  return {
    ready,
    send(method, params = {}) {
      const id = ++nextId;
      socket.send(JSON.stringify({ id, method, params }));
      return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
    },
    close: () => socket.close(),
  };
}

async function evaluate(cdp, expression) {
  const result = await cdp.send('Runtime.evaluate', {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.exception?.description || 'evaluate failed');
  }
  return result.result.value;
}

async function main() {
  const [src, prefix, widthArg, heightArg, ...steps] = process.argv.slice(2);
  if (!src || !prefix) {
    console.error('Usage: node render_web_interact.js <page.html> <out-prefix> <w> <h> <step…>');
    process.exit(2);
  }
  const width = Number(widthArg || 500);
  const height = Number(heightArg || 900);

  const chrome = findChrome();
  const port = 9222 + (process.pid % 500);
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'ralph-chrome-'));
  const child = spawn(
    chrome,
    [
      '--headless=new',
      `--remote-debugging-port=${port}`,
      `--user-data-dir=${profile}`,
      `--window-size=${width},${height}`,
      '--hide-scrollbars',
      '--force-device-scale-factor=1',
      '--no-first-run',
      '--disable-gpu',
      'about:blank',
    ],
    { stdio: 'ignore' },
  );

  let cdp;
  try {
    const target = await waitForTarget(port);
    cdp = connect(target.webSocketDebuggerUrl);
    await cdp.ready;
    await cdp.send('Page.enable');
    await cdp.send('Runtime.enable');
    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width,
      height,
      deviceScaleFactor: 1,
      mobile: width < 640,
    });

    const url = 'file://' + path.resolve(src);
    await cdp.send('Page.navigate', { url });
    await new Promise((r) => setTimeout(r, 900));

    for (const step of steps) {
      const separator = step.indexOf(':');
      const verb = step.slice(0, separator);
      const argument = step.slice(separator + 1);

      if (verb === 'click') {
        const ok = await evaluate(
          cdp,
          `(() => { const el = document.querySelector(${JSON.stringify(argument)});
                    if (!el) return false; el.click(); return true; })()`,
        );
        if (!ok) throw new Error(`no element matches ${argument}`);
        await new Promise((r) => setTimeout(r, 250));
      } else if (verb === 'key') {
        await cdp.send('Input.dispatchKeyEvent', { type: 'keyDown', key: argument });
        await cdp.send('Input.dispatchKeyEvent', { type: 'keyUp', key: argument });
        await new Promise((r) => setTimeout(r, 250));
      } else if (verb === 'shot') {
        const shot = await cdp.send('Page.captureScreenshot', { format: 'png' });
        const out = `${prefix}-${argument}.png`;
        fs.mkdirSync(path.dirname(out), { recursive: true });
        fs.writeFileSync(out, Buffer.from(shot.data, 'base64'));
        console.log(`wrote ${out}`);
      } else if (verb === 'eval') {
        console.log(`${argument} => ${JSON.stringify(await evaluate(cdp, argument))}`);
      } else {
        throw new Error(`unknown step "${step}"`);
      }
    }
  } finally {
    if (cdp) cdp.close();
    child.kill();
    fs.rmSync(profile, { recursive: true, force: true });
  }
}

main().catch((error) => {
  console.error(String(error.message || error));
  process.exit(1);
});
