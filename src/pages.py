"""Streamlit pages (Overview and Comparative Visualizations). Every page receives (filtered, full): `filtered` already
reflects the sidebar filters and is the only data used for metrics, charts and tables. `full` is kept for a consistent page
signature. Resistance (%) = 100 - susceptible (%): see src/data_processing.py.
The dashboard is descriptive: it shows observed resistance only (no trend labels, forecasts or risk categories)."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from . import charts as ch
from . import data_processing as dp
from . import theme as th
from . import viz_utils as vu

plt.rcParams["figure.max_open_warning"] = 0
RES = "Resistance (%)"
FIGSIZE = (9, 4.6)
HIGH_RESISTANCE = 70.0   # latest observed resistance (%) flagged as "high" in the Selected combinations table


# ------------------------------------------------------------------ helpers
def _show(fig):
    st.pyplot(fig)
    plt.close(fig)


def _empty(filtered) -> bool:
    if filtered.empty:
        st.warning("No records match the current filters. Widen the filters in the sidebar (or lower 'Minimum isolates tested').")
        return True
    return False


def _wres(g: pd.DataFrame) -> float:
    return dp.weighted_resistance(g)


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


# ------------------------------------------------------------------ A. Overview
def overview(filtered, full):
    st.title("Antibiotic Resistance Trend Predictor")
    st.caption("Indian ICMR-AMRSN hospital surveillance data, yearly. Primary metric: " + RES)
    if _empty(filtered):
        return
    n_combos = len(filtered[["organism_short", "antibiotic"]].drop_duplicates())

    c = st.columns(4)
    c[0].metric("Overall resistance", f"{dp.weighted_resistance(filtered):.1f}%", help="Non-susceptible isolates / isolates tested, all selected rows.")
    c[1].metric("Bacteria analysed", filtered["organism"].nunique())
    c[2].metric("Antibiotics analysed", filtered["antibiotic"].nunique())
    c[3].metric("Bacteria-antibiotic combinations", n_combos)
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
    thr = HIGH_RESISTANCE

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
        pairs = filtered[["organism_short", "antibiotic"]].drop_duplicates().sort_values(["organism_short", "antibiotic"])
        labs = list(pairs["organism_short"] + " / " + pairs["antibiotic"])
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
            t = last.rename(columns={"organism_short": "Organism", "antibiotic": "Antibiotic"}).copy()
            t["Latest resistance (%)"] = t["resistant_pct"].round(1)
            t["High observed resistance"] = np.where(t["Latest resistance (%)"] >= thr, f">= {thr:g}%", "")
            st.dataframe(t.sort_values(["Organism", "Antibiotic"])[["Organism", "Antibiotic", "Latest resistance (%)",
                                                                    "High observed resistance"]], hide_index=True)
    st.caption("High observed resistance is highlighted for surveillance only. Resistance percentages alone "
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
