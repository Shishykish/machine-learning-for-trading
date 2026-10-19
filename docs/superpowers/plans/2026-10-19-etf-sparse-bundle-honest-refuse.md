# ETF Sparse Bundle Honest Refuse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unblock FK Task 2 / overlay Task 4 by making `build_readout` **honestly refuse** the published ETF artifact install when the slim backtest tree cannot support `resolve_solvent_carrier`, without bypassing solvency and without changing the book's ranker.

**Architecture:** Root cause (verified 2026-10-19): `etfs.tar.gz` install is a **complete intentional slim pack**, not a broken extract. `.release/artifact_coverage.tsv` records `backtest selected=21 copied=21 missing=0`; `accepted_registry.tsv` records `backtest_runs=2308`; `registry.db` SHA-256 matches the TSV. `resolve_solvent_carrier` → common-support re-rank needs **1882** candidate return files; **14** of those hashes are on disk; first miss is `ee588560602d` (`FileNotFoundError`). Overlay wraps that failure with an operator-facing message that cites the coverage TSV and forbids fabricating a carrier. `production_extract` asserts the refuse path on today's bundle (and keeps a success branch if a future dense bundle appears). Book code under `case_studies/utils/strategy_analysis.py` is untouched.

**Tech Stack:** Python 3, pytest, existing `docs/operator/etf_calibration_lib.py`, overlay tests.

## Global Constraints

- Do **not** bypass `resolve_solvent_carrier` / solvency checks.
- Do **not** edit `case_studies/etfs/01`–`20`.
- Do **not** change `rank_backtests_on_common_support` to skip missing artifacts (book change — out of scope unless the operator explicitly widens).
- Do **not** fake carriers, pins, or synthetic returns.
- Do **not** write under `case_studies/etfs/run_log/` from readout / tests.
- Do **not** commit `.cache/` or installed `run_log`.
- Teaching-only overlay; no MT5 / operator-universe / `F:\Market_Data`.
- TDD on every production change: failing test → run fail → minimal code → run pass.
- Commits on `feat/etf-calibration-overlay` in `F:\Knowledge-Base\03-Development\Active-Projects\trading\machine-learning-for-trading-git`.
- Use lib venv: `.worktrees/etf-cal-lib\.venv\Scripts\python.exe`. Set `ML4T_RESULTS_FILE=F:\temp\pytest\ml4t-test-results.jsonl` and `PYTHONUTF8=1` for pytest.

## Evidence (do not re-diagnose)

```text
GitHub v3.1.0-artifacts asset etfs.tar.gz digest sha256:46693e83… == ARTIFACT_SHA256["etfs"]
installer deletes .cache/etfs.tar.gz after a checksum-matching install (download_case_study finally)
registry.db sha256 == accepted_registry.tsv sha256 (8c252bff…)  → True
artifact_coverage.tsv backtest: selected=21 copied=21 missing=0
SHA256SUMS daily_returns.parquet lines: 21 present, 0 missing
disk backtest/*/daily_returns.parquet trees: 21 (stages: 5 signal, 5 allocation, 5 risk_overlay, 5 cost_sensitivity, 1 holdout)
backtest_runs rows: 2308
common-support candidates for etfs: 1882 (conformal field; re-rank required)
of those on disk: 14
SELECTION.json notebook_rank1: 18c7a8419306 (on disk); helper_rank1 unresolved (packager missing setup.yaml path)
FileNotFoundError first miss, in candidate order: …/backtest/ee588560602d/daily_returns.parquet
immutable=1 reads created no registry.db-wal / -shm
```

Upstream note (for ledger / Outlook, not a code task): the published `v3.1.0-artifacts` etfs bundle ships a dense registry with a curated return subset; solvent carrier resolution on ETF therefore cannot succeed until upstream ships return trees for the conformal candidate set (or pins a carrier that does not require common-support re-rank). Escalate; do not patch the book ranker here.

## File structure

| Path | Responsibility |
|------|----------------|
| `docs/operator/etf_calibration_lib.py` | Detect / wrap sparse-bundle `FileNotFoundError` from `resolve_solvent_carrier` into a clear refuse |
| `tests/test_etf_calibration_overlay.py` | Hermetic wrap test + `production_extract` refuse/success branches |
| `docs/operator/etf-calibration.md` | One short note that published etfs may refuse solvent readout when slim |
| `.superpowers/sdd/progress.md` | FK Task 2 / overlay Task 4 evidence |

## Parallel dispatch map

| Wave | Tasks | Parallel? |
|------|-------|-----------|
| A | Task 1 overlay refuse message (TDD) | Serial |
| B | Task 2 production_extract + guide note | Serial (needs Task 1) |
| C | Task 3 FK verification (pytest, smoke, mtime) | Serial (needs Task 2) |
| D | Task 4 ledger + finish-branch options + Outlook implement evidence | Serial (needs Task 3) |

---

### Task 1: Honest refuse wrapper in overlay lib

**Files:**
- Modify: `docs/operator/etf_calibration_lib.py`
- Modify: `tests/test_etf_calibration_overlay.py`

**Interfaces:**
- Consumes: existing `resolve_carrier` → `resolve_solvent_carrier`; `FileNotFoundError` from `rank_backtests_on_common_support`
- Produces: `SparseArtifactBundleError(RuntimeError)` (or reuse `RuntimeError` with a stable message substring) raised from `resolve_carrier` / `build_readout` when the solvent path hits a missing registered return artifact
- Message must include: `Missing registered return artifact` (or the original path), `artifact_coverage.tsv`, and that the overlay will not fabricate a carrier

- [ ] **Step 1: Write the failing hermetic test**

Add to `tests/test_etf_calibration_overlay.py`:

Patch `resolve_solvent_carrier` on the book module, not `lib.resolve_carrier`. The wrap lives inside `resolve_carrier`; replacing that function would hide the behavior under test.

```python
def test_build_readout_refuses_missing_return_artifact(monkeypatch, tmp_path: Path) -> None:
    lib = _load_lib()
    reg = tmp_path / "case_studies" / "etfs" / "run_log" / "registry.db"
    reg.parent.mkdir(parents=True)
    reg.write_bytes(b"sqlite")  # presence only; carrier is patched
    lib.ensure_repo_on_path(REPO_ROOT)
    import case_studies.utils.strategy_analysis as strategy_analysis

    def _missing(*_a, **_k):
        raise FileNotFoundError(
            "Missing registered return artifact: "
            f"{tmp_path}/case_studies/etfs/run_log/backtest/ee588560602d/daily_returns.parquet"
        )

    monkeypatch.setattr(strategy_analysis, "resolve_solvent_carrier", _missing)
    with pytest.raises(Exception) as caught:
        lib.build_readout(tmp_path, case_study="etfs")
    assert type(caught.value).__name__ == "SparseArtifactBundleError"
    message = str(caught.value)
    assert "artifact_coverage" in message
    assert "fabricate" in message
    assert "Missing registered return artifact" in message
```

Assert the type by name so the red run fails on `FileNotFoundError` instead of erroring on a missing attribute. One public type: `SparseArtifactBundleError`.

- [ ] **Step 2: Run test — expect FAIL**

```powershell
$env:ML4T_RESULTS_FILE='F:\temp\pytest\ml4t-test-results.jsonl'
$env:PYTHONUTF8='1'
$py = ".\.worktrees\etf-cal-lib\.venv\Scripts\python.exe"
& $py -m pytest tests/test_etf_calibration_overlay.py::test_build_readout_refuses_missing_return_artifact -v --basetemp=F:\temp\pytest
```

Expected: FAIL (exception type / message not wrapped yet, or `SparseArtifactBundleError` undefined).

- [ ] **Step 3: Minimal implementation**

In `docs/operator/etf_calibration_lib.py`:

```python
class SparseArtifactBundleError(RuntimeError):
    """Published run_log is installed but too sparse for solvent carrier resolution."""


def resolve_carrier(repo_root: Path, case_study: str) -> dict:
    """Resolve the canonical solvent carrier for ``case_study``."""
    ensure_repo_on_path(repo_root)
    from case_studies.utils.strategy_analysis import resolve_solvent_carrier

    try:
        return resolve_solvent_carrier(case_study)
    except FileNotFoundError as exc:
        msg = str(exc)
        if "Missing registered return artifact" not in msg:
            raise
        coverage = (
            repo_root
            / "case_studies"
            / case_study
            / "run_log"
            / ".release"
            / "artifact_coverage.tsv"
        )
        raise SparseArtifactBundleError(
            f"{msg}. The published {case_study} artifact bundle ships a curated "
            f"subset of return trees (see {coverage} when present). "
            "This overlay will not fabricate a carrier or bypass solvency; "
            "re-run stages locally or wait for a denser upstream release."
        ) from exc
```

Keep `build_readout` calling `resolve_carrier` unchanged so the wrap applies to headless smoke and the notebook.

- [ ] **Step 4: Run test — expect PASS**

Same pytest command as Step 2. Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add docs/operator/etf_calibration_lib.py tests/test_etf_calibration_overlay.py
git commit -m "fix: refuse ETF readout when published return trees are sparse"
```

---

### Task 2: production_extract asserts refuse on today's slim bundle

**Files:**
- Modify: `tests/test_etf_calibration_overlay.py` (`test_build_readout_against_published_registry`)
- Modify: `docs/operator/etf-calibration.md` (one short prerequisite / stop note)

**Interfaces:**
- Consumes: Task 1 `SparseArtifactBundleError`; installed `case_studies/etfs/run_log/.release/artifact_coverage.tsv`
- Produces: `production_extract` green when the installed bundle matches today's slim contract (refuse) **or** a future dense bundle (success)

- [ ] **Step 1: Write the failing production_extract update (RED if still expecting success only)**

Replace the body of `test_build_readout_against_published_registry` with:

```python
@pytest.mark.production_extract
def test_build_readout_against_published_registry() -> None:
    lib = _load_lib()
    run_log = REPO_ROOT / "case_studies" / "etfs" / "run_log"
    reg = run_log / "registry.db"
    if not reg.is_file() or reg.stat().st_size == 0:
        pytest.skip("ETF artifact bundle not installed")

    coverage = run_log / ".release" / "artifact_coverage.tsv"
    disk_trees = (
        len(list((run_log / "backtest").glob("*/daily_returns.parquet")))
        if (run_log / "backtest").is_dir()
        else 0
    )
    # Today's published etfs pack: dense registry, curated 21 return trees.
    slim = coverage.is_file() and disk_trees < 100

    if slim:
        with pytest.raises(lib.SparseArtifactBundleError, match="Missing registered return artifact"):
            lib.build_readout(REPO_ROOT)
        return

    out = lib.build_readout(REPO_ROOT)
    assert out["val_backtest_hash"]
    assert "6. Does not establish" in lib.format_readout(out)
```

- [ ] **Step 2: Run production_extract — expect PASS after Task 1**

```powershell
$env:ML4T_RESULTS_FILE='F:\temp\pytest\ml4t-test-results.jsonl'
$env:PYTHONUTF8='1'
$py = ".\.worktrees\etf-cal-lib\.venv\Scripts\python.exe"
& $py -m pytest tests/test_etf_calibration_overlay.py -v --basetemp=F:\temp\pytest
& $py -m pytest tests/test_etf_calibration_overlay.py -v -m production_extract --basetemp=F:\temp\pytest
```

Expected: full file green (count = prior hermetic tests + refuse hermetic + production_extract). Paste summary into the SDD ledger.

- [ ] **Step 3: Guide note (minimal)**

In `docs/operator/etf-calibration.md`, near the artifact download prerequisite, add one short paragraph:

```markdown
The published `etfs` artifact bundle may install a **full registry** with only a
**curated subset** of `run_log/backtest/*/daily_returns.parquet` trees (see
`run_log/.release/artifact_coverage.tsv`). The calibration readout calls
`resolve_solvent_carrier` and will **refuse** rather than invent a carrier when
common-support ranking needs return files the release did not ship.
```

- [ ] **Step 4: Commit**

```powershell
git add tests/test_etf_calibration_overlay.py docs/operator/etf-calibration.md
git commit -m "test: assert sparse ETF bundle refuses solvent readout"
```

---

### Task 3: FK Task 2 verification remainder (smoke + mtime)

**Files:** none created (verification only). Snapshot already at `F:\temp\etf-run-log-before.csv`.

**Interfaces:**
- Consumes: Task 1–2 code; installed etfs `run_log`

- [ ] **Step 1: Headless smoke — expect honest refuse**

```powershell
$py = ".\.worktrees\etf-cal-lib\.venv\Scripts\python.exe"
& $py docs/operator/etf_calibration.py
```

Expected: process exits non-zero with `SparseArtifactBundleError` / message citing missing return artifact and `artifact_coverage.tsv`. This is the agreed hard stop — **not** a solvency bypass.

- [ ] **Step 2: After-mtime snapshot + diff**

```powershell
Get-ChildItem case_studies/etfs/run_log -Recurse | Select-Object FullName, LastWriteTime, Length |
  Export-Csv F:\temp\etf-run-log-after.csv -NoTypeInformation
$py = ".\.worktrees\etf-cal-lib\.venv\Scripts\python.exe"
& $py -c @"
import csv
from pathlib import Path
def load(p):
    with open(p, newline='', encoding='utf-8') as f:
        return {(r['FullName'], r['LastWriteTime'], r['Length']) for r in csv.DictReader(f)}
b, a = load(r'F:\temp\etf-run-log-before.csv'), load(r'F:\temp\etf-run-log-after.csv')
print('only_before', len(b-a), 'only_after', len(a-b))
wal = [p for p,_,_ in (a-b)|(b-a) if p.endswith('-wal') or p.endswith('-shm')]
print('wal_shm_delta', wal)
"@
```

Expected: no path/mtime/length deltas attributable to the readout; no new `-wal`/`-shm` from the refuse path. If sidecars appear, record and escalate — do not claim Task 4 green.

- [ ] **Step 3: Re-run overlay pytest once more (fresh evidence)**

Same commands as Task 2 Step 2. Expected: all green. Paste into ledger.

---

### Task 4: Ledger, finish-branch options, Outlook implement evidence

**Files:**
- Modify: `.superpowers/sdd/progress.md`

- [ ] **Step 1: Update SDD ledger**

Mark FK Task 2 complete with: root-cause summary (slim pack), pytest paste, smoke refuse text, mtime diff result, upstream escalation note. Overlay Task 4 = complete via **honest refuse** (not a successful six-section readout against the published slim pack).

- [ ] **Step 2: `finishing-a-development-branch`**

Present the four options (merge locally / PR to fork / keep branch / discard). Do **not** push or merge to upstream `main` without operator choice. Merge-base for review: `16dbb8c`..HEAD.

- [ ] **Step 3: Outlook**

Complete **ETF-cal implement** only, with pytest evidence paste. Leave **run** / **record** open until a real guide walk (operator). Category `machine-learning-for-trading`, campaign `ETF-cal`.

---

## Spec coverage

| Requirement | Task |
|-------------|------|
| Root-cause slim pack vs broken extract | Evidence (this plan header) |
| No solvency bypass / no fake carrier | 1, Global |
| No book ranker change | Global |
| production_extract green under honest refuse | 2 |
| Headless smoke + no run_log writes | 3 |
| Operator closeout / Outlook implement only | 4 |

## Self-review

1. **Spec coverage:** Overlay design allows fail-loud on unusable registry; handoff explicitly allows succeed **or** honest refuse. Covered.
2. **Placeholder scan:** None.
3. **Type consistency:** `SparseArtifactBundleError` used in Task 1–3; if implementer collapses to bare `RuntimeError`, update all three tasks' assertions to match in the same commit.

## Remaining known risks (accepted)

- A future dense etfs release should take the success branch of `production_extract`; the `disk_trees < 100` heuristic is a deliberate ceiling (`ponytail:` upgrade = parse `artifact_coverage.tsv` selected/copied vs `accepted_registry.tsv` backtest_runs).
- Unmerged polish `3084735` remains optional / skipped.
- Windows `test_notebook_sync` CRLF noise remains pre-existing / out of scope.

---

## Execution handoff

Plan path: `docs/superpowers/plans/2026-10-19-etf-sparse-bundle-honest-refuse.md`

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks
2. **Inline Execution** — `executing-plans` in this session with checkpoints after each task

**Which approach?**
