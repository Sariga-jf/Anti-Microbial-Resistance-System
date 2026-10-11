"""Data loading, validation and resistance calculation for the AMR dashboard.

Resistance (%) is derived as 100 - susceptible (%). This is valid for this dataset because every row
comes from the same ICMR-AMRSN yearly tables, where susceptible_pct = susceptible_n / tested_n x 100
(this is checked below). The reports do not publish intermediate results separately, so
"resistance" here means NON-SUSCEPTIBLE (resistant + intermediate). See README limitation 3.

Only aggregated yearly surveillance data is loaded. No patient-level records are read here.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import viz_utils as vu

DATA_FILE = vu.PROCESSED / "clean_trends.csv"
REQUIRED = ["organism", "antibiotic", "year", "susceptible_n", "tested_n", "susceptible_pct"]
PCT_TOLERANCE = 0.5  # percentage points allowed between reported and recomputed susceptibility (rounding)


class DataError(Exception):
    """Raised when the dataset is missing or cannot be used."""


def _validate_columns(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise DataError(
            f"Required column(s) {missing} not found. The file has: {list(df.columns)}. "
            "Without susceptibility counts/percentages, resistance cannot be calculated, and no values are invented."
        )


def load_trends(path: Path | str | None = None) -> pd.DataFrame:
    """Load the yearly organism x antibiotic table and add resistance columns.

    Added columns: organism_short, gram, resistant_pct (= 100 - susceptible_pct), resistant_n, ci_low, ci_high.
    """
    path = Path(path) if path else DATA_FILE
    if not path.exists():
        raise DataError(f"Data file not found: {path}")
    try:
        df = pd.read_csv(path)
    except Exception as exc:  # unreadable / malformed file
        raise DataError(f"Could not read {path.name}: {exc}") from exc
    _validate_columns(df)

    for col in ["year", "susceptible_n", "tested_n", "susceptible_pct"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["organism"] = df["organism"].astype(str).str.strip()
    df["antibiotic"] = df["antibiotic"].astype(str).str.strip().str.lower()

    # Rows that cannot give a valid resistance value are dropped (never filled with 0).
    ok = (df[["year", "susceptible_n", "tested_n", "susceptible_pct"]].notna().all(axis=1)
          & (df["tested_n"] > 0) & df["susceptible_pct"].between(0, 100)
          & (df["susceptible_n"] <= df["tested_n"]) & (df["susceptible_n"] >= 0))
    df = df[ok].copy()
    if df.empty:
        raise DataError("No valid rows remain after validation.")

    # One value per organism-antibiotic-year: keep the newest source report (later editions revise earlier years).
    if "source_report_year" in df.columns:
        df = df.sort_values("source_report_year")
    df = df.drop_duplicates(["organism", "antibiotic", "year"], keep="last")

    df["year"] = df["year"].astype(int)
    df["organism_short"] = df["organism"].map(vu.SHORT).fillna(df["organism"])
    df["gram"] = df["organism"].map(vu.GRAM).fillna("Unknown")
    df["resistant_pct"] = 100 - df["susceptible_pct"]
    df["resistant_n"] = df["tested_n"] - df["susceptible_n"]
    # 95% Wilson interval for the resistance proportion (shows how uncertain small samples are)
    p = df["resistant_n"] / df["tested_n"]
    n = df["tested_n"]
    z = 1.96
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    df["ci_low"] = (centre - half) * 100
    df["ci_high"] = (centre + half) * 100
    return df.sort_values(["organism", "antibiotic", "year"]).reset_index(drop=True)


def pair_label(organism_short: str, antibiotic: str) -> str:
    return f"{organism_short} / {antibiotic}"


def weighted_resistance(df: pd.DataFrame) -> float:
    """Overall resistance % = total non-susceptible isolates / total isolates tested (isolate-weighted)."""
    n = df["tested_n"].sum()
    return float(df["resistant_n"].sum() / n * 100) if n else float("nan")


def quality_report(raw_path: Path | str | None = None) -> dict:
    """Quality checks on the file as stored on disk (before cleaning), for the Data Explorer page."""
    path = Path(raw_path) if raw_path else DATA_FILE
    raw = pd.read_csv(path)
    _validate_columns(raw)
    num = raw.copy()
    for c in ["year", "susceptible_n", "tested_n", "susceptible_pct"]:
        num[c] = pd.to_numeric(num[c], errors="coerce")
    key = ["organism", "antibiotic", "year"]
    recomputed = num["susceptible_n"] / num["tested_n"] * 100
    return {
        "rows": len(raw),
        "missing": raw[REQUIRED].isna().sum().rename("Missing values").to_frame(),
        "duplicate_keys": int(raw.duplicated(key).sum()),
        "pct_out_of_range": int((~num["susceptible_pct"].between(0, 100)).sum()),
        "n_inconsistent": int((num["susceptible_n"] > num["tested_n"]).sum()),
        "pct_mismatch": int(((recomputed - num["susceptible_pct"]).abs() > PCT_TOLERANCE).sum()),
        "max_mismatch": float((recomputed - num["susceptible_pct"]).abs().max()),
    }
