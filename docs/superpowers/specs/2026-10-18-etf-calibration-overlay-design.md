# ETF Calibration Overlay — Design

Date: 2026-10-18  
Repo: `machine-learning-for-trading` (Stefan Jansen, 3rd edition companion)  
Status: approved — plan at `docs/superpowers/plans/2026-10-18-etf-calibration-overlay.md`

## Purpose

Give a solo retail operator a coherent path through the book's notebooks so they can **find, evaluate, and validate strategies under the ML4T conventions**, starting with one calibration pass on the published ETF case study. This pass teaches the process and the evidence boundary. It does not produce deployable alpha or a live signal.

A later, separate spec will point the same gates at operator universes on `F:\Market_Data` (FX / liquid ETFs or CFDs) for paper-path research toward MetaTrader 5. That work is out of scope here.

## Decisions (locked)

| Decision | Choice |
|----------|--------|
| Program shape | Calibration first (ETF), then a second operator-universe spec |
| Deliverables | Operator guide + one readout notebook |
| Notebook role | Reader only; guide opens existing stages `01`, `05`, `13`, `20` |
| Placement | Sidecar under `docs/operator/` (not stage 21 inside `case_studies/etfs/`) |
| Results source | Downloaded ETF artifact bundle / `run_log/registry.db` |
| Live trading | Out of scope (Ch25–26 demos only; no MT5 in this spec) |

## Background (book and repo conventions)

The third edition and this repository share one workflow: data infrastructure and strategy research, an **evidence boundary** between exploration and confirmation, then deployment and monitoring. Case studies are the structural centerpiece: the same phase order maps to book chapters (Ch6–20).

Relevant conventions this design must respect:

- A strategy is a **versioned trading setup** (`config/setup.yaml`: universe, decision schedule, costs, walk-forward), not a model alone.
- Stages write artifacts; later stages consume them. Metrics live in **`run_log/registry.db`** (content-addressed runs).
- Published case-study artifacts are for learning and reproduction; the repo is **not** a research platform or production system (`docs/what-this-is.md`).
- Experimentation that changes configs uses a **writable experiment** copy (`scripts/create_experiment.py`); the release baseline stays untouched. This calibration overlay does **not** create an experiment.
- Notebooks are **Jupytext** pairs (`.py` + `.ipynb`), run from the **repository root**.

ETF is the calibration case: daily data, monthly decisions, material costs, broadest model-family comparison, and the teaching point that **IC leaders need not be Sharpe leaders** after portfolio construction.

## Scope

### In

1. **`docs/operator/etf-calibration.md`** — reading map and continue-only-if checklists.
2. **`docs/operator/etf_calibration.py`** and paired **`etf_calibration.ipynb`** (Jupytext) — read-only registry readout.
3. Minimal verification that the readout refuses a missing registry and that guide links point at real paths.

### Out

- New or edited numbered stages under `case_studies/etfs/01`–`20`.
- Retraining, feature rebuilds, hyperparameter sweeps, writable experiments.
- Operator universes, `F:\Market_Data` adapters, MT5 / broker integration.
- Claiming published ETF results as edge or a go-live signal.

## Architecture

```text
Book Ch1, Ch6  ──►  docs/operator/etf-calibration.md  ──►  open in place:
                                                          case_studies/etfs/
                                                            01_feasibility_analysis
                                                            05_evaluation
                                                            13_model_analysis
                                                            20_strategy_analysis
                                                              │
                                                              ▼
download_artifacts --cs etfs  ──►  run_log/registry.db  ──►  docs/operator/etf_calibration
                                                              (read-only readout)
```

The overlay never becomes part of the stage chain. Upstream notebook guards and CI that enumerate numbered case-study stages must not pick it up as a book stage.

## Components

### 1. Guide — `docs/operator/etf-calibration.md`

Fixed reading order:

1. Book / chapter guides: **Ch1** (process, evidence boundary) and **Ch6** (setup, walk-forward, run log).
2. **`case_studies/etfs/README.md`** pipeline table (full stage list; operator opens only the four below for calibration).
3. Open existing stages in place (do not reimplement):
   - `01_feasibility_analysis` — universe, eligibility, horizon vs cost, walk-forward demo.
   - `05_evaluation` — feature–label IC triage.
   - `13_model_analysis` — cross-family IC / stability (reads registry).
   - `20_strategy_analysis` — end-to-end assessment / tearsheet outputs.
4. Run **`docs/operator/etf_calibration`** for the fixed readout.
5. Stop: write what the result does and does not establish. Defer operator-universe work to a **second spec**.

Each stop includes a short **continue only if** checklist (e.g. free data present if a stage needs it; artifact bundle installed before registry-dependent stages; stage `20` produces its assessment outputs; readout prints all six sections).

Prerequisites called out once at the top:

```bash
# From repository root (uv path; Docker equivalent per docs/running-notebooks.md)
uv run python data/download_all.py --free-only   # as needed for opened stages
uv run python scripts/download_artifacts.py --cs etfs
```

### 2. Readout notebook — `docs/operator/etf_calibration.py` (+ `.ipynb`)

**Behavior**

- Run from repository root; resolve `case_studies/etfs/run_log/registry.db` (and any assessment artifact paths stage `20` already documents).
- **Read-only**: no training, no writes under `case_studies/etfs/run_log/`, no edits to `setup.yaml` or training menus.
- Inline explanation suitable as a teaching pass for a solo operator.

**Fixed readout sections (order locked)**

1. **Bundle present** — path to `registry.db`; artifact version note if available.
2. **Selected configuration** — label, model family / preset, allocation and cost settings as recorded for the book's selected path (from registry / stage-20 outputs, not recomputed).
3. **IC vs traded Sharpe** — show the teaching point that rank-IC leaders need not be Sharpe leaders after portfolio construction.
4. **Cost survival** — whether the selected path still looks positive under the ETF cost model in the published backtests.
5. **Sealed holdout** — holdout prediction / backtest rows (`split='holdout'` / `stage='holdout'`) if present; otherwise state they are missing.
6. **Does not establish** — bullets: not retail CFDs; not MT5; not the operator's universe; not unbiased alpha after search; not a go-live signal. Cite Ch1 evidence boundary and `docs/what-this-is.md`.

**Errors**

| Condition | Behavior |
|-----------|----------|
| Missing `registry.db` | Fail with exact command: `uv run python scripts/download_artifacts.py --cs etfs` |
| Empty / unusable registry | Fail loudly; no synthetic or placeholder metrics |
| Accidental write path | Must not create or modify files under `case_studies/etfs/run_log/` |

### 3. Verification

- Guide links resolve to real chapter directories and ETF stage files (`01`, `05`, `13`, `20`).
- One small assert-based check (or tiny test file): readout entrypoint **refuses** without `registry.db`; **succeeds** when a fixture or downloaded path is present (fixture preferred for CI-like local checks if download is heavy).
- Manual gate: follow the guide once; notebook prints all six sections without training.

## Success criteria

1. An operator can follow the guide from Ch1/Ch6 through stages `01`, `05`, `13`, `20` and the readout notebook.
2. The readout prints all six sections against the downloaded ETF bundle.
3. The numbered ETF pipeline and release registry remain as shipped (no stage 21, no baseline mutation).
4. The "does not establish" section is present and unambiguous.

## Non-goals and second spec

After this calibration lands, a **separate design** may cover:

- Writable experiments against FX / ETF CFD-relevant symbols on `F:\Market_Data`.
- Retail cost stress and signal semantics portable to MT5 later.
- Still under ML4T gates (setup, walk-forward, run log, sealed holdout)—not a fork of the book's methodology.

That work must not start until this overlay is approved and implemented.

## Implementation notes (for the plan, not this design)

- **Canonical selection:** `resolve_solvent_carrier("etfs")` (wraps `resolve_canonical_rank1_lineage` + solvency). Do not reimplement stage-20 ranking in the overlay. Call it with **no** `admitted`/`labels` overrides (matches cost/holdout stage usage; do not replicate stage 20's local `ADMITTED` field).
- **Write-surface disclosure:** the overlay is read-only, but the *book's own stages* the guide opens are not: stages `01`/`05` write gitignored `eligibility.csv`, `labels/`, `features/`, `evaluation/`; stage `20` may register derived `cohort_metrics`/`backtest_paired_metrics` rows additively into `registry.db` when missing/stale. The guide must disclose this and offer `scripts/create_experiment.py` (or read-only opening) to keep the bundle pristine.
- **IC vs Sharpe (section 3):** Compare signal-stage IC leader (`BacktestExplorer.best(..., top_n=0)` sorted by `ic_mean_daily`) to the Sharpe-selected carrier family/metrics — same teaching point as Ch20, read-only.
- **Cost survival (section 4):** Read `backtest_runs.stage = 'cost_sensitivity'` rows for the carrier’s `prediction_hash` (`case_studies/RUN_LOG.md`).
- **Holdout (section 5):** Use lineage fields on the carrier (`holdout_backtest_hash`, `holdout_sharpe`); if null, say missing (do not retrain).
- **`sys.path`:** Any import of `case_studies.*` must run after inserting the repository root on `sys.path` (Jupyter cwd may be `docs/operator`).
- Keep the guide short; teaching prose lives in the readout notebook where numbers appear.
- Create `docs/operator/` if missing; do not invent a second docs tree.
- **Execution status:** Approved design + plan; code/commits are **FUTURE WORK** until the operator dispatches implementation (Outlook `ETF-cal implement`).

## Open items

None for this scope.
