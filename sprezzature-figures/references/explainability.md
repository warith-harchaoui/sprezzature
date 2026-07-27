# Model explainability — SHAP / Shapash / TimeSHAP / LIME

> **Experimental.** This surface is wired at the command level, not yet at the
> visual-design level: SHAP / Shapash / LIME render through matplotlib, so their
> figures do **not** inherit the Vega-first house style the rest of the system
> guarantees. Treat the output as a diagnostic, not a publication-ready figure,
> until it has dedicated end-to-end tests, real worked case studies, and
> Vega-conforming output. And read explanations for what they are, *local
> approximations* of a model, not ground truth: state the assumptions (feature
> independence for kernel SHAP, locality for LIME) and their failure modes
> before drawing conclusions.

Pick the engine from the **model** and the **audience**, not from
library familiarity. The dispatcher in `explain_model.py --engine auto`
follows the same tree.

Sources: [SHAP docs](https://shap.readthedocs.io/),
[Shapash docs](https://shapash.readthedocs.io/),
[TimeSHAP repo](https://github.com/feedzai/timeshap),
[LIME paper](https://arxiv.org/abs/1602.04938) and
[Interpretable ML by Molnar](https://christophm.github.io/interpretable-ml-book/).

## Engine selection matrix

| Model shape | Data shape | Audience | Engine | Why |
|---|---|---|---|---|
| Tree ensemble (`XGBoost`, `LightGBM`, `RandomForest`, `sklearn.tree`) | Tabular 2-D | Modelers / reviewers | **SHAP TreeExplainer** | Exact SHAP values in polynomial time; the reference implementation. |
| Linear / logistic | Tabular 2-D | Modelers / reviewers | **SHAP LinearExplainer** | Closed-form contributions from the coefficient vector; no sampling noise. |
| Kernel / SVM / arbitrary black-box | Tabular 2-D | Modelers / reviewers | **SHAP KernelExplainer** | Model-agnostic; slow but universal. |
| Any of the above | Tabular 2-D | **Business stakeholders** | **Shapash** | Full HTML report with global importance, per-row waterfalls, filters. Wraps SHAP; user sees a dashboard, not a plot. |
| Recurrent / attention-based (LSTM, GRU, Transformer classifier) | Sequence 3-D `(N, T, features)` | Modelers | **TimeSHAP** | SHAP alone assigns one contribution per feature; TimeSHAP decomposes along the time axis, so you see *when* in the sequence each feature mattered. |
| Deep black-box (large CNN, non-differentiable ensemble) where SHAP is impractical | Tabular / image | Modelers | **LIME** | Local linear approximation around one row; use as a fallback when KernelSHAP is too slow. |

## What each engine emits

### SHAP (default)

Writes to `<out>/`:
- `summary_bar.png` + `.svg` — global mean absolute SHAP per feature.
- `summary_beeswarm.png` + `.svg` — global impact + direction.
- `dependence_<feature>.png` + `.svg` — one per top-N feature.
- `waterfall_row_<i>.png` + `.svg` — one row (largest absolute
  prediction by default; override with `--waterfall-row <i>`).
- `shap_values.parquet` — every SHAP value for downstream analysis.

### Shapash

Writes to `<out>/`:
- `report.html` — the full Shapash HTML report (global + local +
  filters). Open in a browser; no server needed.
- `smart_explainer.pkl` — the underlying `SmartExplainer` for further
  interactive use in a notebook.
- Everything SHAP writes (Shapash uses SHAP under the hood; the
  intermediate artefacts are kept).

### TimeSHAP

Writes to `<out>/`:
- `event_level.png` + `.svg` — attribution per event (time step).
- `feature_level.png` + `.svg` — attribution per feature averaged
  over time.
- `cell_level.png` + `.svg` — the full `(T × features)` grid.
- `pruning.png` + `.svg` — the pruning heuristic's convergence.
- `timeshap_report.json` — machine-readable summary.

### LIME

Writes to `<out>/`:
- `lime_row_<i>.html` — one interactive explanation per row.
- `lime_summary.parquet` — top-K contribution features per row for
  downstream analysis.

## Guardrails

- **Sample size for SHAP.** KernelSHAP is O(2^n) in the number of
  features; the dispatcher subsamples to 100 background rows by
  default and 500 explained rows. Override with `--n-background` and
  `--n-explain`.
- **Categorical encoding.** SHAP values are only interpretable if the
  categorical columns are labelled. Pass `--categorical-cols "a,b,c"`
  or the dispatcher will infer from `pandas.CategoricalDtype`.
- **Cross-model consistency.** Never compare raw SHAP values across
  different models on different train sets. Compare *ranks* of
  features, not magnitudes.
- **Business narrative.** Shapash's HTML report is designed for
  non-technical readers; use it in stakeholder meetings. Raw SHAP
  plots are for the modeler.
- **Do not confuse SHAP with causality.** SHAP tells you what the
  *model uses*; it does not tell you what *causes* the outcome. For
  causal questions, use `causal_estimate.py`.

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| SHAP values sum to a wrong baseline | Model output space (probability vs log-odds) mismatched | Pass `--link logit` for binary classification, or `--output raw` for the raw score. |
| Beeswarm plot is illegible | Too many features | Cap with `--top-n 20`. |
| Shapash report fails on `pandas 2.x` | Shapash pinned to older pandas | `pip install "shapash>=2.5"` or run under `pandas<2`. |
| TimeSHAP is slow | Sequence too long, pruning threshold too tight | Raise `--tolerance 0.05` (default 0.025). |
| LIME explanations differ between runs | LIME samples locally at random | Pass `--random-state 42` for reproducibility. |
