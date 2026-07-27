#!/usr/bin/env python3
"""
explain_model
=============

Model-explainability dispatcher. Given a fitted model and a dataset,
picks the right engine and emits summary + local explanations in the
front-* house style.

Engines
-------

======================  ==========================================================
``shap`` (default)      Tree, linear, kernel — universal fallback via
                        :class:`shap.Explainer`.
``shapash``             Full HTML report for a business stakeholder — wraps
                        SHAP under the hood.
``timeshap``            Recurrent / attention-based time-series predictors
                        (LSTM, GRU, transformer classifier on sequences).
``lime``                Deep black-box classifiers where KernelSHAP is
                        impractical; local linear approximation only.
======================  ==========================================================

Dispatch (when ``--engine auto``):

    tree model (XGBoost / LightGBM / RandomForest / sklearn.tree)
        → SHAP TreeExplainer
    linear / logistic
        → SHAP LinearExplainer
    torch.nn.Module + 3-D input
        → TimeSHAP
    otherwise
        → SHAP Explainer (falls back to KernelSHAP)

Pass ``--report shapash`` at any time to add the Shapash HTML report on
top of whichever engine ran.

Usage
-----
::

    # Auto-dispatch (default) on a scikit-learn model
    python explain_model.py --model model.pkl --data X.csv --out ./explain/

    # Business-facing report
    python explain_model.py --model model.pkl --data X.csv \\
        --engine shapash --report shapash --out ./explain/

    # LSTM time-series classifier
    python explain_model.py --model seq_model.pkl --data X.npy \\
        --engine timeshap --sequence-cols "t_0,t_1,t_2,t_3,t_4" \\
        --out ./explain/

Notes
-----
* Python 3.10+, ``pip install -r requirements-explain.txt``.
* Deferred imports throughout: importing this module does not pull
  shap / shapash / timeshap / lime unless the corresponding path is
  taken.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _argparse import make_parser  # noqa: E402
from _style import matplotlib_rc  # noqa: E402


# ------------------------------------------------------------------
# Model / data loading
# ------------------------------------------------------------------
def load_model(path: str) -> Any:
    """Load a pickled model.

    .. warning::
        Unpickling executes arbitrary code. Only load a model file **you
        produced or trust** — never a pickle from an untrusted source.

    Parameters
    ----------
    path : str
        Filesystem path to a pickle. ``joblib`` is used when the file
        extension is ``.joblib``.

    Returns
    -------
    object
        The unpickled model.
    """
    p = Path(path)
    if p.suffix.lower() == ".joblib":
        import joblib
        return joblib.load(p)
    with p.open("rb") as fh:
        return pickle.load(fh)


def load_data(path: str) -> Any:
    """Load a data matrix.

    Parameters
    ----------
    path : str
        Path to CSV / JSON / Parquet / NPY.

    Returns
    -------
    pandas.DataFrame or numpy.ndarray
        A DataFrame for tabular inputs; a numpy array for NPY (needed
        for the TimeSHAP path).
    """
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".csv":
        import pandas as pd
        return pd.read_csv(p)
    if ext == ".json":
        import pandas as pd
        return pd.read_json(p)
    if ext in {".parquet", ".pq"}:
        import pandas as pd
        return pd.read_parquet(p)
    if ext == ".npy":
        import numpy as np
        return np.load(p)
    raise SystemExit(f"Unsupported data extension: {ext}")


# ------------------------------------------------------------------
# Engine dispatch
# ------------------------------------------------------------------
def pick_engine(model: Any, data: Any) -> str:
    """Auto-dispatch to SHAP or TimeSHAP from model + data shape.

    Parameters
    ----------
    model : object
        The fitted model.
    data : pandas.DataFrame or numpy.ndarray
        Feature matrix or sequence tensor.

    Returns
    -------
    str
        ``"timeshap"`` for a 3-D torch sequence model, otherwise ``"shap"``.
        ``"lime"`` and ``"shapash"`` are never auto-selected — they are only
        used when the user passes ``--engine`` explicitly (LIME as a black-box
        fallback; Shapash for its HTML report).
    """
    module = getattr(type(model), "__module__", "") or ""
    lower = module.lower()

    if "torch" in lower and hasattr(data, "ndim") and getattr(data, "ndim", 0) == 3:
        return "timeshap"
    if any(key in lower for key in ("xgboost", "lightgbm", "catboost", "sklearn.ensemble", "sklearn.tree")):
        return "shap"
    if any(key in lower for key in ("sklearn.linear_model", "linear")):
        return "shap"
    return "shap"


# ------------------------------------------------------------------
# SHAP path
# ------------------------------------------------------------------
def run_shap(model: Any, data: Any, ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Compute SHAP explanations and write plots to ``ctx['out']``.

    Parameters
    ----------
    model : object
        Fitted estimator.
    data : pandas.DataFrame
        Feature matrix.
    ctx : dict
        Context bag with keys ``out`` (Path), ``n_background`` (int),
        ``n_explain`` (int), ``top_n`` (int), ``dark`` (bool),
        ``waterfall_row`` (int or None), ``link`` (str).

    Returns
    -------
    dict
        Summary metadata (feature ranks, files written).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update(matplotlib_rc(dark=ctx.get("dark", False)))
    import numpy as np
    import shap

    out: Path = ctx["out"]
    out.mkdir(parents=True, exist_ok=True)

    n_background = min(ctx.get("n_background", 100), len(data))
    n_explain = min(ctx.get("n_explain", 500), len(data))
    background = data.sample(n_background, random_state=42) if hasattr(data, "sample") else data[:n_background]
    explain_rows = data.sample(n_explain, random_state=7) if hasattr(data, "sample") else data[:n_explain]

    explainer = shap.Explainer(model, background)
    shap_values = explainer(explain_rows)

    # summary bar
    shap.plots.bar(shap_values, show=False, max_display=ctx.get("top_n", 20))
    plt.tight_layout()
    plt.savefig(out / "summary_bar.png", dpi=300)
    plt.savefig(out / "summary_bar.svg")
    plt.close()

    # summary beeswarm
    shap.plots.beeswarm(shap_values, show=False, max_display=ctx.get("top_n", 20))
    plt.tight_layout()
    plt.savefig(out / "summary_beeswarm.png", dpi=300)
    plt.savefig(out / "summary_beeswarm.svg")
    plt.close()

    # dependence plots for top-N features by mean |shap|
    mean_abs = np.abs(shap_values.values).mean(axis=0)
    top_idx = np.argsort(-mean_abs)[: ctx.get("top_n", 5)]
    feat_names = list(explain_rows.columns) if hasattr(explain_rows, "columns") else [f"f{i}" for i in range(explain_rows.shape[1])]
    for i in top_idx:
        try:
            shap.plots.scatter(shap_values[:, int(i)], show=False)
            plt.tight_layout()
            plt.savefig(out / f"dependence_{feat_names[int(i)]}.png", dpi=300)
            plt.savefig(out / f"dependence_{feat_names[int(i)]}.svg")
            plt.close()
        except Exception as exc:  # noqa: BLE001 — plot best-effort
            print(f"[warn] dependence plot for {feat_names[int(i)]} failed: {exc}", file=sys.stderr)

    # waterfall for the row with largest absolute prediction
    row_idx = ctx.get("waterfall_row")
    if row_idx is None:
        try:
            preds = model.predict(explain_rows) if hasattr(model, "predict") else np.abs(shap_values.values).sum(axis=1)
            row_idx = int(np.argmax(np.abs(preds)))
        except Exception:  # noqa: BLE001
            row_idx = 0
    try:
        shap.plots.waterfall(shap_values[row_idx], show=False)
        plt.tight_layout()
        plt.savefig(out / f"waterfall_row_{row_idx}.png", dpi=300)
        plt.savefig(out / f"waterfall_row_{row_idx}.svg")
        plt.close()
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] waterfall failed: {exc}", file=sys.stderr)

    # Persist shap values
    try:
        import pandas as pd
        vals_df = pd.DataFrame(shap_values.values, columns=feat_names)
        vals_df.to_parquet(out / "shap_values.parquet")
    except Exception as exc:  # noqa: BLE001 — parquet needs pyarrow; optional artifact
        # Unlike the plots, surface a note so the missing artifact isn't silent
        # (matches the sibling plot handlers' [warn] convention).
        print(f"[warn] could not write shap_values.parquet ({exc}); skipping.",
              file=sys.stderr)

    return {
        "engine": "shap",
        "n_background": n_background,
        "n_explain": n_explain,
        "top_features": [feat_names[int(i)] for i in top_idx],
        "waterfall_row": int(row_idx),
        "files": [p.name for p in sorted(out.glob("*"))],
    }


# ------------------------------------------------------------------
# Shapash path
# ------------------------------------------------------------------
def run_shapash(model: Any, data: Any, ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Emit a Shapash HTML report + underlying SHAP artefacts."""
    from shapash import SmartExplainer

    out: Path = ctx["out"]
    out.mkdir(parents=True, exist_ok=True)

    xpl = SmartExplainer(model=model)
    y_pred = None
    if hasattr(model, "predict"):
        try:
            y_pred = model.predict(data)
        except Exception:  # noqa: BLE001
            pass
    xpl.compile(x=data, y_pred=y_pred)

    report_path = out / "report.html"
    try:
        xpl.generate_report(output_file=str(report_path))
    except Exception:
        # Older Shapash API — fall back to save_html on the WebApp
        xpl.plot.features_importance().write_html(str(report_path))

    try:
        xpl.save(str(out / "smart_explainer.pkl"))
    except Exception:  # noqa: BLE001
        pass

    return {"engine": "shapash", "report": report_path.name, "files": [p.name for p in sorted(out.glob("*"))]}


# ------------------------------------------------------------------
# TimeSHAP path
# ------------------------------------------------------------------
def run_timeshap(model: Any, data: Any, ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Compute TimeSHAP attributions for a sequence model."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update(matplotlib_rc(dark=ctx.get("dark", False)))
    import numpy as np

    try:
        from timeshap.explainer import local_report  # type: ignore
        # Availability guard: verify the timeshap.plot submodule imports too
        # (distinct from timeshap.explainer above); the symbol itself is unused.
        from timeshap.plot import plot_temp_coalition_pruning  # type: ignore  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "TimeSHAP is not installed. Run `python scripts/install_figures.py --tier explain`."
        ) from exc

    out: Path = ctx["out"]
    out.mkdir(parents=True, exist_ok=True)

    sequence_cols: List[str] = ctx.get("sequence_cols") or []

    # Wrap the model in the callable TimeSHAP expects
    def model_fn(x: "np.ndarray") -> "np.ndarray":
        """Adapt the loaded model to the ``(x) -> predictions`` callable TimeSHAP expects."""
        return model(x) if callable(model) else model.predict(x)

    pruning_dict = {"tol": ctx.get("tolerance", 0.025)}
    event_dict = {"rs": 42, "nsamples": 1000}
    feature_dict = {"rs": 42, "nsamples": 1000, "feature_names": sequence_cols}
    cell_dict = {"rs": 42, "nsamples": 1000, "top_x_events": 5, "top_x_feats": 5}

    # local_report returns a dict of plots + intermediate frames
    report = local_report(
        model_fn,
        pruning_dict,
        event_dict,
        feature_dict,
        cell_dict,
        data if isinstance(data, np.ndarray) else np.asarray(data),
        entity_col=None,
        baseline=None,
    )

    # Persist the frames
    for name, frame in getattr(report, "items", lambda: [])():  # type: ignore[misc]
        try:
            frame.to_csv(out / f"timeshap_{name}.csv", index=False)
        except Exception:  # noqa: BLE001
            pass

    (out / "timeshap_report.json").write_text(
        json.dumps({"pruning": pruning_dict, "event": event_dict, "feature": feature_dict, "cell": cell_dict}, indent=2),
        encoding="utf-8",
    )

    return {"engine": "timeshap", "files": [p.name for p in sorted(out.glob("*"))]}


# ------------------------------------------------------------------
# LIME path
# ------------------------------------------------------------------
def run_lime(model: Any, data: Any, ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Emit LIME HTML explanations for a black-box classifier."""
    from lime.lime_tabular import LimeTabularExplainer
    import numpy as np

    out: Path = ctx["out"]
    out.mkdir(parents=True, exist_ok=True)

    values = data.values if hasattr(data, "values") else np.asarray(data)
    feat_names = list(data.columns) if hasattr(data, "columns") else [f"f{i}" for i in range(values.shape[1])]

    explainer = LimeTabularExplainer(
        training_data=values,
        feature_names=feat_names,
        discretize_continuous=True,
        random_state=42,
    )

    n_explain = min(ctx.get("n_explain", 10), len(values))
    predict_fn = model.predict_proba if hasattr(model, "predict_proba") else model.predict

    for i in range(n_explain):
        exp = explainer.explain_instance(values[i], predict_fn, num_features=min(15, values.shape[1]))
        exp.save_to_file(str(out / f"lime_row_{i}.html"))

    return {"engine": "lime", "n_explained": n_explain, "files": [p.name for p in sorted(out.glob("*"))]}


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for the script."""
    parser = make_parser(
        prog="explain_model",
        description=(
            "Model-explainability dispatcher — SHAP / Shapash / TimeSHAP / "
            "LIME. Auto-picks by model + data shape unless --engine is set."
        ),
    )
    parser.add_argument("--model", required=True,
                        help="Path to a pickled / joblib model. Loading unpickles it, "
                             "which runs arbitrary code — only pass a model you trust.")
    parser.add_argument("--data", required=True, help="Path to CSV / JSON / Parquet / NPY.")
    parser.add_argument("--engine", choices=("auto", "shap", "shapash", "timeshap", "lime"),
                        default="auto", help="Explainability engine (default: auto).")
    parser.add_argument("--report", choices=("none", "shapash"), default="none",
                        help='Add a Shapash HTML report on top of the chosen engine.')
    parser.add_argument("--out", default="./explain", help="Output directory.")
    parser.add_argument("--n-background", type=int, default=100, help="SHAP background sample size.")
    parser.add_argument("--n-explain", type=int, default=500, help="Rows to explain (SHAP) / LIME instances.")
    parser.add_argument("--top-n", type=int, default=20, help="Top-N features for summary + dependence plots.")
    parser.add_argument("--waterfall-row", type=int, default=None, help="Row index for the SHAP waterfall.")
    parser.add_argument("--sequence-cols", default="", help="Comma-separated column names for TimeSHAP.")
    parser.add_argument("--tolerance", type=float, default=0.025, help="TimeSHAP pruning tolerance.")
    parser.add_argument("--link", choices=("identity", "logit"), default="identity",
                        help="SHAP link function (use logit for binary classification).")
    parser.add_argument("--dark", action="store_true", help="Dark-mode plots.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point."""
    args = build_parser().parse_args(argv)

    model = load_model(args.model)
    data = load_data(args.data)

    engine = args.engine
    if engine == "auto":
        engine = pick_engine(model, data)
    print(f"[info] engine = {engine}", file=sys.stderr)

    ctx: Dict[str, Any] = {
        "out": Path(args.out),
        "n_background": args.n_background,
        "n_explain": args.n_explain,
        "top_n": args.top_n,
        "waterfall_row": args.waterfall_row,
        "link": args.link,
        "dark": args.dark,
        "sequence_cols": [c.strip() for c in args.sequence_cols.split(",") if c.strip()],
        "tolerance": args.tolerance,
    }

    dispatch = {
        "shap": run_shap,
        "shapash": run_shapash,
        "timeshap": run_timeshap,
        "lime": run_lime,
    }
    summary = dispatch[engine](model, data, ctx)

    if args.report == "shapash" and engine != "shapash":
        summary["shapash_report"] = run_shapash(model, data, ctx)

    summary_path = Path(args.out) / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"wrote {summary_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
