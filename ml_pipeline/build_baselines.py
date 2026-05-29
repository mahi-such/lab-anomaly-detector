"""
build_baselines.py
==================
BUILDER — run once (or on every data refresh) to produce the artefact
that the API loads at startup.

Usage
-----
    python build_baselines.py                          # default paths
    python build_baselines.py --csv path/to/data.csv  # override CSV
    python build_baselines.py --out path/to/out.json  # override output

What it does
------------
1. Loads rely_lis_model_features_v10.csv (or the path you pass in).
2. Computes per-biomarker population statistics from result_value_num.
3. Writes population_baselines.json consumed by the API scorer.

Nothing here is imported by the API — this file has no runtime role.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

DEFAULT_CSV = "ml_pipeline/data/rely_lis_model_features_v10.csv"
DEFAULT_OUT = "backend_api/artifacts/population_baselines.json"

# Minimum samples required before a biomarker gets a baseline entry.
MIN_SAMPLES = 5

def build_population_baselines(df: pd.DataFrame) -> dict[str, dict]:
    """
    Compute per-biomarker descriptive statistics from *df*.
    mean, std, p5, p25, median, p75, p95,
    n_samples, ref_min_typical, ref_max_typical
    """
    clean = df.dropna(subset=["biomarker_code", "result_value_num"]).copy()

    baselines: dict[str, dict] = {}

    for code, grp in clean.groupby("biomarker_code"):
        vals = grp["result_value_num"].dropna()
        if len(vals) < MIN_SAMPLES:
            continue

        ref_min_raw = (
            grp["ref_min_parsed"].median()
            if "ref_min_parsed" in grp.columns
            else None
        )
        ref_max_raw = (
            grp["ref_max_parsed"].median()
            if "ref_max_parsed" in grp.columns
            else None
        )

        def safe(v) -> float | None:
            """Return rounded float or None for NaN / missing."""
            if v is None:
                return None
            try:
                f = float(v)
                return None if math.isnan(f) else round(f, 4)
            except (TypeError, ValueError):
                return None

        baselines[str(code)] = {
            "mean":            round(float(vals.mean()), 4),
            "std":             round(float(vals.std(ddof=1)), 4),
            "p5":              round(float(vals.quantile(0.05)), 4),
            "p25":             round(float(vals.quantile(0.25)), 4),
            "median":          round(float(vals.quantile(0.50)), 4),
            "p75":             round(float(vals.quantile(0.75)), 4),
            "p95":             round(float(vals.quantile(0.95)), 4),
            "n_samples":       int(len(vals)),
            "ref_min_typical": safe(ref_min_raw),
            "ref_max_typical": safe(ref_max_raw),
        }

    return baselines

def run(csv_path: str, out_path: str) -> None:
    """Load CSV → build baselines → write JSON."""
    print(f"[builder] Loading CSV  : {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"[builder] Rows loaded  : {len(df):,}")

    baselines = build_population_baselines(df)
    print(f"[builder] Biomarkers   : {len(baselines)} (>= {MIN_SAMPLES} samples each)")

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(baselines, f, indent=2)

    print(f"[builder] Saved        : {out}")

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build population_baselines.json from the model features CSV."
    )
    p.add_argument(
        "--csv",
        default=DEFAULT_CSV,
        help=f"Path to model-features CSV (default: {DEFAULT_CSV})",
    )
    p.add_argument(
        "--out",
        default=DEFAULT_OUT,
        help=f"Output JSON path (default: {DEFAULT_OUT})",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run(csv_path=args.csv, out_path=args.out)