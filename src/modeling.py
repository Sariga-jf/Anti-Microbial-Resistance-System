"""Trend analysis, forecasting and early-warning classification for resistance (%).

Method (kept simple and explainable on purpose, only ~8 yearly points per pair exist):
  * Trend: ordinary least-squares slope of resistance (%) on year, with a p-value (scipy linregress).
  * Forecast: linear regression (scikit-learn) on year.
  * Validation: chronological walk-forward. For each year t (from the 4th point on) the model is fitted on
    years < t only and predicts t. No future data is used to predict the past.
  * Baseline: "naive" forecast = the previous year's value. A forecast is only shown when the trend model's
    walk-forward MAE is no worse than the baseline's.
  * Uncertainty: approximate 95% range = forecast +/- 1.96 x walk-forward RMSE (not a formal prediction interval).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression

MIN_TRAIN = 3  # smallest training window used inside walk-forward validation


@dataclass
class Criteria:
    """All thresholds used for trend labels and early-warning categories (user-adjustable)."""
    horizon: int = 1             # years ahead to forecast
    min_points: int = 6          # minimum yearly observations before a forecast is attempted
    slope_threshold: float = 0.5  # |slope| (percentage points / year) below this => "Stable"
    require_significance: bool = True   # trend must also have p <= alpha to count as increasing/decreasing
    alpha: float = 0.10
    moderate_change: float = 2.0  # predicted rise (pts) over the horizon for Moderate Concern
    high_change: float = 5.0      # predicted rise (pts) over the horizon for High Concern
    high_level: float = 70.0      # latest resistance (%) treated as an already-high level
    require_baseline_win: bool = True   # only trust forecasts that beat the naive baseline in validation


@dataclass
class PairResult:
    organism: str
    antibiotic: str
    years: np.ndarray
    values: np.ndarray
    n_points: int
    slope: float
    p_value: float
    trend: str
    forecast_years: np.ndarray = field(default_factory=lambda: np.array([]))
    forecast: np.ndarray = field(default_factory=lambda: np.array([]))
    lower: np.ndarray = field(default_factory=lambda: np.array([]))
    upper: np.ndarray = field(default_factory=lambda: np.array([]))
    mae_model: float = np.nan
    mae_baseline: float = np.nan
    n_validation: int = 0
    forecast_status: str = ""   # "Available" or the reason it is not
    rmse: float = np.nan


def _fit_linear(x, y):
    return LinearRegression().fit(np.asarray(x, float).reshape(-1, 1), np.asarray(y, float))


def walk_forward(years: np.ndarray, values: np.ndarray, min_train: int = MIN_TRAIN):
    """Chronological one-step-ahead validation. Returns (errors_model, errors_baseline)."""
    em, eb = [], []
    for i in range(min_train, len(values)):
        m = _fit_linear(years[:i], values[:i])
        pred = float(np.clip(m.predict([[years[i]]])[0], 0, 100))
        em.append(pred - values[i])
        eb.append(values[i - 1] - values[i])
    return np.array(em), np.array(eb)


def classify_trend(slope: float, p_value: float, c: Criteria) -> str:
    if np.isnan(slope):
        return "Insufficient data"
    significant = (not c.require_significance) or (p_value <= c.alpha)
    if abs(slope) < c.slope_threshold or not significant:
        return "Stable"
    return "Increasing" if slope > 0 else "Decreasing"


def analyse_pair(g: pd.DataFrame, c: Criteria) -> PairResult:
    g = g.sort_values("year")
    years = g["year"].to_numpy(int)
    vals = g["resistant_pct"].to_numpy(float)
    org, ab = g["organism_short"].iloc[0], g["antibiotic"].iloc[0]
    n = len(g)
    if n < 3:
        return PairResult(org, ab, years, vals, n, np.nan, np.nan, "Insufficient data",
                          forecast_status=f"Only {n} yearly point(s); at least 3 needed to describe a trend")
    lr = stats.linregress(years, vals)
    slope, p = float(lr.slope), float(lr.pvalue)
    res = PairResult(org, ab, years, vals, n, slope, p, classify_trend(slope, p, c))
    if n < c.min_points:
        res.forecast_status = f"Not forecast: {n} yearly points (minimum {c.min_points})"
        return res
    em, eb = walk_forward(years, vals)
    res.n_validation = len(em)
    res.mae_model, res.mae_baseline = float(np.mean(np.abs(em))), float(np.mean(np.abs(eb)))
    res.rmse = float(np.sqrt(np.mean(em ** 2)))
    if c.require_baseline_win and res.mae_model > res.mae_baseline:
        res.forecast_status = (f"Not forecast: trend model error ({res.mae_model:.2f} pts) is worse than the "
                               f"naive baseline ({res.mae_baseline:.2f} pts) in time-aware validation")
        return res
    model = _fit_linear(years, vals)
    fy = np.arange(years.max() + 1, years.max() + 1 + c.horizon)
    fc = np.clip(model.predict(fy.reshape(-1, 1)), 0, 100)
    half = 1.96 * res.rmse
    res.forecast_years, res.forecast = fy, fc
    res.lower, res.upper = np.clip(fc - half, 0, 100), np.clip(fc + half, 0, 100)
    res.forecast_status = "Available"
    return res


def warning_for(res: PairResult, c: Criteria) -> tuple[str, str]:
    """Return (category, reason). Screening categories only, not clinical risk classes."""
    if res.trend == "Insufficient data":
        return "Not assessed", res.forecast_status
    latest = float(res.values[-1])
    has_fc = res.forecast_status == "Available"
    change = float(res.forecast[-1] - latest) if has_fc else np.nan
    reasons = []
    cat = "Low Concern"
    if res.trend == "Increasing":
        trend_txt = f"sustained upward trend (+{res.slope:.2f} pts/yr, p={res.p_value:.3f})"
        if not has_fc:
            cat = "Moderate Concern"
            reasons.append(trend_txt + "; no validated forecast, so rated from the observed trend only")
        elif change >= c.high_change:
            cat = "High Concern"
            reasons.append(trend_txt + f"; predicted rise of {change:+.1f} pts (>= {c.high_change:g})")
        elif change >= c.moderate_change:
            cat = "Moderate Concern"
            reasons.append(trend_txt + f"; predicted rise of {change:+.1f} pts (>= {c.moderate_change:g})")
        else:
            reasons.append(trend_txt + f"; but predicted change is small ({change:+.1f} pts < {c.moderate_change:g})")
    if latest >= c.high_level and res.trend != "Decreasing":
        reasons.append(f"latest resistance already high ({latest:.1f}% >= {c.high_level:g}%)")
        if cat == "Low Concern":
            cat = "Moderate Concern"
    if not reasons:
        reasons.append("trend " + res.trend.lower() + " and no threshold exceeded")
    return cat, "; ".join(reasons)


def analyse_all(df: pd.DataFrame, c: Criteria) -> tuple[pd.DataFrame, dict]:
    """Analyse every organism-antibiotic pair in df. Returns (summary table, {(org, abx): PairResult})."""
    results, rows = {}, []
    for (org, ab), g in df.groupby(["organism_short", "antibiotic"]):
        r = analyse_pair(g, c)
        cat, why = warning_for(r, c)
        results[(org, ab)] = r
        has_fc = r.forecast_status == "Available"
        latest = float(r.values[-1])
        rows.append({
            "Organism": org, "Antibiotic": ab,
            "Years of data": r.n_points, "Latest year": int(r.years[-1]),
            "Latest resistance (%)": round(latest, 1),
            "Slope (pts/yr)": round(r.slope, 2) if not np.isnan(r.slope) else np.nan,
            "Trend": r.trend,
            "Forecast year": int(r.forecast_years[-1]) if has_fc else np.nan,
            "Predicted resistance (%)": round(float(r.forecast[-1]), 1) if has_fc else np.nan,
            "Range low (%)": round(float(r.lower[-1]), 1) if has_fc else np.nan,
            "Range high (%)": round(float(r.upper[-1]), 1) if has_fc else np.nan,
            "Change (pts)": round(float(r.forecast[-1] - latest), 1) if has_fc else np.nan,
            "Model MAE (pts)": round(r.mae_model, 2) if not np.isnan(r.mae_model) else np.nan,
            "Baseline MAE (pts)": round(r.mae_baseline, 2) if not np.isnan(r.mae_baseline) else np.nan,
            "Forecast status": r.forecast_status,
            "Risk category": cat, "Reason": why,
        })
    out = pd.DataFrame(rows)
    return out, results
