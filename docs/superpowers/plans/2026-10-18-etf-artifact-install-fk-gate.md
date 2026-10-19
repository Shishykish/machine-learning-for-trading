# ETF Artifact Install FK Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `scripts/download_artifacts.py` accept the published `etfs` registry (and any bundle whose `.release/accepted_registry.tsv` documents a non-zero foreign-key count), then finish the ETF calibration overlay Task 4 verification gate.

**Architecture:** The installer already requires `PRAGMA integrity_check == ok` and refuses a shipped WAL. Keep that. Change only the foreign-key gate: when `.release/accepted_registry.tsv` records `foreign_keys=N`, require `len(PRAGMA foreign_key_check) == N` instead of forcing `N == 0`. Bundles without that file still require zero FK violations (safe default). Then re-run download, the `production_extract` overlay test, headless readout, and the `run_log` mtime check.

**Tech Stack:** Python 3, sqlite3, pytest, existing `tests/test_download_artifacts.py` helpers, overlay tests in `tests/test_etf_calibration_overlay.py`.

## Global Constraints

- Root cause (verified 2026-10-18): `etfs.tar.gz` SHA-256 matches `ARTIFACT_SHA256["etfs"]`; `PRAGMA integrity_check` is `ok`; `PRAGMA foreign_key_check` returns **3** rows; shipped `.release/accepted_registry.tsv` records `foreign_keys=3`. Current `_verify_run_log` raises if `foreign_keys` is non-empty, so install fails with a misleading "integrity checks" message even when integrity is fine.
- Do not edit `case_studies/etfs/01`–`20`.
- Overlay remains read-only after install: readout must not write under `case_studies/etfs/run_log/`.
- Teaching only — not deployable alpha.
- TDD on the installer change: failing test → run fail → minimal code → run pass.
- Do not weaken checksum or WAL refusal.
- Diagnostic extract left at `case_studies/etfs/etf-diag-*/` must be deleted before claiming Task 4 done (not a shipped path).
- Commits on `feat/etf-calibration-overlay` in `F:\Knowledge-Base\03-Development\Active-Projects\trading\machine-learning-for-trading-git`.

## File structure

| Path | Responsibility |
|------|----------------|
| `scripts/download_artifacts.py` | `_verify_run_log`: honor accepted FK count |
| `tests/test_download_artifacts.py` | Hermetic FK / accepted_registry cases |
| `tests/test_etf_calibration_overlay.py` | Already has `production_extract` test (no change unless assert fails) |
| `docs/operator/*` | Unchanged; used by headless smoke |

## Parallel dispatch map

| Wave | Tasks | Parallel? |
|------|-------|-----------|
| A | Task 1 installer TDD fix | Serial |
| B | Task 2 download + overlay verification | Serial (needs Task 1) |
| C | Task 3 optional nested-spec merge (`3084735`) | After B, optional |
| D | Task 4 finish branch / Outlook evidence | After B |

---

### Task 1: Honor accepted foreign-key count in artifact install

**Files:**
- Modify: `scripts/download_artifacts.py` (`_verify_run_log`)
- Modify: `tests/test_download_artifacts.py`

**Interfaces:**
- Consumes: existing `_build_bundle`, `install_artifact_archive`, `_verify_run_log`
- Produces: `_accepted_foreign_key_count(run_log: Path) -> int | None` (or inline helper) — `None` means "require zero"; `int` means exact expected violation count from TSV

- [ ] **Step 1: Extend `_build_bundle` to optionally ship FK violations + accepted TSV**

Add parameters to the existing helper (keep defaults so old tests unchanged):

```python
def _build_bundle(
    tmp_path: Path,
    *,
    valid_manifest: bool = True,
    wal: bool = False,
    ship_wal: bool = False,
    dangling_fk: bool = False,
    accepted_fk: int | None = None,
) -> Path:
```

When `dangling_fk` is True, create parent/child tables with one orphan child row so `PRAGMA foreign_key_check` returns at least one row. When `accepted_fk` is not None, write `.release/accepted_registry.tsv` with header matching the published file and `foreign_keys` set to that integer:

```text
case_study	source_path	sha256	integrity	foreign_keys	training_runs	prediction_sets	backtest_runs
etfs	/tmp	deadbeef	ok	{accepted_fk}	0	0	0
```

(Use the real registry sha256 in the TSV if easy; the installer must not re-check that column in this task — only `foreign_keys`.)

- [ ] **Step 2: Write failing tests**

```python
def test_bundle_with_documented_fk_count_installs(tmp_path: Path) -> None:
    archive = _build_bundle(tmp_path, dangling_fk=True, accepted_fk=1)
    repo = tmp_path / "repo"
    install = download_artifacts.install_artifact_archive(
        archive,
        "etfs",
        expected_sha256=_sha256(archive),
        repo_root=repo,
        force=True,
    )
    assert (install / "registry.db").is_file()


def test_bundle_with_fk_but_no_accepted_tsv_is_refused(tmp_path: Path) -> None:
    archive = _build_bundle(tmp_path, dangling_fk=True, accepted_fk=None)
    repo = tmp_path / "repo"
    with pytest.raises(ValueError, match="foreign.key|integrity"):
        download_artifacts.install_artifact_archive(
            archive,
            "etfs",
            expected_sha256=_sha256(archive),
            repo_root=repo,
            force=True,
        )


def test_bundle_with_wrong_accepted_fk_count_is_refused(tmp_path: Path) -> None:
    archive = _build_bundle(tmp_path, dangling_fk=True, accepted_fk=99)
    repo = tmp_path / "repo"
    with pytest.raises(ValueError, match="foreign.key|accepted"):
        download_artifacts.install_artifact_archive(
            archive,
            "etfs",
            expected_sha256=_sha256(archive),
            repo_root=repo,
            force=True,
        )
```

Adjust `match=` strings to whatever the implementation raises; keep the three behaviors.

- [ ] **Step 3: Run tests — expect FAIL**

```powershell
$env:ML4T_RESULTS_FILE='F:\temp\pytest\ml4t-test-results.jsonl'
$env:PYTHONUTF8='1'
uv run --no-sync pytest tests/test_download_artifacts.py -k "documented_fk or no_accepted_tsv or wrong_accepted" -v --basetemp=F:\temp\pytest
```

(If `uv run --no-sync` is unavailable, use the sibling worktree venv python as in prior SDD runs.)

Expected: new tests FAIL (current code refuses any FK).

- [ ] **Step 4: Implement minimal `_verify_run_log` change**

Keep checksums, WAL refusal, and `integrity != ("ok",)` refusal.

Replace the blunt `or foreign_keys` with:

1. Parse `.release/accepted_registry.tsv` if present; read the `foreign_keys` column from the data row (integer).
2. If no file / no column → expected FK count = `0`.
3. If `integrity != ("ok",)` → raise (unchanged message or clearer).
4. If `len(foreign_keys) != expected` → raise a **distinct** message that mentions foreign keys and the expected vs actual counts (do not call this an integrity failure).
5. If counts match (including both zero) → return.

Suggested shape:

```python
def _accepted_foreign_key_count(run_log: Path) -> int:
    path = run_log / ".release" / "accepted_registry.tsv"
    if not path.is_file():
        return 0
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if len(lines) < 2:
        return 0
    header = lines[0].split("\t")
    row = lines[1].split("\t")
    try:
        idx = header.index("foreign_keys")
        return int(row[idx])
    except (ValueError, IndexError):
        return 0
```

- [ ] **Step 5: Run tests — expect PASS**

```powershell
$env:ML4T_RESULTS_FILE='F:\temp\pytest\ml4t-test-results.jsonl'
$env:PYTHONUTF8='1'
uv run --no-sync pytest tests/test_download_artifacts.py -v --basetemp=F:\temp\pytest
```

Expected: all tests in the file PASS, including the three new ones.

- [ ] **Step 6: Commit**

```powershell
git add scripts/download_artifacts.py tests/test_download_artifacts.py
git commit -m "fix: accept published registry foreign-key counts from release TSV"
```

---

### Task 2: Re-install etfs artifacts and finish overlay Task 4 gate

**Files:** none created (verification + ledger). May delete `case_studies/etfs/etf-diag-*`.

**Interfaces:**
- Consumes: fixed installer; existing `tests/test_etf_calibration_overlay.py::test_build_readout_against_published_registry`; `docs/operator/etf_calibration.py`

- [ ] **Step 1: Remove diagnostic extract dirs**

```powershell
Remove-Item -Recurse -Force "F:\Knowledge-Base\03-Development\Active-Projects\trading\machine-learning-for-trading-git\case_studies\etfs\etf-diag-*"
```

- [ ] **Step 2: Download with force**

```powershell
uv run --no-sync python scripts/download_artifacts.py --cs etfs --force
```

Expected: `Verifying and installing... done` (not the previous integrity ValueError).

- [ ] **Step 3: Snapshot `run_log` mtimes before smoke**

```powershell
Get-ChildItem case_studies/etfs/run_log -Recurse | Select-Object FullName, LastWriteTime, Length |
  Export-Csv F:\temp\etf-run-log-before.csv -NoTypeInformation
```

- [ ] **Step 4: Overlay suite including production_extract**

```powershell
$env:ML4T_RESULTS_FILE='F:\temp\pytest\ml4t-test-results.jsonl'
$env:PYTHONUTF8='1'
uv run --no-sync pytest tests/test_etf_calibration_overlay.py -v --basetemp=F:\temp\pytest
uv run --no-sync pytest tests/test_etf_calibration_overlay.py -v -m production_extract --basetemp=F:\temp\pytest
```

Expected: **9 passed, 0 skipped** on the full file (or 1 passed on the marker-only run). Paste the summary into the SDD ledger / Outlook implement Status trail.

- [ ] **Step 5: Headless readout smoke**

```powershell
uv run --no-sync python docs/operator/etf_calibration.py
```

Expected: six section headers (`1. Bundle present` … `6. Does not establish`); no exception. If `resolve_solvent_carrier` refuses (insolvent / stale), that is an honest hard stop — capture the exception text and stop Task 2 for operator decision (do not bypass solvency).

- [ ] **Step 6: Confirm no overlay writes under `run_log`**

Re-export mtimes to `F:\temp\etf-run-log-after.csv` and diff against Step 3. Expected: identical paths and timestamps (installer already wrote the tree; Step 5 must not mutate further). New `-wal`/`-shm` from a read-only open would be a finding — record and escalate (known Windows `mode=ro` WAL sidecar risk); do not claim Task 4 green if sidecars appear from the readout.

- [ ] **Step 7: Update `.superpowers/sdd/progress.md` and commit only if code changed**

If only verification, no commit. If smoke required a tiny overlay fix, TDD that fix first in a new commit.

---

### Task 3 (optional): Merge nested `strategy` spec polish

**Files:** bring `3084735` from `feat/etf-cal-task1` onto `feat/etf-calibration-overlay` if still unmerged.

- [ ] **Step 1:** `git log --oneline b921449..feat/etf-cal-task1` — confirm `3084735` still only on that branch.
- [ ] **Step 2:** Cherry-pick or merge; re-run `tests/test_etf_calibration_overlay.py`.
- [ ] **Step 3:** Commit only if merge creates a merge commit; otherwise cherry-pick already commits.

Skip this task if the operator prefers the minimal integration tip without that polish.

---

### Task 4: Finish branch + Outlook evidence

**Files:** Outlook tasks only (via `outlook-workstream`).

- [ ] **Step 1:** Run `superpowers:finishing-a-development-branch` — verify overlay + download_artifacts tests, then present the four options (merge / PR / keep / discard).
- [ ] **Step 2:** Complete Outlook `ETF-cal implement` only with pytest output from Task 2 Step 4.
- [ ] **Step 3:** Leave `run` / `record` open until a real guide walk (operator). Do not mark them complete from this install fix alone.

---

## Spec coverage

| Requirement | Task |
|-------------|------|
| Root-cause installer gate | 1 |
| Published etfs install | 2 |
| Overlay production_extract + smoke + no run_log writes | 2 |
| Optional nested-spec polish | 3 |
| Operator closeout | 4 |

## Evidence already gathered (do not re-diagnose)

```text
sha256 match True
integrity first [('ok',)]
fk count 3
fk sample [('fold_metrics', 4425, 'prediction_sets', 0), ...]
accepted_registry.tsv foreign_keys=3
```

## Remaining known risks (accepted)

- Windows `test_notebook_sync` path-separator failures and CRLF hash noise are **pre-existing** and out of this plan’s scope.
- Unmerged `3084735` is polish, not required for Task 4 green.
- If headless smoke hits a solvency refusal, that is book behavior — escalate, do not fabricate a carrier.

---

## Execution handoff

Plan path: `docs/superpowers/plans/2026-10-18-etf-artifact-install-fk-gate.md`

**Two execution options:**

1. **Subagent-Driven (recommended)** — Task 1 then Task 2 with review between; Task 3 optional; Task 4 finish/Outlook.
2. **Inline Execution** — `executing-plans` in this session with checkpoints after each task.

Which approach?
