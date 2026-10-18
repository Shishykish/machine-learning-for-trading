# ETF Calibration Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **FUTURE WORK:** Design and plan are approved; **do not commit or implement** until the operator dispatches execution (Outlook tasks `ETF-cal implement` / `run` / `record`). When dispatching, complete Task 0 (git) first.

**Goal:** Ship an operator guide plus a read-only ETF registry readout (Jupytext notebook) that teaches the ML4T find → evaluate → validate path without mutating the book’s numbered pipeline.

**Architecture:** Thin helper under `docs/operator/` with lazy repo imports (a lib-level `resolve_carrier` seam ensures the repo root is on `sys.path` before importing `case_studies.*`, then calls the book's `resolve_solvent_carrier`), reads IC / cost / holdout via read-only sqlite, and formats six fixed sections. Guide sequences Ch1/Ch6 and ETF stages `01`/`05`/`13`/`20`.

**Tech Stack:** Python 3 (`uv`), pytest, Jupytext percent, sqlite read-only URI (`file:...?mode=ro`), `case_studies.utils.strategy_analysis.resolve_solvent_carrier`, `case_studies.utils.backtest_explorer.BacktestExplorer`.

## Critical review log

**Round 1 (2026-10-18, applied)**: TDD order, importlib-only tests, `resolve_solvent_carrier` as canonical API, `stage='cost_sensitivity'`, sys.path requirement, IC-leader comparison, guide markdown structure, `.py` links, Wave B split, FUTURE WORK banner, PowerShell commit alternative.

**Round 2 (2026-10-18, applied)**:

| Defect | Fix |
|--------|-----|
| Top-level `from case_studies... import` in the lib breaks direct execution (`python docs/operator/etf_calibration.py` puts `docs/operator` on `sys.path`, not repo root) | Lib-level seam `resolve_carrier(repo_root, case_study)` does `ensure_repo_on_path` **then** imports; all sqlite work inside private helpers; tests patch lib seams so mocked runs never touch sqlite |
| Test patched `lib.resolve_solvent_carrier` (repo symbol) instead of a lib seam | Tests patch `lib.resolve_carrier` and the private helpers; `build_readout` calls only seams |
| Typo `FileNotError` | `FileNotFoundError` |
| Wave B hazard: guide (Wave A) links `etf_calibration.py`, so a parallel Task 4 link test fails if it runs before Task 3 creates the notebook | **Task 4 merged into Task 3** (link test added after the notebook exists, same RED→GREEN cycle); old Task 5 renumbered Task 4 |
| `@pytest.mark.integration` is not a registered marker (`pyproject.toml` registers only `production_extract`) | Integration test uses `@pytest.mark.production_extract` (the repo's own convention for "runs locally against real data") **and** skipif registry missing |
| `test_format_readout_has_six_section_headers` inline-by-reference ("copy from prior plan") | Full test code inlined; `format_readout` must use `.get()` with `None` defaults so a minimal dict formats |
| `repo_root_from_here` could walk past drive root | Raises `FileNotFoundError` when no ancestor contains `case_studies/etfs` |
| IC-leader path could crash the readout (coverage-bar refusal, empty frame) | `_ic_leader_row` returns `(None, None, None)` on empty result and catches the explorer's coverage refusal; format prints "IC leader: unavailable from published rows" |

**Round 3 (2026-10-18, applied — verified against source)**:

| Defect | Fix |
|--------|-----|
| Polars `sort(descending=True)` puts **nulls first** by default, so sorting `best()` output by `ic_mean_daily` descending can crown a null-IC row as "IC leader" | `_ic_leader_row` must sort with `nulls_last=True` |
| Catch clause was vague ("catch the exception it raises"); the coverage refusal is a plain **`RuntimeError`** (verified in `backtest_explorer.py:359`) | Pin `except RuntimeError: return (None, None, None)` around the `best()` call only |
| Notebook's lib loader used `Path(__file__)`, which is **undefined when the paired `.ipynb` runs in Jupyter** (only the `.py` executed as a script has it) | `try: Path(__file__)... except NameError: Path.cwd() / "docs" / "operator"` — repo README starts Jupyter from the repo root, so the fallback is correct |
| Guide (Wave A) could markdown-link readout files that Task 3 (Wave B) has not created yet | Task 2 rule: refer to `etf_calibration.py` / `.ipynb` as **code spans, never links**; only chapter/stage files are links |
| Undisclosed write surface: the guide tells the operator to open/run stages `01`, `05`, `20` — stage 01/05 write gitignored `eligibility.csv`, `labels/`, `features/`, `evaluation/`; **stage 20 can register derived `cohort_metrics`/`backtest_paired_metrics` rows additively into `registry.db` when missing/stale** (`compute_and_register` / `populate_paired_metrics`) | Guide gains an explicit "What running a stage writes" note; keep-the-bundle-pristine guidance (open read-only, or copy via `scripts/create_experiment.py`); overlay's own read-only guarantee restated as covering only the readout |
| `resolve_carrier` could be "improved" by replicating stage 20's local `ADMITTED` set — that would re-rank differently from the canonical contract | Rule: call the canonical resolver with **no** `admitted`/`labels` overrides, exactly as the cost/holdout stages do |
| Notebook-pair guards untested against the new pair (repo has `test_notebook_sync`, `test_notebook_pair_metadata_filter`, provenance-digest tests) | Task 3 verification step runs those guard tests after `jupytext --sync` |

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-18-etf-calibration-overlay-design.md` (approved).
- Overlay read-only guarantee (lib, notebook, tests): never create/modify under `case_studies/etfs/run_log/`, and the notebook performs no sys.path mutation or repo imports itself.
- The **book's own stages** the guide opens are outside that guarantee and documented as such: stage 01/05 write gitignored `eligibility.csv`, `labels/`, `features/`, `evaluation/`; stage 20 may register derived rows into `registry.db` additively (book-documented behavior). The guide discloses this and points to `scripts/create_experiment.py` for a pristine bundle.
- Do not edit `case_studies/etfs/01`–`20`.
- Overlay only under `docs/operator/` (not stage 21).
- Teaching only — not deployable alpha; no MT5 / operator-universe / live.
- TDD: failing test → run fail → minimal code → run pass.
- No `case_studies`/`utils` import at lib module top level; all repo imports happen after `ensure_repo_on_path`, inside seams.
- `resolve_carrier` calls the canonical resolver with **no** `admitted`/`labels` overrides (matches cost/holdout stage usage; do not replicate stage 20's local `ADMITTED` field).
- Tests must not require the downloaded registry; the only registry-dependent test is `production_extract` + skipif.
- Commits: **only when implementation is dispatched** (FUTURE WORK until then).

## File structure

| Path | Responsibility |
|------|----------------|
| `docs/operator/etf_calibration_lib.py` | Path helpers, `resolve_carrier` seam, `build_readout`, `format_readout` |
| `docs/operator/etf_calibration.py` | Jupytext source calling the lib (also executable headless) |
| `docs/operator/etf_calibration.ipynb` | `jupytext --sync` |
| `docs/operator/etf-calibration.md` | Reading map + continue-only-if |
| `tests/test_etf_calibration_overlay.py` | Unit tests (hermetic) + one `production_extract` test |

## Parallel dispatch map

| Wave | Tasks | Parallel? |
|------|-------|-----------|
| 0 | Task 0 git/worktree | Serial |
| A | Task 1 (lib), Task 2 (guide) | **Yes** (no shared files) |
| B | Task 3 (notebook pair **including** guide-link test) | Single task |
| C | Task 4 verification | Serial |

Do not parallelize anything else with Task 1 (every later task imports its seams).

---

### Task 0: Git root and worktree

**Files:** none (environment)

- [ ] **Step 1: Detect git**

```powershell
Set-Location "F:\Knowledge-Base\03-Development\Active-Projects\trading\machine-learning-for-trading-main\machine-learning-for-trading-main"
Test-Path .git
```

Expected: `False` on the current zip tree (as of 2026-10-18).

- [ ] **Step 2: Establish git (required before any commit)**

Preferred: clone upstream to the F: drive, copy `docs/superpowers/` from the zip tree into the clone, then feature branch or `.worktrees/` per `using-git-worktrees` (verify `.worktrees` is gitignored).

```powershell
git clone https://github.com/stefan-jansen/machine-learning-for-trading.git `
  F:\Knowledge-Base\03-Development\Active-Projects\trading\machine-learning-for-trading-git
```

- [ ] **Step 3: Baseline**

```powershell
uv sync
uv run pytest tests/test_workspace_prerequisites.py -q
```

Expected: exit 0 (or document pre-existing failures before proceeding).

- [ ] **Step 4: Report** working repo root path used by all later tasks.

---

### Task 1: Readout library (TDD)

**Files:**
- Create: `docs/operator/etf_calibration_lib.py`
- Test: `tests/test_etf_calibration_overlay.py`

**Interfaces produced (exact):**

```python
DOWNLOAD_HINT: str  # "uv run python scripts/download_artifacts.py --cs etfs"

def ensure_repo_on_path(repo_root: Path) -> None          # sys.path guard, idempotent
def repo_root_from_here(start: Path | None = None) -> Path  # FileNotFoundError if no ancestor holds case_studies/etfs
def etf_registry_path(repo_root: Path) -> Path
def require_etf_registry(repo_root: Path) -> Path         # FileNotFoundError, message contains DOWNLOAD_HINT
def resolve_carrier(repo_root: Path, case_study: str) -> dict  # SEAM: ensures path, imports case_studies, calls resolve_solvent_carrier
def does_not_establish_bullets() -> list[str]
def _prediction_ic(registry_db: Path, prediction_hash: str) -> tuple[float, float, float] | None
def _ic_leader_row(repo_root: Path, case_study: str) -> tuple[str | None, float | None, float | None]
def _cost_sensitivity_note(registry_db: Path, prediction_hash: str) -> str
def _holdout_note(carrier: dict) -> str
def build_readout(repo_root: Path, *, case_study: str = "etfs") -> dict[str, Any]  # calls only the seams above
def format_readout(readout: dict[str, Any]) -> str  # .get() with None defaults everywhere
```

Rules: no top-level `case_studies`/`utils` imports in the lib; every sqlite connection uses `sqlite3.connect(f"file:{path}?mode=ro", uri=True)`; `resolve_solvent_carrier` failures (insolvent rank-1, stale calibration) propagate uncaught — the readout refuses rather than fabricating metrics.

**Test helper (used by every test — no `docs` package import):**

```python
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

def _load_lib():
    path = REPO_ROOT / "docs" / "operator" / "etf_calibration_lib.py"
    spec = importlib.util.spec_from_file_location("etf_calibration_lib", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod
```

- [ ] **Step 1: Write failing tests (batch 1 — hermetic, no `build_readout`)**

```python
def test_require_etf_registry_missing(tmp_path: Path) -> None:
    lib = _load_lib()
    with pytest.raises(FileNotFoundError) as ei:
        lib.require_etf_registry(tmp_path)
    assert lib.DOWNLOAD_HINT in str(ei.value)


def test_require_etf_registry_present(tmp_path: Path) -> None:
    lib = _load_lib()
    db = tmp_path / "case_studies" / "etfs" / "run_log" / "registry.db"
    db.parent.mkdir(parents=True)
    db.write_bytes(b"sqlite")
    assert lib.require_etf_registry(tmp_path) == db


def test_repo_root_from_here_raises_off_repo(tmp_path: Path) -> None:
    lib = _load_lib()
    with pytest.raises(FileNotFoundError):
        lib.repo_root_from_here(tmp_path)


def test_does_not_establish_bullets_locked() -> None:
    lib = _load_lib()
    bullets = lib.does_not_establish_bullets()
    assert any("MT5" in b for b in bullets)
    assert any("what-this-is.md" in b for b in bullets)
    assert any("unbiased alpha" in b for b in bullets)


def test_format_readout_has_six_section_headers() -> None:
    lib = _load_lib()
    text = lib.format_readout(
        {
            "registry_path": "/tmp/registry.db",
            "artifact_note": "present",
            "family": "gbm",
            "config_name": "demo",
            "label": "fwd_ret_21d",
            "val_backtest_hash": "abc",
            "val_prediction_hash": "def",
            "does_not_establish": ["x"],
        }
    )
    for header in (
        "1. Bundle present",
        "2. Selected configuration",
        "3. IC vs traded Sharpe",
        "4. Cost survival",
        "5. Sealed holdout",
        "6. Does not establish",
    ):
        assert header in text
```

Note the format-test dict deliberately omits every optional key — `format_readout` must tolerate that.

- [ ] **Step 2: Run batch 1 — expect FAIL**

```powershell
uv run pytest tests/test_etf_calibration_overlay.py -v
```

- [ ] **Step 3: Implement minimal lib** — `ensure_repo_on_path`, `repo_root_from_here`, `etf_registry_path`, `require_etf_registry`, `does_not_establish_bullets`, `format_readout`. Missing optional keys format as `"not available from published rows"`.

- [ ] **Step 4: Run batch 1 — expect PASS**

- [ ] **Step 5: Write failing test for `build_readout` (batch 2)**

```python
def test_build_readout_uses_carrier_seam(monkeypatch, tmp_path: Path) -> None:
    lib = _load_lib()
    db = tmp_path / "case_studies" / "etfs" / "run_log" / "registry.db"
    db.parent.mkdir(parents=True)
    db.write_bytes(b"\x00")  # guard passes; no real sqlite is opened (helpers mocked)

    fake = {
        "val_backtest_hash": "bh",
        "val_prediction_hash": "ph",
        "val_stage": "signal",
        "val_sharpe": 0.4,
        "family": "linear",
        "config_name": "ridge",
        "label": "fwd_ret_21d",
        "holdout_backtest_hash": None,
        "holdout_sharpe": None,
        "spec_json": "{}",
    }
    monkeypatch.setattr(lib, "resolve_carrier", lambda root, cs: fake)
    monkeypatch.setattr(lib, "_prediction_ic", lambda dbp, ph: (0.01, -0.01, 0.02))
    monkeypatch.setattr(lib, "_ic_leader_row", lambda root, cs: ("gbm", 0.03, 0.1))
    monkeypatch.setattr(
        lib, "_cost_sensitivity_note", lambda dbp, ph: "cost grid: 3 levels, sharpe 0.2-0.5"
    )

    out = lib.build_readout(tmp_path, case_study="etfs")
    assert out["family"] == "linear"
    assert out["ic_leader_family"] == "gbm"
    assert out["holdout_note"]  # derived from carrier, not a seam
    assert out["does_not_establish"] == lib.does_not_establish_bullets()
```

- [ ] **Step 6: Run batch 2 — expect FAIL**

- [ ] **Step 7: Implement `build_readout` + seams**

`resolve_carrier` (production path):

```python
def resolve_carrier(repo_root: Path, case_study: str) -> dict:
    ensure_repo_on_path(repo_root)
    from case_studies.utils.strategy_analysis import resolve_solvent_carrier

    return resolve_solvent_carrier(case_study)
```

`_prediction_ic` — read-only query on `prediction_metrics` (`ic_mean_daily`, `ic_ci_lo`, `ic_ci_hi`) for the carrier's `val_prediction_hash`; `None` when no row.

`_ic_leader_row` — `ensure_repo_on_path`; `from case_studies.utils.backtest_explorer import BacktestExplorer`; inside a `try/except RuntimeError` (the coverage refusal at `backtest_explorer.py:359` is a plain `RuntimeError`): `frame = BacktestExplorer(case_study).best(stage="signal", top_n=0)`; empty frame or exception → `(None, None, None)`; else sort with **`frame.sort("ic_mean_daily", descending=True, nulls_last=True)`** (polars puts nulls first on descending sorts by default — `nulls_last=True` is what stops a null-IC row being crowned leader) and take the first row → `(family, ic_mean_daily, sharpe)`.

`_cost_sensitivity_note` — read-only query (n = count, min/max sharpe):

```sql
SELECT bm.sharpe
FROM backtest_runs b
JOIN backtest_metrics bm ON bm.backtest_hash = b.backtest_hash
WHERE b.stage = 'cost_sensitivity' AND b.prediction_hash = ?
ORDER BY bm.sharpe ASC;
```

No rows → `"no cost-stage rows found for this prediction_hash"`.

`_holdout_note` — from carrier lineage fields (`holdout_backtest_hash`, `holdout_sharpe`); absent → `"holdout rows missing"`.

Section-2 allocation/signal settings: parse `carrier["spec_json"]` with `json.loads` and print the signal method / top_k if present (minimal; reuse `strategy_view` only if already imported where you copy from — do not add new dependencies).

- [ ] **Step 8: Run full file — expect PASS**

```powershell
uv run pytest tests/test_etf_calibration_overlay.py -v
```

- [ ] **Step 9: Commit (on dispatch only)**

Git Bash or PowerShell:

```bash
git add docs/operator/etf_calibration_lib.py tests/test_etf_calibration_overlay.py
git commit -m "feat: add ETF calibration readout library"
```

---

### Task 2: Operator guide

**Files:** Create `docs/operator/etf-calibration.md`

- [ ] **Step 1: Write guide** (content requirements — write the file directly, do not embed it as a nested markdown sample)

Include:

- Banner: teaching only; second spec for `F:\Market_Data` later.
- Prerequisites: `uv run python scripts/download_artifacts.py --cs etfs` (free-data download optional, only for stages you open).
- Continue only if `case_studies/etfs/run_log/registry.db` exists.
- **"What running a stage writes" note**: stage 01/05 write gitignored `eligibility.csv`, `labels/`, `features/`, `evaluation/` under the case-study dir; stage 20 may **register derived rows into `registry.db` additively** (`cohort_metrics`, `backtest_paired_metrics` — the book's own documented behavior when rows are missing/stale) plus `results/strategy_assessment.json` and the tearsheet output. To keep the downloaded bundle byte-identical, open the stage notebooks read-only or copy the case study via `scripts/create_experiment.py` before executing. The **readout notebook** (`docs/operator/etf_calibration`) never writes anywhere under `run_log/`.
- Reading order with links (relative from `docs/operator/`): `../../01_process_is_edge/README.md`, `../../06_strategy_definition/README.md`, `../../case_studies/etfs/README.md`, then `../../case_studies/etfs/01_feasibility_analysis.py`, `05_evaluation.py`, `13_model_analysis.py`, `20_strategy_analysis.py`.
- Run readout: `uv run python docs/operator/etf_calibration.py` from repo root (also open the `.ipynb` after Task 3's sync). **Refer to `etf_calibration.py` / `etf_calibration.ipynb` only as code spans (backticks), never markdown links** — they do not exist until Wave B, and the guide ships in Wave A.
- Continue-only-if table (per spec).
- Closing: `docs/what-this-is.md`, evidence boundary, operator-universe remainder is a separate spec.

- [ ] **Step 2: Spot-check paths**

```powershell
$root = (Get-Location).Path
@(
  "01_process_is_edge/README.md",
  "06_strategy_definition/README.md",
  "case_studies/etfs/README.md",
  "case_studies/etfs/01_feasibility_analysis.py",
  "case_studies/etfs/05_evaluation.py",
  "case_studies/etfs/13_model_analysis.py",
  "case_studies/etfs/20_strategy_analysis.py"
) | ForEach-Object { if (-not (Test-Path (Join-Path $root $_))) { throw "missing $_" } }
Write-Output "guide targets OK"
```

- [ ] **Step 3: Commit on dispatch** — `git commit -m "docs: add ETF calibration operator guide"`

---

### Task 3: Notebook pair + guide-link test

**Files:**
- Create: `docs/operator/etf_calibration.py`, then `.ipynb` via sync
- Modify: `tests/test_etf_calibration_overlay.py`

- [ ] **Step 1: Write both failing tests**

```python
def test_notebook_source_calls_lib() -> None:
    src = (REPO_ROOT / "docs" / "operator" / "etf_calibration.py").read_text(encoding="utf-8")
    assert "require_etf_registry" in src
    assert "build_readout" in src
    assert "format_readout" in src
    assert "run_log" in src  # read-only prose


def test_guide_relative_targets_exist() -> None:
    import re

    guide = (REPO_ROOT / "docs" / "operator" / "etf-calibration.md").read_text(encoding="utf-8")
    rels = re.findall(r"\]\(([^)#]+?)(?:#[^)]*)?\)", guide)
    assert rels, "guide has no markdown links"
    base = REPO_ROOT / "docs" / "operator"
    for rel in rels:
        if rel.startswith("http"):
            continue
        target = (base / rel).resolve()
        assert target.exists(), f"broken link: {rel} -> {target}"
```

- [ ] **Step 2: Run — expect FAIL** (`etf_calibration.py` does not exist yet)

- [ ] **Step 3: Create `etf_calibration.py`** — percent header matching case-study notebooks (`cell_metadata_filter: tags,-all`); markdown cell stating read-only/no-`run_log`-writes intent; one code cell:

```python
try:
    here = Path(__file__).resolve().parent        # .py executed as a script
except NameError:
    here = Path.cwd() / "docs" / "operator"       # paired .ipynb in Jupyter (repo README runs Jupyter from repo root)
```

then load the sibling lib, `ROOT = lib.repo_root_from_here()`, print `lib.format_readout(lib.build_readout(ROOT))`.

- [ ] **Step 4: Sync, guard tests, and run**

```powershell
uv run python -m jupytext --sync docs/operator/etf_calibration.py
uv run pytest tests/test_etf_calibration_overlay.py -v
uv run pytest tests/test_notebook_sync.py tests/test_notebook_pair_metadata_filter.py -q
```

Expected: `.ipynb` created; overlay tests PASS (link test now resolves every chapter/stage link); the repo's own notebook-pair guards do not trip on the new pair. If a guard fails (metadata filter, empty-cell, provenance), fix the notebook to satisfy it — that is the repo's convention, not ours to waive.

- [ ] **Step 5: Commit on dispatch**

```bash
git add docs/operator/etf_calibration.py docs/operator/etf_calibration.ipynb tests/test_etf_calibration_overlay.py
git commit -m "feat: add ETF calibration readout notebook and guide-link guard"
```

---

### Task 4: Verification gate

- [ ] **Step 1: Automated suite**

```powershell
uv run pytest tests/test_etf_calibration_overlay.py -v
```

Paste output into the Outlook `build` Status trail when completing the implement task.

- [ ] **Step 2: Production-data test (registered marker + skipif)**

```python
@pytest.mark.production_extract
def test_build_readout_against_published_registry() -> None:
    lib = _load_lib()
    reg = REPO_ROOT / "case_studies" / "etfs" / "run_log" / "registry.db"
    if not reg.is_file() or reg.stat().st_size == 0:
        pytest.skip("ETF artifact bundle not installed")
    out = lib.build_readout(REPO_ROOT)
    assert out["val_backtest_hash"]
    assert "6. Does not establish" in lib.format_readout(out)
```

(`production_extract` is the repo's registered marker for "runs locally against the real data"; add the run line `uv run pytest tests/test_etf_calibration_overlay.py -v -m production_extract` after `download_artifacts --cs etfs`.)

- [ ] **Step 3: Headless smoke**

```powershell
uv run python scripts/download_artifacts.py --cs etfs
uv run python docs/operator/etf_calibration.py
```

Expected: six section headers; no exception; failures from `resolve_solvent_carrier` (insolvent rank-1, stale calibration) propagate as honest refusals.

- [ ] **Step 4: Confirm no `run_log` writes** — snapshot `Get-ChildItem case_studies/etfs/run_log -Recurse` mtimes before/after Step 3; identical.

- [ ] **Step 5: Manual guide walk** — operator follows `etf-calibration.md` (Outlook `run` stage).

- [ ] **Step 6: Record closeout** — Outlook `record`; state operator-universe second spec still deferred.

---

## Spec coverage

| Requirement | Task |
|-------------|------|
| Guide | 2 |
| Readout pair | 3 |
| Six sections + IC vs Sharpe teaching | 1, 3 |
| Missing-registry hint | 1 |
| No pipeline mutation / read-only | Global, Task 1 rules, Task 4 Step 4 |
| Link verification | 3 |
| Registry-present integration | 4 (`production_extract`) |
| Git / FUTURE WORK | 0, banner |

## Remaining known risks (accepted)

- `BacktestExplorer.best()` applies full-coverage and active-model filters; if the published etfs registry triggers its coverage refusal, `_ic_leader_row` degrades to "unavailable" rather than crashing — acceptable for a teaching readout.
- `resolve_solvent_carrier` refusals are deliberate hard stops (book's solvency/calibration gates); the readout surfaces them, never works around them.
- This tree is not a git repo; Task 0 must run before any commit.
- The paired `.ipynb`'s `Path.cwd()` fallback assumes Jupyter starts from the repo root (the repo's documented convention); started elsewhere, `repo_root_from_here` fails loudly with `FileNotFoundError` rather than mis-reading — acceptable.

---

## Execution handoff

Plan path: `docs/superpowers/plans/2026-10-18-etf-calibration-overlay.md`

**When dispatching:**

1. **Subagent-Driven (recommended)** — Wave A: two subagents (Task 1 + Task 2) in parallel; Wave B: Task 3; Task 4 inline with fresh verification evidence.
2. **Inline** — `executing-plans` with checkpoints after each wave.

Implementation remains **FUTURE WORK** until you dispatch.