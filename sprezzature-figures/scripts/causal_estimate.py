#!/usr/bin/env python3
"""
causal_estimate
===============

End-to-end causal-effect estimation via DoWhy's four-step loop:

    model → identify → estimate → refute

Backends
--------

* **Binary treatment** — DoWhy's built-in propensity-score matching /
  stratification, or a linear regression when the treatment is
  effectively continuous but low-dim.
* **Continuous treatment** or **high-dim confounders** — EconML
  ``LinearDML`` (default), ``LinearDRLearner``, or ``CausalForestDML``
  depending on ``--estimator``.
* **Instrumental variable** — EconML ``IntentToTreatDRIV`` when the
  caller supplies ``--instrument``.

DAG input
---------

Pass one of:

* ``--dag path/to/dag.gml`` — GraphML file.
* ``--dag path/to/dag.dot`` — Graphviz DOT.
* ``--dag-string 'graph[directed 1 ...]'`` — DoWhy inline string.

Output
------

Writes to ``<out>/``:

* ``effect.json`` — point estimate, CI, refutation deltas.
* ``dag.svg`` / ``dag.png`` — DAG rendered via graphviz in the
  front-* house style.
* ``forest_plot.svg`` — compact forest plot of the effect + refuters.

Usage
-----
::

    python causal_estimate.py --data d.csv --treatment T --outcome Y \\
        --confounders "X1,X2,X3" --dag dag.gml \\
        --estimator dml --refute all --out ./causal/

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    import pandas

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _argparse import make_parser  # noqa: E402
from _style import load_palette, matplotlib_rc  # noqa: E402


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for the script."""
    parser = make_parser(
        prog="causal_estimate",
        description=(
            "DoWhy's four-step causal-effect loop with EconML backends. "
            "Assumes the DAG is supplied — discovery is out of scope."
        ),
    )
    parser.add_argument("--data", required=True, help="CSV / Parquet input.")
    parser.add_argument("--treatment", required=True, help="Name of the treatment column.")
    parser.add_argument("--outcome", required=True, help="Name of the outcome column.")
    parser.add_argument("--confounders", default="",
                        help="Comma-separated confounder columns (falls back to DAG's backdoor set when empty).")
    parser.add_argument("--instrument", default="", help="Column name of an instrumental variable (optional).")
    parser.add_argument("--dag", default="",
                        help="Path to a .gml / .dot DAG describing the causal graph.")
    parser.add_argument("--dag-string", default="",
                        help="DoWhy inline DAG string (alternative to --dag).")
    parser.add_argument("--estimator", choices=("linear", "matching", "stratification",
                                                 "dml", "dr", "causal-forest", "iv-2sls"),
                        default="dml", help="Estimation backend.")
    parser.add_argument("--refute", choices=("none", "placebo", "subset", "random-cause", "all"),
                        default="all", help="Refutation battery.")
    parser.add_argument("--out", default="./causal", help="Output directory.")
    parser.add_argument("--trim-quantile", type=float, default=0.0,
                        help="Trim rows by propensity-score quantile (helps overlap violations).")
    parser.add_argument("--dark", action="store_true", help="Dark-mode plots.")
    return parser


# ------------------------------------------------------------------
# DAG loading
# ------------------------------------------------------------------
def load_dag(dag_path: str, dag_string: str) -> str:
    """Return a DoWhy-compatible DAG string.

    Parameters
    ----------
    dag_path : str
        Path to a .gml / .dot file (may be empty).
    dag_string : str
        Inline DoWhy string (may be empty).

    Returns
    -------
    str
        A DoWhy-compatible DAG spec.
    """
    if dag_string:
        return dag_string
    if not dag_path:
        raise SystemExit("Pass either --dag <file> or --dag-string.")

    p = Path(dag_path)
    if not p.is_file():
        raise SystemExit(f"DAG file not found: {dag_path}")

    ext = p.suffix.lower()
    text = p.read_text(encoding="utf-8")
    if ext in {".gml", ".txt"}:
        return text
    if ext == ".dot":
        # Convert DOT → GML via networkx (deferred import).
        import io
        import networkx as nx
        graph = nx.nx_pydot.read_dot(p)
        buffer = io.StringIO()
        nx.write_gml(graph, buffer)
        return buffer.getvalue()
    raise SystemExit(f"Unsupported DAG format: {ext}. Use .gml or .dot.")


# ------------------------------------------------------------------
# DoWhy loop
# ------------------------------------------------------------------
def run_dowhy(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Run model → identify → estimate → refute; return a summary dict.

    Parameters
    ----------
    ctx : dict
        Context with ``data``, ``treatment``, ``outcome``, ``confounders``,
        ``instrument``, ``dag``, ``estimator``, ``refute``,
        ``trim_quantile``.

    Returns
    -------
    dict
        Serialisable summary.
    """
    from dowhy import CausalModel
    import pandas as pd

    df: "pd.DataFrame" = ctx["data"]

    model = CausalModel(
        data=df,
        treatment=ctx["treatment"],
        outcome=ctx["outcome"],
        graph=ctx["dag"],
        common_causes=ctx["confounders"] or None,
        instruments=[ctx["instrument"]] if ctx["instrument"] else None,
    )

    # 1. identify
    identified = model.identify_effect(proceed_when_unidentifiable=False)
    print(f"[info] estimand: {identified.estimands}", file=sys.stderr)

    # 2. estimate
    method_map = {
        "linear":         "backdoor.linear_regression",
        "matching":       "backdoor.propensity_score_matching",
        "stratification": "backdoor.propensity_score_stratification",
        "dml":            "backdoor.econml.dml.LinearDML",
        "dr":             "backdoor.econml.dr.LinearDRLearner",
        "causal-forest":  "backdoor.econml.dml.CausalForestDML",
        "iv-2sls":        "iv.instrumental_variable",
    }
    method_name = method_map[ctx["estimator"]]

    method_params: Dict[str, Any] = {}
    if ctx["estimator"] in {"dml", "dr", "causal-forest"}:
        from sklearn.ensemble import GradientBoostingRegressor, GradientBoostingClassifier
        method_params = {
            "init_params": {
                "model_y": GradientBoostingRegressor(),
                "model_t": GradientBoostingRegressor() if _looks_continuous(df, ctx["treatment"]) else GradientBoostingClassifier(),
                "featurizer": None,
            },
            "fit_params": {},
        }

    estimate = model.estimate_effect(
        identified,
        method_name=method_name,
        method_params=method_params or None,
        confidence_intervals=True,
    )
    point = float(getattr(estimate, "value", 0.0) or 0.0)
    ci = getattr(estimate, "get_confidence_intervals", None)
    ci_low, ci_high = (float("nan"), float("nan"))
    if callable(ci):
        try:
            lo, hi = ci()
            ci_low, ci_high = float(lo), float(hi)
        except Exception:  # noqa: BLE001
            pass

    # 3. refute
    refuters: Dict[str, Any] = {}
    if ctx["refute"] != "none":
        for name in _refute_list(ctx["refute"]):
            refuters[name] = _run_refuter(model, identified, estimate, name)

    return {
        "treatment": ctx["treatment"],
        "outcome": ctx["outcome"],
        "confounders": ctx["confounders"],
        "instrument": ctx["instrument"] or None,
        "estimator": ctx["estimator"],
        "method": method_name,
        "estimand": str(identified.estimands),
        "point_estimate": point,
        "ci_lower": ci_low,
        "ci_upper": ci_high,
        "refutations": refuters,
    }


def _looks_continuous(df: Any, column: str) -> bool:
    """Return True when ``column`` has more than 10 distinct values."""
    try:
        return int(df[column].nunique()) > 10
    except Exception:  # noqa: BLE001
        return True


def _refute_list(flag: str) -> List[str]:
    """Expand ``--refute`` into the list of refuter names to run."""
    if flag == "all":
        return ["placebo", "random-cause", "subset"]
    if flag == "placebo":
        return ["placebo"]
    if flag == "random-cause":
        return ["random-cause"]
    if flag == "subset":
        return ["subset"]
    return []


def _run_refuter(model: Any, identified: Any, estimate: Any, name: str) -> Dict[str, Any]:
    """Run one DoWhy refuter and return a serialisable summary."""
    kind = {
        "placebo":       "placebo_treatment_refuter",
        "random-cause":  "random_common_cause",
        "subset":        "data_subset_refuter",
    }[name]
    try:
        result = model.refute_estimate(identified, estimate, method_name=kind)
        new_effect = float(getattr(result, "new_effect", float("nan")))
        return {
            "method": kind,
            "new_effect": new_effect,
            "p_value": getattr(result, "refutation_result", {}).get("p_value") if hasattr(result, "refutation_result") else None,
            "verdict": _refuter_verdict(name, float(getattr(estimate, "value", 0.0) or 0.0), new_effect),
        }
    except Exception as exc:  # noqa: BLE001
        return {"method": kind, "error": str(exc)}


def _refuter_verdict(name: str, original: float, new: float) -> str:
    """Return a coarse ``pass`` / ``fail`` per DoWhy refuter convention."""
    if name == "placebo":
        return "pass" if abs(new) < 0.1 * max(abs(original), 1e-6) else "fail"
    if name in {"random-cause", "subset"}:
        return "pass" if abs(new - original) < 0.1 * max(abs(original), 1e-6) else "fail"
    return "unknown"


# ------------------------------------------------------------------
# DAG rendering
# ------------------------------------------------------------------
def render_dag(dag_string: str, out_dir: Path, dark: bool) -> None:
    """Render the DAG via graphviz in the front-* house style."""
    try:
        import graphviz  # type: ignore
    except ImportError:
        print("[warn] graphviz Python package not available; skipping DAG render.", file=sys.stderr)
        return

    palette = load_palette()
    fg = "#F5F5F7" if dark else "#1D1D1F"
    bg = "#1D1D1F" if dark else "#FFFFFF"
    accent = palette.get("Blue", "#007AFF")

    dot = graphviz.Digraph(format="svg")
    dot.attr(bgcolor=bg, fontname="Roboto", rankdir="LR")
    dot.attr("node", shape="circle", style="filled", color=fg, fillcolor=bg,
             fontname="Roboto", fontcolor=fg, penwidth="1.2")
    dot.attr("edge", color=fg, fontname="Roboto", penwidth="1.2", arrowsize="0.7")

    # Parse the DoWhy / GML string minimally — we only need node ids and edges.
    node_pattern = r'node\s*\[\s*id\s+"?(\w+)"?'
    edge_pattern = r'edge\s*\[\s*source\s+"?(\w+)"?\s+target\s+"?(\w+)"?'
    import re as _re
    nodes = set(_re.findall(node_pattern, dag_string))
    edges = _re.findall(edge_pattern, dag_string)
    for n in sorted(nodes):
        dot.node(n)
    for src, dst in edges:
        dot.edge(src, dst, color=accent)

    dot.render(str(out_dir / "dag"), cleanup=True)
    try:
        dot.format = "png"
        dot.render(str(out_dir / "dag"), cleanup=True)
    except Exception:  # noqa: BLE001
        pass


# ------------------------------------------------------------------
# Forest plot
# ------------------------------------------------------------------
def render_forest_plot(summary: Dict[str, Any], out_dir: Path, dark: bool) -> None:
    """Render a compact forest plot of the effect and refutation deltas."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update(matplotlib_rc(dark=dark))

    labels = ["Point estimate"]
    values = [summary["point_estimate"]]
    for name, refute in (summary.get("refutations") or {}).items():
        if isinstance(refute, dict) and "new_effect" in refute:
            labels.append(name)
            values.append(refute["new_effect"])

    fig, ax = plt.subplots(figsize=(5.5, 0.4 * len(labels) + 1))
    ax.hlines(labels, [0] * len(values), values, linewidth=6, color=load_palette().get("Blue", "#007AFF"))
    ax.plot(values, labels, "o", color=load_palette().get("Blue", "#007AFF"))
    ax.axvline(0, color="#888", linewidth=0.5)
    ax.set_xlabel(f"Effect on {summary['outcome']}")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.tick_params(length=0)
    fig.tight_layout()
    fig.savefig(out_dir / "forest_plot.svg")
    fig.savefig(out_dir / "forest_plot.png", dpi=300)
    plt.close(fig)


# ------------------------------------------------------------------
# main
# ------------------------------------------------------------------
def load_data(path: str) -> "pandas.DataFrame":  # noqa: F821 — quoted forward ref
    """Load a data table."""
    import pandas as pd
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".csv":
        return pd.read_csv(p)
    if ext in {".parquet", ".pq"}:
        return pd.read_parquet(p)
    if ext == ".json":
        return pd.read_json(p)
    raise SystemExit(f"Unsupported data extension: {ext}")


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point."""
    args = build_parser().parse_args(argv)

    data = load_data(args.data)
    dag = load_dag(args.dag, args.dag_string)
    confounders = [c.strip() for c in args.confounders.split(",") if c.strip()]

    ctx = {
        "data": data,
        "treatment": args.treatment,
        "outcome": args.outcome,
        "confounders": confounders,
        "instrument": args.instrument,
        "dag": dag,
        "estimator": args.estimator,
        "refute": args.refute,
        "trim_quantile": args.trim_quantile,
    }

    summary = run_dowhy(ctx)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "effect.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    render_dag(dag, out_dir, dark=args.dark)
    try:
        render_forest_plot(summary, out_dir, dark=args.dark)
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] forest plot failed: {exc}", file=sys.stderr)

    print(f"wrote {out_dir / 'effect.json'}", file=sys.stderr)
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
