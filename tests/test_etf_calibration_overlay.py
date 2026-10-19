from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_lib():
    path = REPO_ROOT / "docs" / "operator" / "etf_calibration_lib.py"
    spec = importlib.util.spec_from_file_location("etf_calibration_lib", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


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


def test_format_readout_unavailable_ic_leader() -> None:
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
            "ic_leader_family": None,
            "ic_leader_ic": None,
            "ic_leader_sharpe": None,
        }
    )
    assert "IC leader: unavailable from published rows" in text
    assert "IC leader family: None" not in text


def test_build_readout_uses_carrier_seam(monkeypatch, tmp_path: Path) -> None:
    lib = _load_lib()
    db = tmp_path / "case_studies" / "etfs" / "run_log" / "registry.db"
    db.parent.mkdir(parents=True)
    db.write_bytes(b"\x00")

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
    assert out["holdout_note"]
    assert out["does_not_establish"] == lib.does_not_establish_bullets()


def test_notebook_source_calls_lib() -> None:
    src = (REPO_ROOT / "docs" / "operator" / "etf_calibration.py").read_text(encoding="utf-8")
    assert "require_etf_registry" in src
    assert "build_readout" in src
    assert "format_readout" in src
    assert "run_log" in src  # read-only prose


def test_build_readout_refuses_missing_return_artifact(monkeypatch, tmp_path: Path) -> None:
    lib = _load_lib()
    reg = tmp_path / "case_studies" / "etfs" / "run_log" / "registry.db"
    reg.parent.mkdir(parents=True)
    reg.write_bytes(b"sqlite")
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
