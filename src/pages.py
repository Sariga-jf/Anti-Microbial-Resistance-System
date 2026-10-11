"""Streamlit pages. Every page receives (filtered, full): `filtered` already reflects the sidebar filters and is the
only data used for metrics, charts and tables. `full` is used only to explain what the filters removed.
Resistance (%) = 100 - susceptible (%): see src/data_processing.py and the About page."""
from __future__ import annotations

import dataclasses

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from . import charts as ch
from . import data_processing as dp
from . import modeling as md
from . import theme as th
from . import viz_utils as vu

plt.rcParams["figure.max_open_warning"] = 0
RES = "Resistance (%)"
FIGSIZE = (9, 4.6)


# ------------------------------------------------------------------ helpers
def _show(fig):
    st.pyplot(fig)
    plt.close(fig)


def _empty(filtered) -> bool:
    if filtered.empty:
        st.warning("No records match the current filters. Widen the filters in the sidebar (or lower 'Minimum isolates tested').")
        return True
    return False


def get_criteria() -> md.Criteria:
    return st.session_state.get("crit", md.Criteria())


@st.cache_data(show_spinner=False)
def _analyse(df: pd.DataFrame, crit: dict):
    return md.analyse_all(df, md.Criteria(**crit))


def analyse(df: pd.DataFrame, crit: md.Criteria | None = None):
    crit = crit or get_criteria()
    return _analyse(df, dataclasses.asdict(crit))


def _style_cat(df: pd.DataFrame, col: str, colors: dict):
    try:
        return df.style.map(lambda v: f"color:{colors.get(v, '#000')};font-weight:600", subset=[col])
    except Exception:  # styling is cosmetic; never block the table
        return df


def _wres(g: pd.DataFrame) -> float:
    return dp.weighted_resistance(g)


def _plot_pair(ax, r: md.PairResult, color, label, band=True):
    """Observed = solid line with filled markers. Predicted = dashed line with hollow diamonds (+ approximate range)."""
    ax.plot(r.years, r.values, marker="o", color=color, lw=2, label=f"{label} (observed)")
    if len(r.forecast):
        fx = np.r_[r.years[-1], r.forecast_years]
        fy = np.r_[r.values[-1], r.forecast]
        ax.plot(fx, fy, ls="--", color=color, lw=2, alpha=.9)
        ax.plot(r.forecast_years, r.forecast, ls="none", marker="D", mfc="white", mec=color, ms=8, mew=2,
                label=f"{label} (predicted)")
        if band:
            ax.fill_between(r.forecast_years, r.lower, r.upper, color=color, alpha=.15)


def _finish(ax, title):
    ax.set_xlabel("Year")
    ax.set_ylabel(RES)
    ax.set_title(title)
    ax.set_ylim(-3, 103)
    ax.grid(alpha=.3)
    ax.spines[["top", "right"]].set_visible(False)
    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))


def _hbar(ax, labels, values, colors, xlabel=RES, fmt="{:.1f}%"):
    bars = ax.barh(labels, values, color=colors)
    for b, v in zip(bars, values):
        ax.text(v + 0.8, b.get_y() + b.get_height() / 2, fmt.format(v), va="center", fontsize=9)
    ax.set_xlabel(xlabel)
    ax.spines[["top", "right"]].set_visible(False)


def _weighted_by(df, col):
    return (df.groupby(col).apply(_wres, include_groups=False).sort_values())


def _legend_note():
    st.caption("Observed = solid line with filled markers. Predicted = dashed line with hollow diamonds and a shaded approximate range.")


def _trend_note():
    st.markdown(
        " ".join(f"<span class='legend-dot' style='background:{c}'></span>{t}&nbsp;&nbsp;"
                 for t, c in th.TREND_COLORS.items() if t != "Insufficient data"), unsafe_allow_html=True)


# ------------------------------------------------------------------ A. Overview
def overview(filtered, full):
    st.title("Antibiotic Resistance Trend Predictor")
    st.caption("Indian ICMR-AMRSN hospital surveillance data, yearly. Primary metric: " + RES)
    if _empty(filtered):
        return
    summary, _ = analyse(filtered)
    n_inc = int((summary["Trend"] == "Increasing").sum())
    n_flag = int(summary["Risk category"].isin(["Moderate Concern", "High Concern"]).sum())

    c = st.columns(3)
    c[0].metric("Overall resistance", f"{dp.weighted_resistance(filtered):.1f}%", help="Non-susceptible isolates / isolates tested, all selected rows.")
    c[1].metric("Bacteria analysed", filtered["organism"].nunique())
    c[2].metric("Antibiotics analysed", filtered["antibiotic"].nunique())
    c = st.columns(3)
    c[0].metric("Bacteria-antibiotic combinations", len(summary))
    c[1].metric("Combinations with increasing resistance", n_inc, help="Significant upward slope; thresholds on the Early Warning page.")
    c[2].metric("Combinations flagged for further review", n_flag, help="Moderate or High Concern screening category.")
    st.caption(th.RESISTANCE_NOTE)

    a, b = st.columns(2)
    with a:
        st.subheader("Distribution of resistance")
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.hist(filtered["resistant_pct"], bins=np.arange(0, 110, 10), color=th.NAVY, edgecolor="white")
        ax.set_xlabel(RES)
        ax.set_ylabel("Number of organism-antibiotic-year values")
        ax.spines[["top", "right"]].set_visible(False)
        _show(fig)
    with b:
        st.subheader("Resistance by bacteria")
        m = _weighted_by(filtered, "organism_short")
        fig, ax = plt.subplots(figsize=(6, 4))
        _hbar(ax, m.index, m.values, [ch.ORG_COLORS[o] for o in m.index], xlabel="Resistance (%), weighted by isolates tested")
        ax.set_xlim(0, 100)
        _show(fig)

    a, b = st.columns(2)
    with a:
        st.subheader("Resistance by antibiotic")
        m = _weighted_by(filtered, "antibiotic")
        fig, ax = plt.subplots(figsize=(6, max(4, 0.28 * len(m))))
        _hbar(ax, m.index, m.values, th.NAVY, xlabel="Resistance (%), weighted by isolates tested")
        ax.set_xlim(0, 105)
        _show(fig)
    with b:
        yr = int(filtered["year"].max())
        st.subheader(f"Highest observed resistance ({yr})")
        d = filtered[filtered["year"] == yr].copy()
        d["pair"] = d["organism_short"] + " / " + d["antibiotic"]
        d = d.nlargest(12, "resistant_pct").sort_values("resistant_pct")
        fig, ax = plt.subplots(figsize=(6, 5))
        _hbar(ax, d["pair"], d["resistant_pct"], [ch.ORG_COLORS[o] for o in d["organism_short"]])
        ax.set_xlim(0, 112)
        _show(fig)

    st.subheader("Resistance trend over the study period")
    yearly = filtered.groupby("year").apply(_wres, include_groups=False)
    fig, ax = plt.subplots(figsize=(10, 4.4))
    for o, g in filtered.groupby("organism_short"):
        s = g.groupby("year").apply(_wres, include_groups=False)
        ax.plot(s.index, s.values, marker="o", ms=3, lw=1.3, alpha=.8, color=ch.ORG_COLORS[o], label=o)
    ax.plot(yearly.index, yearly.values, color="black", lw=3, marker="o", label="All selected")
    _finish(ax, "Isolate-weighted resistance by year")
    ax.legend(frameon=False, ncol=4, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.15))
    _show(fig)


# ------------------------------------------------------------------ B. Organism and antibiotic analysis
def analysis(filtered, full):
    st.title("Antibiotic & Organism Analysis")
    if _empty(filtered):
        return
    orgs = sorted(filtered["organism_short"].unique())
    c1, c2, c3 = st.columns([2, 2, 1])
    org = c1.selectbox("Bacterial organism", orgs)
    abx_for_org = sorted(filtered.loc[filtered["organism_short"] == org, "antibiotic"].unique())
    abx = c2.selectbox("Antibiotic", abx_for_org)
    horizon = c3.selectbox("Forecast years ahead", [1, 2, 3], index=0)
    crit = dataclasses.replace(get_criteria(), horizon=horizon)

    g = filtered[(filtered["organism_short"] == org) & (filtered["antibiotic"] == abx)]
    res = md.analyse_pair(g, crit)
    cat, why = md.warning_for(res, crit)
    latest = g.sort_values("year").iloc[-1]

    st.subheader(f"{org} / {abx}")
    m = st.columns(5)
    m[0].metric(f"Observed resistance ({int(latest['year'])})", f"{latest['resistant_pct']:.1f}%",
                help=f"95% CI {latest['ci_low']:.1f}-{latest['ci_high']:.1f}% (Wilson)")
    m[1].metric("Trend direction", res.trend, delta=f"{res.slope:+.2f} pts/yr" if not np.isnan(res.slope) else None,
                delta_color="inverse")
    m[2].metric("Years of data", res.n_points)
    m[3].metric("Isolates tested (latest year)", f"{int(latest['tested_n']):,}")
    if len(res.forecast):
        m[4].metric(f"Predicted ({int(res.forecast_years[-1])})", f"{res.forecast[-1]:.1f}%",
                    delta=f"{res.forecast[-1] - res.values[-1]:+.1f} pts", delta_color="inverse")
    else:
        m[4].metric("Predicted", "Not available")
    st.caption(f"Screening category: **{cat}** - {why}")

    st.markdown("**Historical observed values and predicted values**")
    fig, ax = plt.subplots(figsize=FIGSIZE)
    _plot_pair(ax, res, th.OBSERVED_COLOR, f"{org} / {abx}")
    ax.fill_between(g["year"], g["ci_low"], g["ci_high"], color=th.OBSERVED_COLOR, alpha=.08, label="Observed 95% CI (sampling)")
    _finish(ax, f"{org} / {abx}: observed vs predicted resistance")
    ax.legend(frameon=False, fontsize=8)
    _show(fig)
    _legend_note()
    if len(res.forecast):
        st.caption(f"Time-aware validation ({res.n_validation} held-out years): trend model MAE {res.mae_model:.2f} pts vs naive "
                   f"baseline MAE {res.mae_baseline:.2f} pts. Shaded range = forecast +/- 1.96 x validation RMSE (approximate).")
    else:
        st.info(res.forecast_status)

    st.dataframe(g[["year", "tested_n", "susceptible_n", "resistant_n", "susceptible_pct", "resistant_pct", "ci_low", "ci_high"]]
                 .rename(columns={"year": "Year", "tested_n": "Isolates tested", "susceptible_n": "Susceptible isolates",
                                  "resistant_n": "Non-susceptible isolates", "susceptible_pct": "Susceptible (%)",
                                  "resistant_pct": RES, "ci_low": "95% CI low", "ci_high": "95% CI high"}).round(1),
                 hide_index=True)

    yr = int(latest["year"])
    a, b = st.columns(2)
    with a:
        st.subheader(f"Other antibiotics for {org} ({yr})")
        d = filtered[(filtered["organism_short"] == org) & (filtered["year"] == yr)].sort_values("resistant_pct")
        fig, ax = plt.subplots(figsize=(6, max(3, 0.3 * len(d))))
        _hbar(ax, d["antibiotic"], d["resistant_pct"], [th.FORECAST_COLOR if x == abx else th.NAVY for x in d["antibiotic"]])
        ax.set_xlim(0, 112)
        _show(fig)
    with b:
        st.subheader(f"Other organisms for {abx} ({yr})")
        d = filtered[(filtered["antibiotic"] == abx) & (filtered["year"] == yr)].sort_values("resistant_pct")
        fig, ax = plt.subplots(figsize=(6, max(3, 0.6 * len(d))))
        _hbar(ax, d["organism_short"], d["resistant_pct"], [th.FORECAST_COLOR if x == org else th.NAVY for x in d["organism_short"]])
        ax.set_xlim(0, 112)
        _show(fig)
    st.caption("Highlighted bar = the selected organism / antibiotic. Observed values only.")

    st.subheader(f"Comparison table: antibiotics for {org}, ranked by observed resistance")
    summary, _ = analyse(filtered, crit)
    t = summary[summary["Organism"] == org].sort_values("Latest resistance (%)", ascending=False)
    st.dataframe(t[["Antibiotic", "Years of data", "Latest year", "Latest resistance (%)", "Trend", "Predicted resistance (%)",
                    "Risk category"]], hide_index=True)


# ------------------------------------------------------------------ C. Trends over time
def trends(filtered, full):
    st.title("Resistance Trends Over Time")
    if _empty(filtered):
        return
    crit0 = get_criteria()
    summary0, _ = analyse(filtered, crit0)
    labels = {f"{o} / {a}": (o, a) for o, a in zip(summary0["Organism"], summary0["Antibiotic"])}
    default = list(summary0.sort_values("Slope (pts/yr)", ascending=False)["Organism"].add(" / ")
                   .add(summary0.sort_values("Slope (pts/yr)", ascending=False)["Antibiotic"]).head(3))
    c1, c2, c3 = st.columns([4, 1, 1])
    chosen = c1.multiselect("Bacteria-antibiotic combinations", list(labels), default=default[:3],
                            help="Default: the three combinations with the steepest upward slope in the current selection.")
    horizon = c2.selectbox("Forecast years ahead", [1, 2, 3], index=1)
    show_fc = c3.checkbox("Show forecasts", value=True)
    crit = dataclasses.replace(crit0, horizon=horizon)
    if not chosen:
        st.info("Select at least one combination.")
    else:
        fig, ax = plt.subplots(figsize=(10, 5))
        cmap = plt.get_cmap("tab10")
        notes = []
        for i, lab in enumerate(chosen):
            o, a = labels[lab]
            g = filtered[(filtered["organism_short"] == o) & (filtered["antibiotic"] == a)]
            r = md.analyse_pair(g, crit)
            if not show_fc:
                r.forecast, r.forecast_years = np.array([]), np.array([])
            _plot_pair(ax, r, cmap(i), lab, band=len(chosen) <= 3)
            if show_fc and r.forecast_status != "Available":
                notes.append(f"**{lab}**: {r.forecast_status}")
        _finish(ax, "Resistance over time: observed (solid) and predicted (dashed)")
        ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2)
        _show(fig)
        _legend_note()
        for n in notes:
            st.caption(n)

    summary, _ = analyse(filtered, crit)
    st.subheader("Trend direction for every combination in the current selection")
    _trend_note()
    d = summary.dropna(subset=["Slope (pts/yr)"]).copy()
    d["lab"] = d["Organism"] + " / " + d["Antibiotic"]
    d = d.reindex(d["Slope (pts/yr)"].abs().sort_values(ascending=False).index).head(20).sort_values("Slope (pts/yr)")
    fig, ax = plt.subplots(figsize=(9, max(3.5, 0.3 * len(d))))
    bars = ax.barh(d["lab"], d["Slope (pts/yr)"], color=[th.TREND_COLORS[t] for t in d["Trend"]])
    ax.axvline(0, color="black", lw=.8)
    ax.set_xlabel("Change in resistance (percentage points per year)")
    ax.set_title("Largest yearly changes (20 combinations)")
    ax.spines[["top", "right"]].set_visible(False)
    _show(fig)
    st.caption(f"Increasing/decreasing = |slope| >= {crit.slope_threshold:g} pts/yr and "
               f"{'p <= ' + str(crit.alpha) if crit.require_significance else 'no significance test'}; otherwise Stable. "
               "Grey = stable, red = increasing, green = decreasing.")
    st.dataframe(summary[["Organism", "Antibiotic", "Years of data", "Latest resistance (%)", "Slope (pts/yr)", "Trend",
                          "Predicted resistance (%)", "Forecast status"]].sort_values("Slope (pts/yr)", ascending=False),
                 hide_index=True)

    st.subheader("Resistance heat map over time")
    orgs = sorted(filtered["organism"].unique())
    org = st.selectbox("Organism for heat map", orgs, index=orgs.index("Klebsiella pneumoniae") if "Klebsiella pneumoniae" in orgs else 0)
    _show(ch.fig_heatmap_years(filtered, org))


# ------------------------------------------------------------------ D. Early warning
def early_warning(filtered, full):
    st.title("Resistance Prediction & Early Warning")
    st.markdown(f"<div class='note'>{th.DISCLAIMER}</div>", unsafe_allow_html=True)
    base = get_criteria()  # last-used settings, so the thresholds survive navigating between pages
    with st.expander("Warning criteria (adjustable)", expanded=False):
        c = st.columns(4)
        horizon = c[0].selectbox("Forecast horizon (years)", [1, 2, 3], index=base.horizon - 1)
        min_pts = c[1].slider("Min. yearly points to forecast", 4, 8, base.min_points)
        slope_thr = c[2].number_input("Stable if |slope| below (pts/yr)", 0.0, 5.0, base.slope_threshold, 0.1)
        level = c[3].number_input("Already-high level (%)", 0.0, 100.0, base.high_level, 5.0)
        c = st.columns(4)
        mod = c[0].number_input("Moderate: predicted rise >= (pts)", 0.0, 50.0, base.moderate_change, 0.5)
        high = c[1].number_input("High: predicted rise >= (pts)", 0.0, 50.0, base.high_change, 0.5)
        sig = c[2].checkbox("Require statistical support (p-value)", base.require_significance)
        alpha = c[3].number_input("p-value limit", 0.01, 0.5, base.alpha, 0.01)
        bl = st.checkbox("Only forecast when the model beats the naive baseline in time-aware validation",
                         base.require_baseline_win)
    crit = md.Criteria(horizon=horizon, min_points=min_pts, slope_threshold=slope_thr, require_significance=sig, alpha=alpha,
                       moderate_change=mod, high_change=high, high_level=level, require_baseline_win=bl)
    st.session_state["crit"] = crit
    if _empty(filtered):
        return
    summary, results = analyse(filtered, crit)

    c = st.columns(4)
    for col, cat in zip(c, ["High Concern", "Moderate Concern", "Low Concern", "Not assessed"]):
        col.metric(cat, int((summary["Risk category"] == cat).sum()))
    st.caption(f"{int((summary['Forecast status'] == 'Available').sum())} of {len(summary)} combinations have a validated forecast. "
               "The others are rated from the observed trend only (or not assessed), and no values are invented for them.")

    f1, f2 = st.columns([3, 1])
    cats = f1.multiselect("Show categories", list(th.RISK_COLORS), default=["High Concern", "Moderate Concern", "Low Concern"])
    only_fc = f2.checkbox("Only with forecast", False)
    t = summary[summary["Risk category"].isin(cats)]
    if only_fc:
        t = t[t["Forecast status"] == "Available"]
    order = {"High Concern": 0, "Moderate Concern": 1, "Low Concern": 2, "Not assessed": 3}
    t = t.assign(_o=t["Risk category"].map(order)).sort_values(["_o", "Change (pts)"], ascending=[True, False]).drop(columns="_o")
    cols = ["Organism", "Antibiotic", "Latest year", "Latest resistance (%)", "Trend", "Predicted resistance (%)", "Range low (%)",
            "Range high (%)", "Change (pts)", "Risk category", "Reason"]
    st.dataframe(_style_cat(t[cols], "Risk category", th.RISK_COLORS), hide_index=True)
    st.download_button("Download early-warning table (CSV)", t.to_csv(index=False).encode(), "early_warning_table.csv", "text/csv")

    fc = t[t["Forecast status"] == "Available"].dropna(subset=["Change (pts)"])
    if not fc.empty:
        st.subheader(f"Predicted change in resistance by {int(fc['Forecast year'].iloc[0])} (percentage points)")
        d = fc.reindex(fc["Change (pts)"].abs().sort_values(ascending=False).index).head(20).sort_values("Change (pts)")
        fig, ax = plt.subplots(figsize=(9, max(3.5, 0.3 * len(d))))
        ax.barh(d["Organism"] + " / " + d["Antibiotic"], d["Change (pts)"], color=[th.RISK_COLORS[x] for x in d["Risk category"]])
        ax.axvline(0, color="black", lw=.8)
        ax.set_xlabel("Predicted minus latest observed resistance (pts)")
        ax.spines[["top", "right"]].set_visible(False)
        _show(fig)
        st.caption("Bar colour = screening category (red High, orange Moderate, green Low). Predicted values only; see the range columns for uncertainty.")

    st.subheader("Inspect one combination")
    labs = list((summary["Organism"] + " / " + summary["Antibiotic"]))
    pick = st.selectbox("Combination", labs)
    o, a = pick.split(" / ")
    r = results[(o, a)]
    cat, why = md.warning_for(r, crit)
    fig, ax = plt.subplots(figsize=FIGSIZE)
    _plot_pair(ax, r, th.OBSERVED_COLOR, pick)
    _finish(ax, f"{pick}: {cat}")
    ax.legend(frameon=False, fontsize=8)
    _show(fig)
    st.markdown(f"**Reason for the warning:** {why}")
    if r.forecast_status != "Available":
        st.caption(r.forecast_status)

    with st.expander("How the categories are assigned"):
        st.markdown(f"""
- **Trend**: least-squares slope of resistance on year. *Increasing/Decreasing* if |slope| ≥ **{crit.slope_threshold:g}** pts/yr{f' and p ≤ **{crit.alpha:g}**' if crit.require_significance else ''}; otherwise *Stable*.
- **Forecast**: linear trend, **{crit.horizon}** year(s) ahead, only when ≥ **{crit.min_points}** yearly points exist{' and the model beats the naive previous-year baseline in chronological walk-forward validation' if crit.require_baseline_win else ''}.
- **High Concern**: increasing trend and predicted rise ≥ **{crit.high_change:g}** pts.
- **Moderate Concern**: increasing trend with predicted rise ≥ **{crit.moderate_change:g}** pts; or increasing trend with no validated forecast; or latest resistance ≥ **{crit.high_level:g}%** while not decreasing.
- **Low Concern**: everything else. **Not assessed**: fewer than 3 yearly points.

These default thresholds are analytical conventions chosen for screening, not clinical cut-offs. Change them above and the whole dashboard updates.
""")


# ------------------------------------------------------------------ F. Data explorer
def explorer(filtered, full):
    st.title("Data Explorer & Data Quality")
    st.caption("Aggregated yearly surveillance data only. No patient-level or personally identifiable information is loaded or shown.")
    if _empty(filtered):
        return
    tab1, tab2 = st.tabs(["Data table", "Data quality & coverage"])
    with tab1:
        view = st.radio("Rows", ["Observed", "Observed + predicted"], horizontal=True)
        t = filtered.assign(Type="Observed")[["organism_short", "antibiotic", "year", "tested_n", "susceptible_n", "susceptible_pct",
                                              "resistant_n", "resistant_pct", "ci_low", "ci_high", "Type", "source_report_year",
                                              "source_table"]]
        t.columns = ["Organism", "Antibiotic", "Year", "Isolates tested", "Susceptible isolates", "Susceptible (%)",
                     "Non-susceptible isolates", RES, "95% CI low", "95% CI high", "Type", "Source report year", "Source table"]
        if view == "Observed + predicted":
            summary, results = analyse(filtered)
            rows = []
            for (o, a), r in results.items():
                for y, v, lo, hi in zip(r.forecast_years, r.forecast, r.lower, r.upper):
                    rows.append({"Organism": o, "Antibiotic": a, "Year": int(y), RES: round(float(v), 1),
                                 "95% CI low": round(float(lo), 1), "95% CI high": round(float(hi), 1), "Type": "Predicted"})
            if rows:
                t = pd.concat([t, pd.DataFrame(rows)], ignore_index=True)
            else:
                st.info("No combination in the current selection has a validated forecast.")
        q = st.text_input("Search organism or antibiotic")
        if q:
            mask = t["Organism"].str.contains(q, case=False, na=False) | t["Antibiotic"].str.contains(q, case=False, na=False)
            t = t[mask]
        t = t.sort_values(["Organism", "Antibiotic", "Year"])
        st.write(f"{len(t):,} rows")
        st.dataframe(t.round(1), hide_index=True)
        st.download_button("Download filtered results (CSV)", t.to_csv(index=False).encode(), "amr_resistance_filtered.csv", "text/csv")
        st.caption("Predicted rows are model output, not observations. Raw table columns 'Susceptible (%)' and "
                   "'Resistance (%)' always add to 100.")
    with tab2:
        try:
            q = dp.quality_report()
        except Exception as exc:
            st.error(f"Could not run quality checks: {exc}")
            return
        c = st.columns(4)
        c[0].metric("Rows in source file", q["rows"])
        c[1].metric("Duplicate organism-antibiotic-year", q["duplicate_keys"])
        c[2].metric("Percentages outside 0-100", q["pct_out_of_range"])
        c[3].metric("Susceptible > tested", q["n_inconsistent"])
        st.caption(f"Reported vs recomputed susceptible % differ by at most {q['max_mismatch']:.2f} pts "
                   f"({q['pct_mismatch']} rows exceed the {dp.PCT_TOLERANCE} pt rounding tolerance).")
        a, b = st.columns(2)
        with a:
            st.markdown("**Missing values (required columns)**")
            st.dataframe(q["missing"])
        with b:
            st.markdown("**Rows kept after validation**")
            st.write(f"{len(full):,} valid rows in the dashboard dataset; {len(filtered):,} match the current filters.")
        st.markdown("**Observation counts: years of data per combination**")
        cov = filtered.groupby(["organism_short", "antibiotic"])["year"].agg(["nunique", "min", "max"]).reset_index()
        cov.columns = ["Organism", "Antibiotic", "Years of data", "First year", "Last year"]
        st.dataframe(cov, hide_index=True)
        st.markdown("**Coverage: isolates tested by combination and year** (blank = no data)")
        piv = filtered.pivot_table(index=["organism_short", "antibiotic"], columns="year", values="tested_n", aggfunc="sum")
        st.dataframe(piv)
        st.caption("Combinations with fewer years than the minimum set on the Early Warning page are not forecast.")


# ------------------------------------------------------------------ E. Comparative
def _cached_fig(name, df, kw):
    return _CHARTS[name](df, **kw)


_CHARTS = {
    "bar_highest": ch.fig_bar_highest_resistance, "bar_org": ch.fig_bar_by_organism, "line_pair": ch.fig_line_pair,
    "line_orgs": ch.fig_line_organisms, "table_rising": ch.fig_table_rising, "heatmap": ch.fig_heatmap,
    "heatmap_years": ch.fig_heatmap_years, "treemap": ch.fig_treemap, "bubbles": ch.fig_packed_bubbles,
    "violin_org": ch.fig_violin_organism, "violin_year": ch.fig_violin_year,
}


@st.cache_resource(show_spinner="Drawing chart...", max_entries=40)
def _gallery_fig(name, df, kw_items):
    return _cached_fig(name, df, dict(kw_items))


def compare(filtered, full):
    st.title("Comparative Visualizations")
    if _empty(filtered):
        return
    view = st.radio("View", ["Interactive comparison", "Chart gallery"], horizontal=True)
    if view == "Chart gallery":
        _gallery(filtered)
        return

    years = sorted(filtered["year"].unique())
    tabs = st.tabs(["Organisms", "Antibiotics", "Years / periods", "Selected combinations"])
    thr = get_criteria().high_level

    with tabs[0]:
        orgs = sorted(filtered["organism_short"].unique())
        sel = st.multiselect("Organisms", orgs, default=orgs, key="cmp_o")
        d = filtered[filtered["organism_short"].isin(sel)]
        if d.empty:
            st.info("Select at least one organism.")
        else:
            a, b = st.columns(2)
            with a:
                m = _weighted_by(d, "organism_short")
                fig, ax = plt.subplots(figsize=(6, 4))
                _hbar(ax, m.index, m.values, [ch.ORG_COLORS[o] for o in m.index], xlabel="Resistance (%), weighted by isolates tested")
                ax.set_xlim(0, 100)
                ax.set_title("Average resistance, all selected years")
                _show(fig)
            with b:
                fig, ax = plt.subplots(figsize=(6, 4))
                for o, g in d.groupby("organism_short"):
                    s = g.groupby("year").apply(_wres, include_groups=False)
                    ax.plot(s.index, s.values, marker="o", color=ch.ORG_COLORS[o], label=o)
                _finish(ax, "Average resistance by year")
                ax.legend(frameon=False, fontsize=8)
                _show(fig)
            s = d.groupby("organism_short").agg(isolates=("tested_n", "sum"), antibiotics=("antibiotic", "nunique"),
                                                years=("year", "nunique")).join(d.groupby("organism_short").apply(_wres, include_groups=False).rename(RES).round(1))
            st.dataframe(s.reset_index().rename(columns={"organism_short": "Organism", "isolates": "Isolate-tests", "antibiotics": "Antibiotics", "years": "Years"}), hide_index=True)

    with tabs[1]:
        abxs = sorted(filtered["antibiotic"].unique())
        sel = st.multiselect("Antibiotics", abxs, default=abxs[:8], key="cmp_a")
        d = filtered[filtered["antibiotic"].isin(sel)]
        if d.empty:
            st.info("Select at least one antibiotic.")
        else:
            a, b = st.columns(2)
            with a:
                m = _weighted_by(d, "antibiotic")
                fig, ax = plt.subplots(figsize=(6, max(3.5, 0.35 * len(m))))
                _hbar(ax, m.index, m.values, th.NAVY, xlabel="Resistance (%), weighted by isolates tested")
                ax.set_xlim(0, 105)
                _show(fig)
            with b:
                fig, ax = plt.subplots(figsize=(6, 4.2))
                for i, (o, g) in enumerate(d.groupby("antibiotic")):
                    s = g.groupby("year").apply(_wres, include_groups=False)
                    ax.plot(s.index, s.values, marker="o", ms=4, color=plt.get_cmap("tab20")(i % 20), label=o)
                _finish(ax, "Average resistance by year")
                ax.legend(frameon=False, fontsize=7, ncol=2)
                _show(fig)
            hm = d.pivot_table(index="antibiotic", columns="organism_short", values="resistant_pct", aggfunc="mean").round(1)
            st.markdown("**Mean resistance (%) across selected years: antibiotic x organism**")
            st.dataframe(hm)

    with tabs[2]:
        if len(years) < 2:
            st.info("At least two years are needed to compare periods. Widen the Years filter.")
        else:
            c1, c2 = st.columns(2)
            y1 = c1.selectbox("From year", years, index=0)
            y2 = c2.selectbox("To year", years, index=len(years) - 1)
            a = filtered[filtered["year"] == y1].set_index(["organism_short", "antibiotic"])["resistant_pct"]
            b = filtered[filtered["year"] == y2].set_index(["organism_short", "antibiotic"])["resistant_pct"]
            t = pd.concat([a.rename(f"Resistance {y1} (%)"), b.rename(f"Resistance {y2} (%)")], axis=1).dropna().round(1)
            t["Change (pts)"] = (t.iloc[:, 1] - t.iloc[:, 0]).round(1)
            t = t.reset_index().rename(columns={"organism_short": "Organism", "antibiotic": "Antibiotic"})
            if y1 == y2 or t.empty:
                st.info("Choose two different years that share combinations.")
            else:
                d = pd.concat([t.nlargest(8, "Change (pts)"), t.nsmallest(8, "Change (pts)")]).drop_duplicates().sort_values("Change (pts)")
                fig, ax = plt.subplots(figsize=(9, max(3.5, 0.3 * len(d))))
                ax.barh(d["Organism"] + " / " + d["Antibiotic"], d["Change (pts)"],
                        color=[th.TREND_COLORS["Increasing"] if v > 0 else th.TREND_COLORS["Decreasing"] for v in d["Change (pts)"]])
                ax.axvline(0, color="black", lw=.8)
                ax.set_xlabel(f"Change in resistance, {y1} to {y2} (percentage points)")
                ax.set_title("Largest increases (red) and decreases (green)")
                ax.spines[["top", "right"]].set_visible(False)
                _show(fig)
                st.dataframe(t.sort_values("Change (pts)", ascending=False), hide_index=True)

    with tabs[3]:
        summary, _ = analyse(filtered)
        labs = list(summary["Organism"] + " / " + summary["Antibiotic"])
        sel = st.multiselect("Combinations to compare", labs, default=labs[:5], key="cmp_c")
        if not sel:
            st.info("Select at least one combination.")
        else:
            d = filtered.assign(lab=filtered["organism_short"] + " / " + filtered["antibiotic"])
            d = d[d["lab"].isin(sel)]
            a, b = st.columns(2)
            with a:
                last = d.sort_values("year").groupby("lab").tail(1).sort_values("resistant_pct")
                fig, ax = plt.subplots(figsize=(6, max(3, 0.4 * len(last))))
                _hbar(ax, last["lab"], last["resistant_pct"], th.NAVY)
                ax.set_xlim(0, 112)
                ax.set_title("Latest observed resistance")
                _show(fig)
            with b:
                fig, ax = plt.subplots(figsize=(6, 4))
                for i, (lab, g) in enumerate(d.groupby("lab")):
                    ax.plot(g["year"], g["resistant_pct"], marker="o", color=plt.get_cmap("tab10")(i % 10), label=lab)
                _finish(ax, "Observed resistance over time")
                ax.legend(frameon=False, fontsize=7)
                _show(fig)
            t = summary.assign(lab=summary["Organism"] + " / " + summary["Antibiotic"])
            t = t[t["lab"].isin(sel)].copy()
            t["High observed resistance"] = np.where(t["Latest resistance (%)"] >= thr, f">= {thr:g}%", "")
            t["Notable upward trend"] = np.where(t["Trend"] == "Increasing", "Yes", "")
            st.dataframe(t[["Organism", "Antibiotic", "Latest resistance (%)", "Trend", "Slope (pts/yr)", "Predicted resistance (%)",
                            "High observed resistance", "Notable upward trend"]], hide_index=True)
    st.caption("High observed resistance and upward trends are highlighted for surveillance only. Resistance percentages alone "
               "do not determine the most appropriate treatment.")


def _gallery(filtered):
    st.caption("All charts from the project's visualization unit, now drawn from the currently filtered data. "
               "Each chart shows Resistance (%) = 100 - susceptible (%).")
    years = sorted(filtered["year"].unique())
    orgs = sorted(filtered["organism"].unique())
    c = st.columns(3)
    year = c[0].selectbox("Year for single-year charts", years, index=len(years) - 1)
    org = c[1].selectbox("Organism for organism-specific charts", orgs,
                         index=orgs.index("Klebsiella pneumoniae") if "Klebsiella pneumoniae" in orgs else 0)
    abx_list = sorted(filtered["antibiotic"].unique())
    abx = c[2].selectbox("Antibiotic for organism-comparison line chart", abx_list,
                         index=abx_list.index("meropenem") if "meropenem" in abx_list else 0)

    def kw(**k):
        return tuple(sorted(k.items()))

    carb = tuple(a for a in ("meropenem", "imipenem", "ertapenem", "amikacin") if a in abx_list) or tuple(abx_list[:4])
    items = [
        ("1. Dimensions and measures", lambda: ch.fig_dimensions_measures()),
        ("2. Bar chart: highest-resistance pairs", lambda: _gallery_fig("bar_highest", filtered, kw(year=year))),
        ("3. Bar chart: resistance by organism", lambda: _gallery_fig("bar_org", filtered, kw(year=year))),
        ("4. Line chart: one organism, several antibiotics", lambda: _gallery_fig("line_pair", filtered, kw(organism=org, antibiotics=carb))),
        ("5. Line chart: one antibiotic, several organisms", lambda: _gallery_fig("line_orgs", filtered, kw(antibiotic=abx))),
        ("6. Table: rising resistance (<= 50% now)", lambda: _gallery_fig("table_rising", filtered, kw())),
        ("7. Heat map: antibiotic x organism", lambda: _gallery_fig("heatmap", filtered, kw(year=year))),
        ("8. Heat map: antibiotic x year", lambda: _gallery_fig("heatmap_years", filtered, kw(organism=org))),
        ("9. Treemap: Gram > organism > antibiotic", lambda: _gallery_fig("treemap", filtered, kw(year=year))),
        ("10. Packed bubble chart: most-tested pairs", lambda: _gallery_fig("bubbles", filtered, kw(year=year))),
        ("11. Interactive tooltip chart", None),
        ("12. Violin plot: by organism", lambda: _gallery_fig("violin_org", filtered, kw())),
        ("13. Violin plot: by year", lambda: _gallery_fig("violin_year", filtered, kw())),
    ]
    names = [n for n, _ in items]
    chosen = st.multiselect("Charts to show", names, default=names[1:3],
                            help="Charts are drawn on demand. Select all of them to see the full set.")
    if st.checkbox("Show all charts"):
        chosen = names
    for name, build in items:
        if name not in chosen:
            continue
        st.subheader(name)
        try:
            if build is None:
                components.html(vu.tooltip_html_string(filtered), height=620, scrolling=True)
            else:
                st.pyplot(build())
        except Exception as exc:
            st.info(f"This chart cannot be drawn with the current filters ({type(exc).__name__}: {exc}). Widen the filters.")


# ------------------------------------------------------------------ About
def about(filtered, full):
    st.title("About & Limitations")
    st.markdown(f"""
### What this dashboard does
It analyses yearly **antibiotic resistance** in Indian tertiary-care hospitals (ICMR-AMRSN annual reports, 2017-2024), shows trends for
each bacteria-antibiotic combination, forecasts resistance where the data support it and screens for combinations whose
resistance is rising.

<div class='note'>{th.DISCLAIMER}</div>

### How resistance is calculated
- The source tables report **susceptible isolates (n), isolates tested (n) and susceptible (%)**. The dashboard uses
  **Resistance (%) = 100 - susceptible (%)**, equivalently non-susceptible isolates / isolates tested.
- This conversion is only applied because all rows use the same definition (susceptible % = susceptible n / tested n; verified on every
  row, maximum rounding difference {dp.quality_report()['max_mismatch']:.2f} pts).
- **Assumption:** the reports do not list *intermediate* results separately, so "resistance" here includes intermediate isolates.
  It is therefore *non-susceptibility* and can be higher than resistance as defined by a strict resistant-only count.
- Missing values are never treated as 0% resistance. Rows with invalid counts or percentages are dropped, and later report
  editions replace earlier values for the same organism, antibiotic and year.
- Colistin is excluded because its published figures are intermediate percentages, not susceptibility.

### Forecasting pipeline
1. Load and validate data, then compute resistance. 2. One value per organism-antibiotic-year. 3. Require enough yearly points.
4. Fit a transparent linear trend per combination. 5. **Chronological walk-forward validation**: each held-out year is predicted using only earlier
years, so the future is never used to predict the past. 6. Compare against a naive "same as last year" baseline and forecast only where the
trend model is not worse. 7. Show forecasts beside observed values with an approximate range (forecast +/- 1.96 x validation RMSE).

### Limitations
- Only about 8 yearly points per combination, so forecasts are indicative and uncertain. The model has not been shown to be accurate
  beyond the held-out comparison reported for each combination (typical errors are several percentage points).
- Hospital surveillance data, not community data. Participating centres, case-mix and testing practice may change over time.
- Linear trends cannot anticipate sudden changes (new clones, policy changes, reporting changes).
- Categories (Low / Moderate / High Concern) depend on adjustable thresholds and are screening aids, not clinical risk classes.
- No patient-level data are used or displayed in this dashboard.
""", unsafe_allow_html=True)
    st.caption("Source: ICMR-AMRSN annual reports 2023 and 2024 (see source_url in the Data Explorer download).")
