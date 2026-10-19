# ETF calibration (operator guide)

**Teaching only.** This pass walks the published ETF case study so you learn ML4T’s find → evaluate → validate flow and the evidence boundary. A **second spec** will later point the same gates at operator universes on `F:\Market_Data`. This is **not deployable alpha** and not a go-live signal.

## Prerequisites

From the repository root:

```bash
uv run python data/download_all.py --free-only
uv run python scripts/download_artifacts.py --cs etfs
```

The free-data download is **optional**—run it only for stages you actually open. **Continue only if** `case_studies/etfs/run_log/registry.db` exists after the artifact step.

The published `etfs` artifact bundle may install a **full registry** with only a
**curated subset** of `run_log/backtest/*/daily_returns.parquet` trees (see
`run_log/.release/artifact_coverage.tsv`). The calibration readout calls
`resolve_solvent_carrier` and will **refuse** rather than invent a carrier when
common-support ranking needs return files the release did not ship.

## What running a stage writes

The calibration readout is read-only, but the **book stages** you open are not:

- Stages **01** and **05** write gitignored `eligibility.csv`, `labels/`, `features/`, and `evaluation/` under the case-study directory.
- Stage **20** may register derived rows into `registry.db` additively (`cohort_metrics`, `backtest_paired_metrics`) when missing or stale, plus `results/strategy_assessment.json` and the tearsheet output.
- To keep the downloaded bundle byte-identical, open stage notebooks **read-only** or copy the case study first with `scripts/create_experiment.py` before executing cells.
- The readout (`docs/operator/etf_calibration`) **never** writes anywhere under `run_log/`.

## Reading order

Work from the repo root. Open these in order (Jupytext pairs: run or read the `.py` / `.ipynb` as you prefer):

1. [Ch1 — process and evidence boundary](../../01_process_is_edge/README.md)
2. [Ch6 — setup, walk-forward, run log](../../06_strategy_definition/README.md)
3. [ETF case study README (pipeline table)](../../case_studies/etfs/README.md)
4. [01 — feasibility](../../case_studies/etfs/01_feasibility_analysis.py)
5. [05 — evaluation / IC triage](../../case_studies/etfs/05_evaluation.py)
6. [13 — model analysis (registry)](../../case_studies/etfs/13_model_analysis.py)
7. [20 — strategy analysis / assessment](../../case_studies/etfs/20_strategy_analysis.py)

You do not need every numbered ETF stage for this calibration—only the four case-study stages above plus the readout.

## Run the readout

After stage **20** (or with a downloaded bundle that already includes its outputs):

```bash
uv run python docs/operator/etf_calibration.py
```

You can also open `etf_calibration.ipynb` after Task 3’s Jupytext sync if you prefer the notebook UI. Both readout files are read-only registry readouts (Wave B; not required for this guide slice).

## Continue only if

Before moving to the next step, check:

- **Free data** is present if the stage you opened needs it (otherwise download or skip that stage).
- **Artifact bundle** is installed (`registry.db` exists) before stages **13** and **20** and before the readout.
- Stage **20** has produced its assessment outputs (or you are using the pre-built bundle).
- The readout prints **all six sections** below without errors.

## What the readout prints (six sections)

When `etf_calibration.py` / `etf_calibration.ipynb` succeeds, expect this order:

1. **Bundle present** — path to `registry.db`; artifact version note if available.
2. **Selected configuration** — label, model family / preset, allocation and cost settings as recorded (not recomputed).
3. **IC vs traded Sharpe** — rank-IC leaders need not be Sharpe leaders after portfolio construction.
4. **Cost survival** — whether the selected path still looks positive under the ETF cost model in published backtests.
5. **Sealed holdout** — holdout rows if present; otherwise an explicit missing state (no retraining).
6. **Does not establish** — not retail CFDs; not MT5; not your operator universe; not unbiased alpha after search; not a go-live signal. See the evidence boundary in [what this repo is](../what-this-is.md).

## Stop here

Treat this calibration as **evidence with a hard boundary**: it teaches the ML4T workflow on the book’s ETF bundle only. Mapping the same gates to FX / ETF CFD symbols on `F:\Market_Data`, retail cost stress, and future MT5 handoff belongs in a **separate operator-universe spec**—out of scope for this guide.
