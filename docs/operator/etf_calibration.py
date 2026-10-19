# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: tags,-all
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.6
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # ETF calibration readout
#
# This notebook is a read-only registry readout. It does not write anywhere under `run_log/`.

# %%
"""ETF calibration readout (operator notebook)."""

import importlib.util
from pathlib import Path

try:
    here = Path(__file__).resolve().parent  # .py executed as a script
except NameError:
    here = Path.cwd() / "docs" / "operator"  # paired .ipynb in Jupyter

lib_path = here / "etf_calibration_lib.py"
spec = importlib.util.spec_from_file_location("etf_calibration_lib", lib_path)
lib = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lib)

ROOT = lib.repo_root_from_here()
lib.require_etf_registry(ROOT)
print(lib.format_readout(lib.build_readout(ROOT)))
