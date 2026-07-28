"""
ralph — the generic Ralph loop and its two standard instantiations.

The Ralph loop is a produce-inspect-fix-repeat cycle that converges when a
verdict says the artifact is ready to ship. The same driver covers visual
quality (the Ralph Eyeball Loop) and prose quality (the prose seam loop).

Two concrete wrappers are provided:

``eyeball_loop``
    Renders a source file to a PNG, critiques it with a vision model, asks a
    text model to rewrite the source to fix the complaints, and repeats.  The
    render step is caller-supplied so the function works with any surface
    (Vega, HTML, Mermaid, TikZ, SVG).

``prose_loop``
    Splits text into paragraphs, examines adjacent-paragraph seams with a text
    model enforcing the project writing charter, rewrites only the seam when a
    flaw is found, and repeats until a full pass makes no edit.

Both wrappers call :func:`llm.chat` for model interactions, which routes to
the configured local backend (Ollama, vLLM, or LangChain) via environment
variables.

Author
------
Warith Harchaoui <warith.harchaoui@gmail.com>
"""

from __future__ import annotations

import json
from typing import Any, Callable

from . import llm


# ---------------------------------------------------------------------------
# Prompts for the eyeball loop
# ---------------------------------------------------------------------------

# The system prompt instructs the text model to edit source code, not prose.
# {kind} is substituted at call time with the surface name (vega, html, etc.).
_EDIT_SYSTEM_TMPL: str = (
    "You edit {kind} source to fix the reviewer's concrete complaints. "
    "Return ONLY the full revised {kind} source, with no explanation and "
    "no surrounding prose. Change nothing the critique did not raise. "
    "Honor the house rules: three Roboto font families, Tailwind utility "
    "classes only, a color-vision-safe palette, and no chartjunk."
)

# The verdict prompt instructs the model to parse a critique and produce a
# machine-readable gate: ship or iterate.
_VERDICT_PROMPT: str = (
    "Given the following visual critique, reply in JSON only with no "
    "surrounding prose. Fields: ship (bool, true when ready), score "
    "(float 0.0 to 1.0), blocking (array of strings naming blocking issues). "
    "A score above 0.8 with an empty blocking array means ship is true.\n\n"
    "CRITIQUE:\n{critique}"
)

# Schema used to request structured JSON from the model for a verdict.
_VERDICT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "ship":     {"type": "boolean"},
        "score":    {"type": "number"},
        "blocking": {"type": "array", "items": {"type": "string"}},
    },
}


# ---------------------------------------------------------------------------
# Prompts for the prose loop
# ---------------------------------------------------------------------------

# System prompt for the seam inspector.  {charter} is substituted at call time.
_SEAM_SYSTEM_TMPL: str = (
    "You are a prose editor enforcing this writing charter:\n\n{charter}\n\n"
    "Examine only the junction between the two paragraphs supplied by the "
    "user.  Report whether the seam needs fixing and list the reasons."
)

# JSON schema for the seam inspection response.
_SEAM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "needs_fix": {"type": "boolean"},
        "reasons":   {"type": "array", "items": {"type": "string"}},
    },
}

# System prompt for the paragraph-pair fixer.
_FIX_SYSTEM: str = (
    "Fix only the seam between the two paragraphs. Return exactly two "
    "paragraphs separated by the literal string '|||' and nothing else: "
    "no explanation, no label, no leading or trailing whitespace beyond the "
    "separator.  Do not add, remove, or reorder any information."
)


# ---------------------------------------------------------------------------
# Generic driver
# ---------------------------------------------------------------------------

def ralph_loop(
    source: Any,
    *,
    render: Callable[[Any], Any],
    inspect: Callable[[Any], str],
    apply_fix: Callable[[Any, str], Any],
    verdict: Callable[[str], dict[str, Any]],
    max_iters: int = 6,
    on_iteration: Callable[[int, Any, Any, str, dict[str, Any]], None] | None = None,
) -> tuple[Any, list[tuple[int, str, dict[str, Any]]]]:
    """
    Run the generic produce-inspect-fix-repeat loop.

    Each iteration: render the artifact, inspect it, ask for a verdict.
    If the verdict says ship, stop.  Otherwise apply a fix and try again.
    Stop early when the fix is a no-op (the model could not improve the
    source) or when the iteration budget is exhausted.

    Parameters
    ----------
    source : Any
        The initial source artifact (e.g. a Vega-Lite JSON string).
    render : callable
        ``render(source) -> artifact``.  Converts source to the inspectable
        form (e.g. PNG bytes from a Vega spec).
    inspect : callable
        ``inspect(artifact) -> critique_str``.  Critiques the artifact and
        returns a human-readable string.
    apply_fix : callable
        ``apply_fix(source, critique_str) -> new_source``.  Edits the source
        to address the critique.  Should return the same source unchanged when
        it cannot improve it.
    verdict : callable
        ``verdict(critique_str) -> dict``.  Returns a dict with at minimum a
        ``ship`` boolean key.
    max_iters : int, optional
        Maximum number of iterations.  Default ``6``.
    on_iteration : callable or None, optional
        Optional progress callback ``(i, source, artifact, critique, verdict)``.

    Returns
    -------
    tuple[Any, list]
        ``(final_source, history)`` where ``history`` is a list of
        ``(iteration_index, critique_str, verdict_dict)`` tuples.

    Examples
    --------
    >>> history = []
    >>> src, hist = ralph_loop(
    ...     "initial",
    ...     render=lambda s: s.encode(),
    ...     inspect=lambda a: "ok",
    ...     apply_fix=lambda s, c: s,
    ...     verdict=lambda c: {"ship": True, "score": 1.0, "blocking": []},
    ...     max_iters=3,
    ... )
    >>> hist[0][2]["ship"]
    True
    """
    history: list[tuple[int, str, dict[str, Any]]] = []

    for i in range(max_iters):
        artifact = render(source)
        critique = inspect(artifact)
        vdict = verdict(critique)
        history.append((i, critique, vdict))

        if on_iteration is not None:
            on_iteration(i, source, artifact, critique, vdict)

        # Ship verdict: the loop has converged.
        if vdict.get("ship"):
            return source, history

        # Apply a fix and check whether it changed anything.
        new_source = apply_fix(source, critique)
        if new_source == source:
            # The model returned the same source — further iterations cannot help.
            return source, history
        source = new_source

    # Iteration budget spent without a ship verdict.
    return source, history


# ---------------------------------------------------------------------------
# Eyeball loop (visual quality)
# ---------------------------------------------------------------------------

def eyeball_loop(
    source_text: str,
    *,
    kind: str,
    render_fn: Callable[[str], bytes],
    max_iters: int = 6,
    on_iteration: Callable[[int, str, bytes, str, dict[str, Any]], None] | None = None,
) -> tuple[str, list[tuple[int, str, dict[str, Any]]]]:
    """
    Autonomous visual quality loop using a vision model as the inspector.

    Calls ``render_fn(source_text)`` to produce a PNG, sends the PNG to the
    vision model (``SPREZZATURE_LLM_VISION``) for a critique, then asks the
    text model (``SPREZZATURE_LLM_TEXT``) to rewrite the source to fix the
    blocking issues.  Repeats until the verdict says ship.

    Parameters
    ----------
    source_text : str
        The source artifact: a Vega-Lite JSON spec, an HTML page, a TikZ
        document, a Mermaid diagram, or an SVG file.
    kind : str
        Surface label used in the edit prompt.  Examples: ``"vega"``,
        ``"html"``, ``"mermaid"``, ``"tikz"``, ``"svg"``.
    render_fn : callable
        ``render_fn(source_text) -> bytes``.  Produces a PNG from the source.
        Use the renderers already in ``sprezzature-figures/scripts/`` or any
        headless renderer suited to the surface.
    max_iters : int, optional
        Iteration budget.  Default ``6``.
    on_iteration : callable or None, optional
        Progress callback ``(i, source, png_bytes, critique, verdict_dict)``.

    Returns
    -------
    tuple[str, list]
        ``(final_source_text, history)`` tuples.  History entries are
        ``(iteration_index, critique_str, verdict_dict)``.

    Examples
    --------
    >>> def fake_render(s: str) -> bytes:
    ...     return b"PNG"
    >>> # eyeball_loop("spec.vl.json content", kind="vega", render_fn=fake_render)
    """
    edit_system = _EDIT_SYSTEM_TMPL.format(kind=kind)

    def _inspect(png: bytes) -> str:
        """Critique the PNG using the vision model."""
        critique_prompt = (
            "Critique this {kind} visualization honestly under these headings:\n"
            "Layout, Contrast, Hierarchy, Spacing, Accessibility, Colors, "
            "Text readability, Overall verdict.\n"
            "Be specific.  Name exact elements that need fixing."
        ).format(kind=kind)
        # The vision model receives the PNG as raw bytes; llm.chat handles encoding.
        result = llm.chat(critique_prompt, images=[png])
        return str(result)

    def _verdict(critique: str) -> dict[str, Any]:
        """Parse the critique into a machine-readable ship/iterate gate."""
        prompt = _VERDICT_PROMPT.format(critique=critique)
        result = llm.chat(prompt, json_schema=_VERDICT_SCHEMA)
        if isinstance(result, dict):
            return result
        # Fallback: if the model returned a string, try to parse it ourselves.
        try:
            return json.loads(str(result))
        except json.JSONDecodeError:
            return {"ship": False, "score": 0.0, "blocking": ["parse error"]}

    def _apply_fix(src: str, critique: str) -> str:
        """Ask the text model to edit the source to address the critique."""
        fix_prompt = (
            f"CURRENT SOURCE:\n{src}\n\n"
            f"REVIEWER CRITIQUE:\n{critique}"
        )
        result = llm.chat(fix_prompt, system=edit_system)
        return str(result) if result else src

    return ralph_loop(
        source_text,
        render=render_fn,
        inspect=_inspect,
        apply_fix=_apply_fix,
        verdict=_verdict,
        max_iters=max_iters,
        on_iteration=on_iteration,
    )


# ---------------------------------------------------------------------------
# Prose loop (writing charter enforcement)
# ---------------------------------------------------------------------------

def prose_loop(
    text: str,
    *,
    charter: str,
    max_passes: int = 3,
) -> str:
    """
    Enforce the writing charter on a text by checking paragraph-pair seams.

    Implements the paragraph-pair seam technique from the project writing
    charter (WRITING.md §10, "Flow by Paragraph Pairs"): the text is split
    into paragraphs and each adjacent pair ``(n, n+1)`` is examined by a
    text model.  When the seam needs fixing, both paragraphs are rewritten.
    The loop repeats until a full pass makes no edit or the pass budget runs
    out.  Every paragraph is tested twice: once on arrival and once on
    departure.

    Parameters
    ----------
    text : str
        Input prose.  Paragraphs are delimited by one or more blank lines.
    charter : str
        The full writing charter text injected into the seam-inspector
        system prompt.  Load it with :func:`writing.load_charter`.
    max_passes : int, optional
        Maximum number of full passes over the paragraph list.  Default ``3``.

    Returns
    -------
    str
        Revised text.  Paragraphs are rejoined with single blank lines.

    Examples
    --------
    >>> result = prose_loop("Para one.\n\nPara two.", charter="Be concise.")
    >>> isinstance(result, str)
    True
    """
    # Split on one or more blank lines; preserve non-empty paragraphs.
    import re
    paragraphs: list[str] = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]

    if len(paragraphs) < 2:
        # Nothing to examine: a single paragraph has no seam.
        return text

    seam_system = _SEAM_SYSTEM_TMPL.format(charter=charter)

    for _pass in range(max_passes):
        changed = False

        # Overlapping window: (0,1), (1,2), ..., (n-2, n-1).
        # Every paragraph except the first and last is tested twice.
        for n in range(len(paragraphs) - 1):
            para_a = paragraphs[n]
            para_b = paragraphs[n + 1]

            seam_prompt = (
                f"Paragraph A:\n{para_a}\n\n"
                f"Paragraph B:\n{para_b}\n\n"
                "Examine the seam: does A call for B logically? Are words "
                "echoed? Is there a bolted-on transition? Is there a logic gap?"
            )
            result = llm.chat(seam_prompt, system=seam_system, json_schema=_SEAM_SCHEMA)

            # Handle both dict (structured) and string (unstructured) responses.
            if isinstance(result, dict):
                needs_fix: bool = bool(result.get("needs_fix", False))
            else:
                # Unstructured fallback: look for "needs_fix: true" in the text.
                needs_fix = '"needs_fix": true' in str(result).lower()

            if not needs_fix:
                continue

            # Ask the model to fix the seam, returning both paragraphs.
            fix_prompt = f"Paragraph A:\n{para_a}\n\nParagraph B:\n{para_b}"
            fixed = llm.chat(fix_prompt, system=_FIX_SYSTEM)
            fixed_str = str(fixed)

            if "|||" not in fixed_str:
                # Model did not use the separator — skip this pair.
                continue

            parts = fixed_str.split("|||", 1)
            new_a = parts[0].strip()
            new_b = parts[1].strip()

            if not new_a or not new_b:
                # Guard against empty halves from a malformed response.
                continue

            # Only count as changed when the model actually rewrote something.
            if new_a != para_a or new_b != para_b:
                paragraphs[n] = new_a
                paragraphs[n + 1] = new_b
                changed = True

        if not changed:
            # A full pass with no edits means all seams are clean.
            break

    return "\n\n".join(paragraphs)
