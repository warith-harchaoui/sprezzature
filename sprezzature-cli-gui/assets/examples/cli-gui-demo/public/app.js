// app.js — cli-gui-demo
//
// Vanilla ES module. No bundler. No framework. Drives:
//   - sidebar swap between three subcommand forms
//   - form serialization into an imgconvert argv
//   - POST /run with SSE streaming of stdout into the log panel
//   - theme switcher persisted in localStorage
//
// The matching skill principles:
//   - event delegation on the sidebar root
//   - native form validation + a tiny dataset-driven dispatch
//   - SSE (text/event-stream) consumed via EventSource
//   - <a> + <button> only; <div onclick> never used

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

// ── Theme switcher ──────────────────────────────────────────────────────────

const THEME_KEY = "color-scheme";

/**
 * Apply a theme (auto / light / dark) by writing the html data attribute and
 * persisting the choice in localStorage.
 *
 * @param {"auto"|"light"|"dark"} mode
 */
function applyTheme(mode = localStorage.getItem(THEME_KEY) ?? "auto") {
  const sys = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  document.documentElement.dataset.colorScheme = mode === "auto" ? sys : mode;
  localStorage.setItem(THEME_KEY, mode);
}

applyTheme();
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
  if ((localStorage.getItem(THEME_KEY) ?? "auto") === "auto") applyTheme("auto");
});
$("#theme-btn").addEventListener("click", () => {
  const cur = document.documentElement.dataset.colorScheme;
  applyTheme(cur === "dark" ? "light" : "dark");
});

// ── Sidebar swap ────────────────────────────────────────────────────────────

const SIDEBAR = $("#sidebar");
const FORMS = Object.fromEntries(
  $$("[data-form]").map((el) => [el.dataset.form, el])
);

/**
 * Activate one subcommand pane: show its form, hide the others, mark the
 * sidebar button as current.
 *
 * @param {string} cmd  "resize" | "convert" | "optimize"
 */
function activate(cmd) {
  for (const [name, form] of Object.entries(FORMS)) {
    form.classList.toggle("hidden", name !== cmd);
  }
  for (const btn of $$("[data-cmd]", SIDEBAR)) {
    const active = btn.dataset.cmd === cmd;
    btn.setAttribute("aria-current", active ? "page" : "false");
    btn.classList.toggle("bg-surface-secondary", active);
    btn.classList.toggle("dark:bg-surface-secondary-dark", active);
  }
}

SIDEBAR.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-cmd]");
  if (!btn) return;
  activate(btn.dataset.cmd);
});

// Quality slider live readout — small enough that DOM-level wiring is fine.
const quality = $("#quality");
const qualityOut = $("#quality-out");
if (quality && qualityOut) {
  quality.addEventListener("input", () => { qualityOut.value = quality.value; });
}

// ── Form → argv ─────────────────────────────────────────────────────────────

/**
 * Convert a HTML form's values into an imgconvert argv list.
 *
 * Rules:
 *   - <input> values become positional args (in form-declaration order)
 *     for non-flag fields named "input" / "output".
 *   - Flag-style fields become "--name value" pairs.
 *   - Checkboxes (toggles) become bare "--name" only when checked.
 *
 * @param {string} cmd  Subcommand name (drives the positional ordering).
 * @param {FormData} fd
 * @returns {string[]}
 */
function toArgv(cmd, fd) {
  const args = [];

  // Positional ordering by subcommand mirrors imgconvert.py's parser.
  if (cmd === "resize" || cmd === "convert") {
    args.push(fd.get("input"), fd.get("output"));
  } else if (cmd === "optimize") {
    args.push(fd.get("input"));
  }

  // Remaining fields → flags. Skip positionals already consumed.
  const positional = new Set(
    cmd === "optimize" ? ["input"] : ["input", "output"]
  );
  for (const [key, raw] of fd.entries()) {
    if (positional.has(key)) continue;
    // Checkboxes: FormData only emits checked boxes; if a key is present
    // for a known boolean toggle, emit the bare flag.
    const isToggle = ["keep-aspect", "in-place", "strip-metadata"].includes(key);
    if (isToggle) {
      args.push(`--${key}`);
      continue;
    }
    args.push(`--${key}`, String(raw));
  }
  return args;
}

// ── Run submit → SSE ────────────────────────────────────────────────────────

const log = $("#log");
const status = $("#status");
const errorBox = $("#error");

/**
 * Append a line to the log panel and scroll to the bottom.
 *
 * @param {string} line
 * @param {string} [tone]  Tailwind class name for the line color.
 */
function appendLog(line, tone = "") {
  const span = document.createElement("span");
  if (tone) span.className = tone;
  span.textContent = line + "\n";
  log.appendChild(span);
  log.scrollTop = log.scrollHeight;
}

/**
 * Reset log, error banner, and status before a new run.
 */
function resetOutput() {
  log.textContent = "";
  errorBox.classList.add("hidden");
  errorBox.textContent = "";
}

/**
 * Run a command via POST /run, consuming the SSE stream.
 *
 * @param {string} cmd
 * @param {string[]} argv
 */
async function run(cmd, argv) {
  resetOutput();
  status.textContent = "Running…";

  // fetch returns once the headers are received; we then read the body
  // as a stream and split on the SSE record separator (\n\n).
  let resp;
  try {
    resp = await fetch("/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cmd, args: argv }),
    });
  } catch (err) {
    status.textContent = "Failed";
    errorBox.textContent = `Network error: ${err.message}`;
    errorBox.classList.remove("hidden");
    return;
  }

  if (!resp.ok) {
    status.textContent = "Failed";
    errorBox.textContent = `HTTP ${resp.status} — ${await resp.text()}`;
    errorBox.classList.remove("hidden");
    return;
  }

  const reader = resp.body.getReader();
  const dec = new TextDecoder();
  let buf = "";

  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });

    // SSE records are separated by a blank line. Process complete records;
    // hold any trailing partial record in ``buf`` for the next chunk.
    let sep;
    while ((sep = buf.indexOf("\n\n")) !== -1) {
      const record = buf.slice(0, sep);
      buf = buf.slice(sep + 2);
      handleRecord(record);
    }
  }
}

/**
 * Handle one SSE record (event + data lines).
 *
 * @param {string} record
 */
function handleRecord(record) {
  const lines = record.split("\n");
  let event = "message";
  const data = [];
  for (const line of lines) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data.push(line.slice(5).trim());
  }
  const payload = data.join("\n");

  if (event === "line") {
    appendLog(payload);
  } else if (event === "done") {
    let info = {};
    try { info = JSON.parse(payload); } catch { /* keep empty */ }
    if (info.exit_code === 0) {
      status.textContent = "Done";
      appendLog("✓ exited 0", "text-brand-green");
    } else {
      status.textContent = `Exit ${info.exit_code}`;
      errorBox.textContent = `Command failed with exit code ${info.exit_code}.`;
      errorBox.classList.remove("hidden");
      appendLog(`✗ exited ${info.exit_code}`, "text-brand-red");
    }
  } else if (event === "error") {
    status.textContent = "Failed";
    errorBox.textContent = payload;
    errorBox.classList.remove("hidden");
  }
}

// Wire each form's submit. Event delegation on document so we don't care
// which form is currently visible.
document.addEventListener("submit", (e) => {
  const form = e.target.closest("[data-form]");
  if (!form) return;
  e.preventDefault();
  if (!form.reportValidity()) return;
  const fd = new FormData(form);
  const argv = toArgv(form.dataset.form, fd);
  run(form.dataset.form, argv);
});
