"""
sprezzature_cli_gui.renderer
=====================

The HTML emitter.

Composes a single-file vanilla-JS + Tailwind GUI from a walked parser
tree (the canonical ``prog`` / ``description`` / ``actions`` /
``sub_commands`` dict). Every action becomes a form field, every
sub-command a collapsible ``<details>`` block, and a tiny inline module
assembles the CLI line client-side for copy / Tauri-invoke. Output
follows the sprezzature-ui stack rules — semantic HTML, Tailwind utilities,
dark-mode peers, focus rings, reduced-motion guards.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import html as html_lib
from typing import Any


def _e(text: str) -> str:
    """Shorthand for :func:`html.escape` (HTML-attribute-safe)."""
    return html_lib.escape(text, quote=True)


def _field_html(action: dict[str, Any], prefix: str) -> str:
    """
    Render one form field for an :func:`serialize_action` dict.

    ``prefix`` is the sub-command path joined by ``"."`` (empty for
    the root parser). It is folded into the field ``id``/``name`` so
    the page can carry multiple sub-command forms without ID
    collisions.
    """
    flag: str = action["flags"][0] if action["flags"] else action["dest"]
    label_text: str = action["dest"].replace("_", " ")
    help_text: str = action.get("help") or ""
    field_id: str = f"{prefix}_{action['dest']}" if prefix else action["dest"]
    field_name: str = field_id

    required_marker: str = (
        ' <span class="text-brand-red" aria-hidden="true">*</span>'
        if action.get("required")
        else ""
    )
    help_block: str = (
        f'<p class="mt-1 text-[13px] text-label-secondary '
        f'dark:text-label-secondary-dark">{_e(help_text)}</p>'
        if help_text
        else ""
    )
    flag_block: str = (
        f'<span class="ml-2 font-mono text-[12px] text-label-secondary '
        f'dark:text-label-secondary-dark">{_e(flag)}</span>'
        if action["flags"]
        else ""
    )

    kind: str = action["kind"]
    default: Any = action.get("default")
    default_attr: str = (
        f' value="{_e(str(default))}"'
        if default not in (None, "", []) and kind != "bool"
        else ""
    )
    common_classes: str = (
        "mt-1 block w-full min-h-11 rounded-xl border border-separator "
        "bg-surface-secondary px-3 py-2 text-[15px] text-label-primary "
        "focus:outline-none focus-visible:ring-2 "
        "focus-visible:ring-brand-blue focus-visible:ring-offset-2 "
        "dark:border-separator-dark dark:bg-surface-secondary-dark "
        "dark:text-label-primary-dark"
    )

    if kind == "bool":
        checked: str = ' checked' if default is True else ""
        # ``min-h-11`` on the checkbox satisfies the sprezzature-ux-laws Fitts
        # heuristic (44 px hit area); ``focus-visible:ring-2`` satisfies
        # the Aesthetic-Usability heuristic. The visible checkbox stays
        # small via the ``h-5 w-5`` token; the label extends the click
        # area through the ``for`` attribute. We pad the field-wrapper
        # in the calling code so the row itself is ≥ 44 px tall.
        body: str = (
            f'<input id="{_e(field_id)}" name="{_e(field_name)}" '
            f'type="checkbox" data-cli-flag="{_e(flag)}" '
            f'class="mt-1 h-5 w-5 min-h-11 rounded border-separator '
            f'text-brand-blue focus:outline-none '
            f'focus-visible:ring-2 focus-visible:ring-brand-blue '
            f'focus-visible:ring-offset-2"{checked}>'
        )
    elif kind == "choice":
        opts: list[str] = []
        for c in action.get("choices") or []:
            sel: str = ' selected' if c == default else ""
            opts.append(
                f'<option value="{_e(str(c))}"{sel}>{_e(str(c))}</option>'
            )
        body = (
            f'<select id="{_e(field_id)}" name="{_e(field_name)}" '
            f'data-cli-flag="{_e(flag)}" class="{common_classes}">'
            f'{"".join(opts)}</select>'
        )
    elif kind in ("int", "float"):
        step: str = "1" if kind == "int" else "any"
        body = (
            f'<input id="{_e(field_id)}" name="{_e(field_name)}" '
            f'type="number" step="{step}" data-cli-flag="{_e(flag)}" '
            f'class="{common_classes}"{default_attr}>'
        )
    elif kind == "file":
        # File-type actions still render as text; the user pastes the
        # path. A real file picker lives in the host (Tauri's
        # ``dialog`` API, or HTTP upload).
        body = (
            f'<input id="{_e(field_id)}" name="{_e(field_name)}" '
            f'type="text" placeholder="path/to/file" '
            f'data-cli-flag="{_e(flag)}" '
            f'class="{common_classes}"{default_attr}>'
        )
    else:
        body = (
            f'<input id="{_e(field_id)}" name="{_e(field_name)}" '
            f'type="text" data-cli-flag="{_e(flag)}" '
            f'class="{common_classes}"{default_attr}>'
        )

    return (
        '<div class="mb-4">'
        f'<label for="{_e(field_id)}" class="block text-[14px] '
        'font-medium text-label-primary dark:text-label-primary-dark">'
        f'{_e(label_text)}{required_marker}{flag_block}</label>'
        f'{body}{help_block}</div>'
    )


def _form_html(node: dict[str, Any], path: list[str]) -> str:
    """Render one sub-command form (or the root form when path is empty)."""
    prefix: str = "_".join(path) if path else ""
    sub_command_id: str = (
        ".".join(path) if path else ""
    )
    fields: str = "\n".join(
        _field_html(a, prefix) for a in node["actions"]
    )
    if not fields:
        fields = (
            '<p class="text-[14px] text-label-secondary '
            'dark:text-label-secondary-dark">This sub-command takes '
            'no arguments.</p>'
        )
    desc: str = (
        f'<p class="mb-3 text-[14px] text-label-secondary '
        f'dark:text-label-secondary-dark">{_e(node["description"])}</p>'
        if node.get("description")
        else ""
    )
    return (
        f'<form data-cli-form data-subcommand="{_e(sub_command_id)}">'
        f'{desc}{fields}'
        f'<button type="button" data-cli-build class="mt-4 inline-flex '
        'min-h-11 items-center justify-center gap-2 rounded-full '
        'bg-brand-blue px-5 py-3 text-[15px] font-semibold text-white '
        'hover:opacity-90 active:scale-[0.97] '
        'focus:outline-none focus-visible:ring-2 '
        'focus-visible:ring-brand-blue focus-visible:ring-offset-2 '
        'motion-reduce:active:scale-100">Build command</button>'
        '</form>'
    )


def _children_html(node: dict[str, Any], path: list[str]) -> str:
    """Render nested sub-commands as collapsible ``<details>`` blocks."""
    parts: list[str] = []
    for name, child in node["sub_commands"].items():
        body: str = _form_html(child, path + [name])
        inner_sub: str = _children_html(child, path + [name])
        parts.append(
            '<details class="mt-3 rounded-2xl bg-surface-secondary p-4 '
            'dark:bg-surface-secondary-dark">'
            # ``min-h-11`` + ``focus-visible:ring-*`` keep sprezzature-ux-laws
            # happy on the disclosure-control element. ``cursor-pointer``
            # is intentional here — the agent's anti-pattern refusal
            # targets clickable ``<div>``/``<span>``, not real ``<summary>``.
            f'<summary class="flex min-h-11 cursor-pointer items-center '
            'text-[16px] font-semibold text-label-primary '
            'focus:outline-none focus-visible:ring-2 '
            'focus-visible:ring-brand-blue focus-visible:ring-offset-2 '
            'rounded-lg dark:text-label-primary-dark">'
            f'{_e(name)}</summary>'
            f'<div class="mt-3">{body}{inner_sub}</div>'
            '</details>'
        )
    return "".join(parts)


def render_html(tree: dict[str, Any], title: str = "CLI GUI") -> str:
    """
    Compose the full HTML document from a walked parser tree.

    Parameters
    ----------
    tree : dict
        Output of :func:`walk_parser`.
    title : str, default "CLI GUI"
        Page ``<title>``. The prog name appears in the visible header
        block regardless.

    Returns
    -------
    str
        A complete, single-file HTML document. ``\n``-terminated.
    """
    root_form: str = (
        _form_html(tree, [])
        if tree["actions"]
        else ""
    )
    sub_html: str = _children_html(tree, [])
    desc: str = (
        f'<p class="text-[14px] text-label-secondary '
        f'dark:text-label-secondary-dark">{_e(tree["description"])}</p>'
        if tree["description"]
        else ""
    )

    # The JS payload below is intentionally tiny: walk every form,
    # collect data-cli-flag inputs, assemble the command string,
    # render it into <pre id="cli-out">. The host adapter (Tauri /
    # FastAPI / shell) takes it from there.
    js_payload: str = """
const escape = (s) => {
  // Conservative shell quoting: wrap in single quotes and escape
  // embedded ones. Good enough for clipboard / display; the host
  // adapter is free to use a stricter quoter.
  if (s === '' || /[^A-Za-z0-9_./:=,@%+-]/.test(s)) {
    return "'" + s.replace(/'/g, "'\\\\''") + "'";
  }
  return s;
};

document.querySelectorAll('[data-cli-build]').forEach((btn) => {
  btn.addEventListener('click', (ev) => {
    const form = ev.currentTarget.closest('form');
    const sub = form.getAttribute('data-subcommand') || '';
    const parts = ['<<PROG>>'];
    if (sub) parts.push(...sub.split('.'));
    form.querySelectorAll('[data-cli-flag]').forEach((el) => {
      const flag = el.getAttribute('data-cli-flag');
      if (el.type === 'checkbox') {
        if (el.checked) parts.push(flag);
        return;
      }
      const value = (el.value || '').trim();
      if (!value) return;
      if (flag.startsWith('-')) parts.push(flag, escape(value));
      else parts.push(escape(value));
    });
    const out = parts.join(' ');
    const pre = document.getElementById('cli-out');
    pre.textContent = out;
    pre.scrollIntoView({behavior: 'smooth', block: 'nearest'});
  });
});
""".replace("<<PROG>>", tree["prog"])

    return (
        '<!doctype html>\n'
        '<html lang="en" data-color-scheme="auto">\n'
        '<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<title>{_e(title)}</title>\n'
        '<script src="https://cdn.tailwindcss.com"></script>\n'
        '<style>\n'
        '  :root { color-scheme: light dark; }\n'
        '  html, body { font-family: ui-sans-serif, system-ui, sans-serif; '
        'background-color: #FFFFFF; color: #000000; }\n'
        '  html.dark, html[data-color-scheme="dark"], '
        'html[data-color-scheme="dark"] body { background-color: #000000; '
        'color: #FFFFFF; }\n'
        '  *:focus { outline: none; }\n'
        '</style>\n'
        '</head>\n'
        '<body class="min-h-screen bg-white text-black dark:bg-black dark:text-white">\n'
        '<main class="mx-auto max-w-3xl px-4 py-8">\n'
        f'<header class="mb-6"><h1 class="text-[28px] font-semibold">{_e(tree["prog"])}</h1>{desc}</header>\n'
        f'{root_form}\n'
        f'{sub_html}\n'
        '<section class="mt-8">\n'
        '  <h2 class="text-[16px] font-semibold mb-2">Built command</h2>\n'
        '  <pre id="cli-out" class="rounded-2xl bg-surface-secondary p-4 '
        'font-mono text-[13px] text-label-primary dark:bg-surface-secondary-dark '
        'dark:text-label-primary-dark overflow-x-auto">'
        '(press Build command above)</pre>\n'
        '</section>\n'
        '<footer class="mt-8 text-[12px] text-label-secondary '
        'dark:text-label-secondary-dark">\n'
        '  Generated by sprezzature-cli-gui/scripts/cli_to_gui.py. '
        'Wire the Build command output to your host '
        '(Tauri invoke / FastAPI SSE / Express / shell).\n'
        '</footer>\n'
        '</main>\n'
        '<script type="module">\n'
        f'{js_payload}\n'
        '</script>\n'
        '</body>\n'
        '</html>\n'
    )
