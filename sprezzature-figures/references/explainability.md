# Explainability: choosing SHAP, Shapash, TimeSHAP, or LIME

`explain_model.py` answers one question about a fitted model: which input
features drove a given prediction, and by how much? That question has a name,
model explainability, and four engines answer it in different ways. This
file documents how `explain_model.py` actually picks one, what each engine
writes to disk, and where the automatic choice (`--engine auto`) stops being
trustworthy and you should pick by hand.

## The four engines, and what each one is for

**SHAP** (Shapley Additive exPlanations) is the default and the universal
fallback. It borrows an idea from cooperative game theory: treat each
feature as a player in a game where the "payout" is the prediction, and
split that payout fairly among the features based on how much each one
moves the prediction when added in every possible order. The result is one
number per feature per row, the SHAP value, that sums exactly to the
prediction. `explain_model.py` calls `shap.Explainer(model, background)`,
which auto-selects the fast, exact `TreeExplainer` for tree models
(XGBoost, LightGBM, RandomForest, scikit-learn's decision trees) and a
slower, sampling-based `KernelExplainer` for anything else.

**Shapash** is not a separate explanation method. It wraps SHAP and
produces a self-contained HTML report meant for a stakeholder who will
never open a notebook: feature-importance rankings, a searchable table of
individual predictions, plain-language summaries. Reach for it when the
explanation's audience is a business reviewer, not another engineer.

**TimeSHAP** extends the SHAP idea to sequence models (LSTM, GRU,
transformer-based time-series predictors) where a plain SHAP value per
feature does not make sense, because the same feature recurs at every time
step. TimeSHAP instead attributes importance to events (specific time
steps), features, and cells (a feature at a specific time step), pruning
the search space so it stays tractable on long sequences.

**LIME** (Local Interpretable Model-agnostic Explanations) takes a
different approach entirely: instead of computing an exact attribution, it
perturbs the input around one row, fits a simple linear model to the
perturbed neighborhood, and reads the linear model's coefficients as the
explanation. It is the fallback for black-box classifiers where KernelSHAP
would be too slow, at the cost of an explanation that only holds locally,
near that one row, and can shift if you re-run it with a different random
seed.

## The `--engine auto` dispatch rule, verified against the code

`pick_engine()` in `explain_model.py` inspects the model's Python module
path and the data's shape, in this exact order:

1. If the model's module name contains `"torch"` and the data is a 3-D
   array (`data.ndim == 3`, the shape a batch of sequences takes), dispatch
   to **TimeSHAP**.
2. Otherwise, dispatch to **SHAP**. The SHAP path itself then lets
   `shap.Explainer` pick the concrete SHAP algorithm (tree, linear, or
   kernel) from the model type: this is `shap`'s own dispatch, not
   `explain_model.py`'s.

That is the entire automatic rule. **LIME and Shapash are never chosen by
`--engine auto`**; the docstring says so explicitly, and the code confirms
it, `pick_engine()` has no branch that returns either name. You get LIME or
Shapash only by passing `--engine lime` or `--engine shapash` yourself, or
by adding `--report shapash` to layer a Shapash HTML report on top of
whichever engine ran. If your model is a black-box classifier where you
want LIME specifically, say so; the tool will not guess it for you.

## Per-engine output contract

| Engine | Files written to `--out` | Notes |
|---|---|---|
| `shap` | `summary_bar.png`/`.svg`, `summary_beeswarm.png`/`.svg`, one `dependence_<feature>.png`/`.svg` per top-N feature (`--top-n`, default 20), `waterfall_row_<i>.png`/`.svg`, `shap_values.parquet` (best-effort; skipped with a warning if `pyarrow` is not installed) | The waterfall row defaults to whichever row has the largest absolute prediction; override with `--waterfall-row`. |
| `shapash` | `report.html`, `smart_explainer.pkl` (best-effort) | Falls back to `xpl.plot.features_importance().write_html(...)` if the installed Shapash version's `generate_report` API differs. |
| `timeshap` | `timeshap_<name>.csv` per report section, `timeshap_report.json` (the pruning/event/feature/cell parameter dicts actually used) | Requires `--sequence-cols` (comma-separated). Raises a clear `SystemExit` naming the missing package if TimeSHAP is not installed, rather than a bare `ImportError`. |
| `lime` | `lime_row_<i>.html` for each of `--n-explain` rows (default 10) | Uses `predict_proba` when the model has one, otherwise `predict`. |

Every run also writes `summary.json` at the top of `--out`, a small
manifest recording which engine ran and which files it produced; when
`--report shapash` added a report on top of another engine, the manifest
nests it under `summary["shapash_report"]`.

## A concrete walkthrough

Say you have a gradient-boosted churn classifier and want to show a
product manager why the model flagged a specific customer as high risk.

```bash
python -m sprezzature_figures_scripts.explain_model \
    --model churn_model.pkl --data customers.csv \
    --engine auto --report shapash --out ./explain/
```

`--engine auto` inspects `churn_model`'s module (something like
`xgboost.sklearn`), finds no 3-D torch tensor, and dispatches to SHAP,
which writes the summary and dependence plots plus a waterfall for the
single highest-risk row. `--report shapash` then adds `report.html`, the
walkthrough a non-technical reviewer can actually open and click through.

## Where the auto choice is not enough

- **A tree ensemble wrapped in a custom class** (a scikit-learn
  `VotingClassifier`, a stacked ensemble) may not carry a module name
  `pick_engine()` recognizes as a tree family, and will silently fall
  through to plain SHAP's slower kernel path. If explanation runtime spikes
  unexpectedly, pass `--engine shap` explicitly, `shap.Explainer` still
  auto-picks the right underlying algorithm once it sees the actual
  fitted model, independent of the module-name heuristic above.
- **A sequence model that is not a `torch.nn.Module`** (a Keras/TensorFlow
  recurrent model, for instance) will not match the `"torch" in module`
  check and falls back to SHAP, which is not built for that shape of data.
  Pass `--engine timeshap` yourself.
- **Deep image or NLP models** are out of scope for all four engines as
  wired here; none of `explain_model.py`'s paths handle convolutional or
  attention-over-tokens inputs beyond the sequence case TimeSHAP covers.

## Not covered here

`explain_model.py` explains predictions; it does not evaluate whether the
model is any good (see `evaluate-ml-pipeline` or scikit-learn's own report
utilities) and it does not answer counterfactual questions ("what would
have to change for this prediction to flip"), which needs `alibi` or
`DiCE` instead. See the "When NOT to use this skill" section of
`SKILL.md` for the full list.
