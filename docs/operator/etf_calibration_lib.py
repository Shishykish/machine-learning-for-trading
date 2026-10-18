from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

DOWNLOAD_HINT: str = "uv run python scripts/download_artifacts.py --cs etfs"


def ensure_repo_on_path(repo_root: Path) -> None:
    """Add ``repo_root`` to ``sys.path`` so repo imports resolve."""
    root = str(repo_root.resolve())
    if root not in sys.path:
        sys.path.insert(0, root)


def repo_root_from_here(start: Path | None = None) -> Path:
    """Walk up from ``start`` until we find a directory containing ``case_studies/etfs``."""
    here = (start or Path(__file__).resolve()).resolve()
    for parent in [here, *here.parents]:
        if (parent / "case_studies" / "etfs").is_dir():
            return parent
    raise FileNotFoundError("No ancestor directory contains case_studies/etfs")


def etf_registry_path(repo_root: Path) -> Path:
    """Path to the ETF case-study registry database."""
    return repo_root / "case_studies" / "etfs" / "run_log" / "registry.db"


def require_etf_registry(repo_root: Path) -> Path:
    """Return the registry path, raising if it is absent."""
    path = etf_registry_path(repo_root)
    if not path.exists():
        raise FileNotFoundError(
            f"ETF registry not found at {path}. "
            f"Download the artifacts with: {DOWNLOAD_HINT}"
        )
    return path


def resolve_carrier(repo_root: Path, case_study: str) -> dict:
    """Resolve the canonical solvent carrier for ``case_study``."""
    ensure_repo_on_path(repo_root)
    from case_studies.utils.strategy_analysis import resolve_solvent_carrier

    return resolve_solvent_carrier(case_study)


def does_not_establish_bullets() -> list[str]:
    """Disclaimers every ETF calibration readout must carry."""
    return [
        "This is a teaching readout, not an MT5 or retail-broker signal.",
        "It describes the published registry; see docs/what-this-is.md for scope.",
        "Selection happened inside the case-study universe, not the operator's universe.",
        "It is research output, not a claim of unbiased alpha or a go-live recommendation.",
        "These numbers do not establish that the strategy works as retail CFDs.",
    ]


def _prediction_ic(
    registry_db: Path, prediction_hash: str
) -> tuple[float, float, float] | None:
    """Return (ic_mean_daily, ic_ci_lo, ic_ci_hi) for a prediction hash, or None."""
    con = sqlite3.connect(f"file:{registry_db}?mode=ro", uri=True)
    try:
        row = con.execute(
            "SELECT ic_mean_daily, ic_ci_lo, ic_ci_hi FROM prediction_metrics "
            "WHERE prediction_hash = ?",
            (prediction_hash,),
        ).fetchone()
    finally:
        con.close()
    if row is None:
        return None
    return tuple(row)


def _ic_leader_row(
    repo_root: Path, case_study: str
) -> tuple[str | None, float | None, float | None]:
    """Best IC row from the signal-stage leaderboard, or (None, None, None)."""
    ensure_repo_on_path(repo_root)
    from case_studies.utils.backtest_explorer import BacktestExplorer

    try:
        frame = BacktestExplorer(case_study).best(stage="signal", top_n=0)
    except RuntimeError:
        return (None, None, None)
    if frame.is_empty():
        return (None, None, None)
    leader = frame.sort("ic_mean_daily", descending=True, nulls_last=True).row(0, named=True)
    return (leader.get("family"), leader.get("ic_mean_daily"), leader.get("sharpe"))


def _cost_sensitivity_note(registry_db: Path, prediction_hash: str) -> str:
    """Summarize the cost-sensitivity grid for a prediction hash."""
    con = sqlite3.connect(f"file:{registry_db}?mode=ro", uri=True)
    try:
        rows = con.execute(
            """
            SELECT bm.sharpe
            FROM backtest_runs b
            JOIN backtest_metrics bm ON bm.backtest_hash = b.backtest_hash
            WHERE b.stage = 'cost_sensitivity' AND b.prediction_hash = ?
            ORDER BY bm.sharpe ASC;
            """,
            (prediction_hash,),
        ).fetchall()
    finally:
        con.close()
    if not rows:
        return "no cost-stage rows found for this prediction_hash"
    sharpes = [r[0] for r in rows if r[0] is not None]
    if not sharpes:
        return f"cost grid: {len(rows)} levels, no measurable sharpe"
    return f"cost grid: {len(rows)} levels, sharpe {min(sharpes):.4f}-{max(sharpes):.4f}"


def _holdout_note(carrier: dict) -> str:
    """Describe sealed-holdout status from the carrier dict."""
    if carrier.get("holdout_backtest_hash") is None or carrier.get("holdout_sharpe") is None:
        return "holdout rows missing"
    return f"holdout {carrier['holdout_backtest_hash'][:12]} sharpe {carrier['holdout_sharpe']:.4f}"


def build_readout(repo_root: Path, *, case_study: str = "etfs") -> dict[str, Any]:
    """Build a hermetic ETF calibration readout dict from the registry."""
    registry_db = require_etf_registry(repo_root)
    carrier = resolve_carrier(repo_root, case_study)
    val_prediction_hash = carrier["val_prediction_hash"]

    ic_vals = _prediction_ic(registry_db, val_prediction_hash)
    ic_leader_family, ic_leader_ic, ic_leader_sharpe = _ic_leader_row(repo_root, case_study)
    cost_note = _cost_sensitivity_note(registry_db, val_prediction_hash)
    holdout_note = _holdout_note(carrier)

    spec = json.loads(carrier.get("spec_json", "{}"))
    signal = spec.get("signal", {})
    signal_method = signal.get("method")
    top_k = signal.get("top_k")

    return {
        "registry_path": str(registry_db),
        "artifact_note": "present",
        "family": carrier.get("family"),
        "config_name": carrier.get("config_name"),
        "label": carrier.get("label"),
        "val_backtest_hash": carrier.get("val_backtest_hash"),
        "val_prediction_hash": val_prediction_hash,
        "val_stage": carrier.get("val_stage"),
        "val_sharpe": carrier.get("val_sharpe"),
        "ic_mean_daily": ic_vals[0] if ic_vals else None,
        "ic_ci_lo": ic_vals[1] if ic_vals else None,
        "ic_ci_hi": ic_vals[2] if ic_vals else None,
        "ic_leader_family": ic_leader_family,
        "ic_leader_ic": ic_leader_ic,
        "ic_leader_sharpe": ic_leader_sharpe,
        "cost_sensitivity_note": cost_note,
        "holdout_note": holdout_note,
        "holdout_backtest_hash": carrier.get("holdout_backtest_hash"),
        "holdout_sharpe": carrier.get("holdout_sharpe"),
        "signal_method": signal_method,
        "top_k": top_k,
        "does_not_establish": does_not_establish_bullets(),
    }


def format_readout(readout: dict[str, Any]) -> str:
    """Render the readout dict as a short, operator-facing report."""
    lines: list[str] = []

    lines.append("1. Bundle present")
    lines.append(f"   Registry: {readout.get('registry_path', 'not available from published rows')}")
    lines.append(f"   Status: {readout.get('artifact_note', 'not available from published rows')}")

    lines.append("")
    lines.append("2. Selected configuration")
    lines.append(f"   Family: {readout.get('family', 'not available from published rows')}")
    lines.append(
        f"   Configuration: {readout.get('config_name', 'not available from published rows')}"
    )
    lines.append(f"   Label: {readout.get('label', 'not available from published rows')}")
    signal_method = readout.get('signal_method')
    top_k = readout.get('top_k')
    if signal_method is not None:
        lines.append(f"   Signal method: {signal_method}")
    if top_k is not None:
        lines.append(f"   Top k: {top_k}")

    lines.append("")
    lines.append("3. IC vs traded Sharpe")
    lines.append(
        f"   Validation backtest: "
        f"{readout.get('val_backtest_hash', 'not available from published rows')}"
    )
    lines.append(
        f"   Validation Sharpe: {readout.get('val_sharpe', 'not available from published rows')}"
    )
    lines.append(
        f"   Prediction IC (daily): {readout.get('ic_mean_daily', 'not available from published rows')}"
    )
    lines.append(
        f"   IC CI: [{readout.get('ic_ci_lo', 'not available from published rows')}, "
        f"{readout.get('ic_ci_hi', 'not available from published rows')}]"
    )
    lines.append(
        f"   IC leader family: {readout.get('ic_leader_family', 'not available from published rows')}"
    )
    lines.append(
        f"   IC leader IC / Sharpe: "
        f"{readout.get('ic_leader_ic', 'not available from published rows')} / "
        f"{readout.get('ic_leader_sharpe', 'not available from published rows')}"
    )

    lines.append("")
    lines.append("4. Cost survival")
    lines.append(
        f"   {readout.get('cost_sensitivity_note', 'not available from published rows')}"
    )

    lines.append("")
    lines.append("5. Sealed holdout")
    lines.append(f"   {readout.get('holdout_note', 'not available from published rows')}")

    lines.append("")
    lines.append("6. Does not establish")
    for bullet in readout.get("does_not_establish", []):
        lines.append(f"   - {bullet}")

    return "\n".join(lines)
