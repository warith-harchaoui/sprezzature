# Causal effect estimation: DoWhy's four-step loop, EconML backends, refuters

`causal_estimate.py` answers a harder question than a correlation plot
ever can: if you changed the treatment for one unit, how much would the
outcome move, holding everything else fixed? That is a causal effect, and
estimating it from data you did not experimentally control (observational
data) needs more machinery than `df.corr()`. This file documents the
actual four-step loop the script runs, the estimator backends behind
`--estimator`, and the refutation battery behind `--refute`, all verified
against the code rather than assumed from a summary.

## The four steps, in the order the script runs them

DoWhy structures causal estimation as **model, identify, estimate,
refute**. `causal_estimate.py` calls these in that order and stops if an
earlier step fails.

1. **Model.** You supply a causal graph, a diagram of which variable is
   assumed to cause which, drawn as arrows with no cycles (a directed
   acyclic graph, DAG), plus the treatment and outcome column names.
   `causal_estimate.py` does not build this graph for you; that is a
   deliberate scope boundary (see "What this does not do" below). Pass it
   as `--dag path/to/dag.gml` (GraphML), `--dag path/to/dag.dot`
   (Graphviz DOT, converted to GML internally via `networkx`), or
   `--dag-string '...'` (DoWhy's inline string form).
2. **Identify.** `model.identify_effect(proceed_when_unidentifiable=False)`
   asks: given this graph, is the causal effect even computable from the
   variables you have? The `proceed_when_unidentifiable=False` flag means
   the script refuses to guess when the graph does not license an answer,
   rather than silently returning a number that is not actually causal.
3. **Estimate.** The identified estimand is handed to one of seven backend
   methods, chosen by `--estimator` (table below).
4. **Refute.** Unless `--refute none`, the estimate is stress-tested by
   the refutation battery (also documented below) before you should trust
   it.

## Estimator backends, and when each applies

`causal_estimate.py` maps `--estimator` to a DoWhy method name through a
fixed lookup table in the code:

| `--estimator` | DoWhy method name | When it applies |
|---|---|---|
| `linear` | `backdoor.linear_regression` | Simple linear confounding; treatment can be continuous or binary. |
| `matching` | `backdoor.propensity_score_matching` | Binary treatment; matches treated and untreated units with similar propensity scores. |
| `stratification` | `backdoor.propensity_score_stratification` | Binary treatment; bins units into propensity strata instead of one-to-one matching. |
| `dml` (default) | `backdoor.econml.dml.LinearDML` | Continuous or high-dimensional treatment, via EconML's Double Machine Learning. |
| `dr` | `backdoor.econml.dr.LinearDRLearner` | Doubly-robust estimation: consistent if either the outcome model or the propensity model is correctly specified, not necessarily both. |
| `causal-forest` | `backdoor.econml.dml.CausalForestDML` | Heterogeneous effects, when the treatment effect itself is expected to vary across units. |
| `iv-2sls` | `iv.instrumental_variable` | An instrument is available (`--instrument`) to handle unmeasured confounding between treatment and outcome. |

For the three EconML backends (`dml`, `dr`, `causal-forest`), the script
also wires up the nuisance models DoWhy needs internally: a
`GradientBoostingRegressor` for the outcome model, and for the treatment
model a `GradientBoostingRegressor` if the treatment column looks
continuous (more than 10 distinct values, checked by `_looks_continuous`)
or a `GradientBoostingClassifier` otherwise. That 10-value cutoff is a
heuristic in the code, not a statistical rule; a treatment with, say, 8
ordered levels will be treated as categorical even if you think of it as
continuous, override by re-encoding the column if that matters to your
analysis.

## The refutation battery

A causal estimate that has not been stress-tested is a number you are
choosing to trust, not one you have earned. `--refute all` (the default)
runs three refuters, each checking a different way the estimate could be
fragile:

| `--refute` name | DoWhy method | What it checks | Pass condition, as coded |
|---|---|---|---|
| `placebo` | `placebo_treatment_refuter` | Replaces the real treatment with random noise and re-estimates. A real effect should collapse toward zero. | New effect's absolute value is under 10% of the original estimate's absolute value. |
| `random-cause` | `random_common_cause` | Adds a random, irrelevant confounder and re-estimates. A robust effect should barely move. | New effect within 10% of the original. |
| `subset` | `data_subset_refuter` | Re-estimates on a random subset of the data. A robust effect should be stable across subsets. | New effect within 10% of the original. |

One naming note worth flagging plainly: `SKILL.md`'s summary calls these
"placebo / random-common-cause / data-subset", closer to DoWhy's own
method names than to the `--refute` flag values the CLI actually accepts
(`placebo`, `random-cause`, `subset`). Use the flag values in the table
above; they are what `argparse` will accept.

Each refuter's pass/fail verdict is a fixed 10% relative-change threshold
hardcoded in `_refuter_verdict()`, not a statistical test with a
principled significance level. Treat "fail" as a prompt to look closer at
that specific instability, not as a formal hypothesis-test rejection.

If a refuter itself throws (a common failure mode: `random_common_cause`
occasionally fails to converge on small datasets), the script catches the
exception and records `{"method": ..., "error": str(exc)}` in the output
rather than crashing the whole run, so a single refuter's failure does not
lose the point estimate you already have.

## DAG encoding

Three ways to hand the script your causal graph:

- **`--dag path.gml`** (or `.txt`): a GraphML-flavored text format read
  directly, `node [ id "X" ]` and `edge [ source "X" target "Y" ]` blocks.
- **`--dag path.dot`**: standard Graphviz DOT, converted to GML internally
  via `networkx.nx_pydot.read_dot` before DoWhy sees it.
- **`--dag-string '...'`**: DoWhy's own inline string syntax, passed
  straight through, useful for a graph small enough to write inline in a
  script or CI config without a separate file.

The rendered `dag.svg` (and a best-effort `dag.png` companion) comes from
a minimal regex-based parse of the same GML-style node/edge blocks, drawn
with `graphviz.Digraph` in the house palette: foreground and background
flip for `--dark`, and edges are colored with the palette's `Blue` accent.
If `graphviz`'s Python package is not installed, the script prints a
warning and skips the DAG image rather than failing the whole run, the
`effect.json` output is unaffected either way.

## Output files

Everything lands under `--out` (default `./causal/`):

- **`effect.json`** the full summary: treatment, outcome, confounders,
  instrument, chosen estimator and method name, the estimand DoWhy
  identified, the point estimate, a confidence interval when the estimator
  supports one, and every refuter's result.
- **`dag.svg`** / **`dag.png`** the rendered causal graph, house-styled.
- **`forest_plot.svg`** / **`.png`** a compact horizontal plot placing the
  point estimate alongside each refuter's re-estimated effect, so a
  reader can see at a glance whether the refuters moved the number.

## What this does not do

`causal_estimate.py` assumes you already know, or have hypothesized, the
causal graph; it does not discover one from data. That is a genuinely
different problem, causal discovery, and belongs to tools like
`causal-learn`, not this script. It also does not handle
interrupted-time-series or synthetic-control designs (`CausalImpact`,
`SparseSC` cover those); this script's model is exclusively DoWhy's
backdoor/instrumental-variable framework over a supplied DAG. See the
"When NOT to use this skill" section of `SKILL.md` for the complete
boundary.
