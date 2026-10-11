"""One function per chart (all based on Resistance (%) = 100 - % susceptible).
Each returns a matplotlib Figure so the notebook and make_charts.py share the same code."""
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import cm, colors

try:
    from . import viz_utils as vu   # when imported as part of the Streamlit app (src package)
except ImportError:
    import viz_utils as vu           # when run as a script: python src/make_charts.py

RES_CMAP = "YlOrRd"   # sequential: pale yellow = low resistance, dark red = high resistance
ORG_COLORS = dict(zip(vu.SHORT.values(), ["#1f77b4", "#d62728", "#2ca02c", "#ff7f0e", "#9467bd", "#8c564b"]))
ORG_COLORS = __import__("collections").defaultdict(lambda: "#7f7f7f", ORG_COLORS)  # unknown organisms get grey
ABBR = {"piperacillin-tazobactam": "pip-tazo", "ciprofloxacin": "cipro", "cotrimoxazole": "cotrimox.",
        "erythromycin": "erythro.", "levofloxacin": "levoflox.", "ceftazidime": "ceftaz.", "clindamycin": "clinda."}


def ab(name):
    return ABBR.get(name, name)


def _year(trends, year):
    return trends[trends["year"] == year]


# 1. Dimensions and measures --------------------------------------------------
DIM_MEASURE_TABLE = pd.DataFrame([
    ["organism", "Dimension", "Categorical (nominal)", "Which bacterium was tested"],
    ["antibiotic", "Dimension", "Categorical (nominal)", "Which drug it was tested against"],
    ["year", "Dimension", "Ordered (temporal)", "Report year, 2017 to 2024"],
    ["gram (derived)", "Dimension", "Categorical", "Gram-positive or Gram-negative group"],
    ["tested_n", "Measure", "Quantitative", "Number of isolates tested"],
    ["susceptible_n", "Measure", "Quantitative", "Number of isolates that were susceptible"],
    ["susceptible_pct", "Measure", "Quantitative", "susceptible_n / tested_n x 100"],
    ["resistant_pct (derived)", "Measure", "Quantitative", "100 - susceptible_pct (main measure in this unit)"],
    ["change_per_year (derived)", "Measure", "Quantitative", "Slope of resistant_pct against year"],
], columns=["Field", "Role", "Data type", "Meaning"])


def fig_dimensions_measures():
    t = DIM_MEASURE_TABLE
    fig, ax = plt.subplots(figsize=(11, 4.4))
    ax.axis("off")
    tb = ax.table(cellText=t.values, colLabels=t.columns, loc="center", cellLoc="left", colWidths=[0.22, 0.1, 0.22, 0.46])
    tb.auto_set_font_size(False)
    tb.set_fontsize(9.5)
    tb.scale(1, 1.55)
    for (r, cidx), cell in tb.get_celld().items():
        if r == 0:
            cell.set_facecolor("#2b4c7e")
            cell.set_text_props(color="white", weight="bold")
        elif t.iloc[r - 1]["Role"] == "Dimension":
            cell.set_facecolor("#e8f0fb")
        else:
            cell.set_facecolor("#fdf0e0")
    ax.set_title("Dimensions (blue rows) and measures (orange rows) in the AMR trend data", pad=12)
    fig.tight_layout()
    return fig


# 2. Bar chart ----------------------------------------------------------------
def fig_bar_highest_resistance(trends, year=2024, n=12):
    d = _year(trends, year).copy()
    d["pair"] = d["organism_short"] + " / " + d["antibiotic"]
    d = d.nlargest(n, "resistant_pct").sort_values("resistant_pct")
    fig, ax = plt.subplots(figsize=(9, 5.2))
    bars = ax.barh(d["pair"], d["resistant_pct"], color=[ORG_COLORS[o] for o in d["organism_short"]])
    for b, v in zip(bars, d["resistant_pct"]):
        ax.text(v + 0.5, b.get_y() + b.get_height() / 2, f"{v:.1f}%", va="center", fontsize=9)
    ax.set_xlabel("Resistance (%)")
    ax.set_xlim(0, 112)
    ax.set_title(f"Bar chart: {n} organism-antibiotic pairs with the highest resistance, {year}")
    present = [o for o in ORG_COLORS if o in d["organism_short"].values]
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=ORG_COLORS[o]) for o in present], labels=present,
              loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=len(present), frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def fig_bar_by_organism(trends, year=2024):
    """Mean Resistance (%) per organism, weighted by isolates tested."""
    d = _year(trends, year)
    m = d.groupby("organism_short").apply(lambda g: np.average(g["resistant_pct"], weights=g["tested_n"]), include_groups=False)
    m = m.sort_values()
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.barh(m.index, m.values, color=[ORG_COLORS[o] for o in m.index])
    for b, v in zip(bars, m.values):
        ax.text(v + 0.8, b.get_y() + b.get_height() / 2, f"{v:.1f}%", va="center", fontsize=9)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Resistance (%), weighted by isolates tested")
    ax.set_title(f"Bar chart: average resistance by organism, {year}")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


# 3. Line chart ---------------------------------------------------------------
def fig_line_pair(trends, organism="Klebsiella pneumoniae", antibiotics=("meropenem", "imipenem", "ertapenem", "amikacin")):
    d = trends[(trends["organism"] == organism) & (trends["antibiotic"].isin(antibiotics))]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    for name, g in d.groupby("antibiotic"):
        g = g.sort_values("year")
        ax.plot(g["year"], g["resistant_pct"], marker="o", label=name)
        ax.annotate(f"{g['resistant_pct'].iloc[-1]:.0f}%", (g["year"].iloc[-1], g["resistant_pct"].iloc[-1]),
                    textcoords="offset points", xytext=(6, -3), fontsize=9)
    ax.set_xlabel("Year")
    ax.set_ylabel("Resistance (%)")
    ax.set_title(f"Line chart: {vu.SHORT.get(organism, organism)} resistance over time")
    ax.legend(frameon=False)
    ax.grid(alpha=.3)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def fig_line_organisms(trends, antibiotic="meropenem"):
    d = trends[trends["antibiotic"] == antibiotic]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    for o, g in d.groupby("organism_short"):
        g = g.sort_values("year")
        ax.plot(g["year"], g["resistant_pct"], marker="o", color=ORG_COLORS[o], label=o)
    ax.set_xlabel("Year")
    ax.set_ylabel("Resistance (%)")
    ax.set_title(f"Line chart: {antibiotic} resistance by organism")
    ax.legend(frameon=False)
    ax.grid(alpha=.3)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


# 4. Table ----------------------------------------------------------------------
def risk_table(trends, min_years=6):
    rows = []
    for (o, a), g in trends.groupby(["organism_short", "antibiotic"]):
        g = g.sort_values("year")
        if len(g) < min_years:
            continue
        slope = np.polyfit(g["year"], g["resistant_pct"], 1)[0]
        rows.append([o, a, g["resistant_pct"].iloc[0], g["resistant_pct"].iloc[-1], slope, int(g["tested_n"].iloc[-1])])
    return pd.DataFrame(rows, columns=["Organism", "Antibiotic", "First year %", "Latest %", "Change per year (pts)", "Tested (latest)"])


def fig_table_rising(trends, n=10):
    t = risk_table(trends)
    t = t[t["Latest %"] <= 50].nlargest(n, "Change per year (pts)").round(1)   # not yet above 50Resistance (%), but rising fastest
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.axis("off")
    tb = ax.table(cellText=t.values, colLabels=t.columns, loc="center", cellLoc="center")
    tb.auto_set_font_size(False)
    tb.set_fontsize(9.5)
    tb.scale(1, 1.5)
    for (r, cidx), cell in tb.get_celld().items():
        if r == 0:
            cell.set_facecolor("#2b4c7e")
            cell.set_text_props(color="white", weight="bold")
        elif cidx == 4:
            cell.set_facecolor("#f8d7d7")
    ax.set_title(f"Table: {n} pairs at or below 50Resistance (%) in 2024 whose resistance is rising fastest", pad=10)
    fig.tight_layout()
    return fig


# 5. Heat map -------------------------------------------------------------------
def fig_heatmap(trends, year=2024):
    p = _year(trends, year).pivot(index="antibiotic", columns="organism_short", values="resistant_pct")
    p = p.loc[p.mean(axis=1).sort_values(ascending=False).index]
    fig, ax = plt.subplots(figsize=(8.5, 8))
    im = ax.imshow(p.values, cmap=RES_CMAP, vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(p.shape[1]), p.columns, rotation=30, ha="right")
    ax.set_yticks(range(p.shape[0]), p.index)
    for i in range(p.shape[0]):
        for j in range(p.shape[1]):
            v = p.values[i, j]
            if np.isnan(v):
                ax.text(j, i, "-", ha="center", va="center", color="#999")
            else:
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8, color="white" if v > 65 else "black")
    fig.colorbar(im, ax=ax, label="Resistance (%)", shrink=0.7)
    ax.set_title(f"Heat map: Resistance (%), antibiotic x organism, {year}\n(blank = not reported)")
    fig.tight_layout()
    return fig


def fig_heatmap_years(trends, organism="Klebsiella pneumoniae"):
    d = trends[trends["organism"] == organism].pivot(index="antibiotic", columns="year", values="resistant_pct")
    d = d.loc[d.mean(axis=1).sort_values(ascending=False).index]
    fig, ax = plt.subplots(figsize=(8, 0.35 * len(d) + 2))
    im = ax.imshow(d.values, cmap=RES_CMAP, vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(d.shape[1]), d.columns)
    ax.set_yticks(range(d.shape[0]), d.index)
    for i in range(d.shape[0]):
        for j in range(d.shape[1]):
            v = d.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8, color="white" if v > 65 else "black")
    fig.colorbar(im, ax=ax, label="Resistance (%)", shrink=0.8)
    ax.set_title(f"Heat map over time: {vu.SHORT.get(organism, organism)}, antibiotic x year")
    fig.tight_layout()
    return fig


# 6. Treemap ----------------------------------------------------------------------
def fig_treemap(trends, year=2024, top_per_org=6):
    """Hierarchy: Gram group > organism > antibiotic. Area = isolates tested, colour = Resistance (%)."""
    d = _year(trends, year).sort_values("tested_n", ascending=False).groupby("organism_short").head(top_per_org)
    fig, ax = plt.subplots(figsize=(12, 7.5))
    norm = colors.Normalize(0, 100)
    cmap = matplotlib.colormaps[RES_CMAP]
    W, H = 100, 60
    groups = d.groupby("gram")["tested_n"].sum().sort_values(ascending=False)
    for (gname, _), (gx, gy, gw, gh) in zip(groups.items(), vu.squarify(groups.values, 0, 0, W, H)):
        og = d[d["gram"] == gname].groupby("organism_short")["tested_n"].sum().sort_values(ascending=False)
        for (oname, _), (ox, oy, ow, oh) in zip(og.items(), vu.squarify(og.values, gx, gy, gw, gh)):
            leaf = d[d["organism_short"] == oname].sort_values("tested_n", ascending=False)
            for row, (lx, ly, lw, lh) in zip(leaf.itertuples(), vu.squarify(leaf["tested_n"].values, ox, oy, ow, oh)):
                ax.add_patch(plt.Rectangle((lx, ly), lw, lh, facecolor=cmap(norm(row.resistant_pct)), edgecolor="white", lw=1))
                if lw > 6 and lh > 4:
                    ax.text(lx + lw / 2, ly + lh / 2, f"{ab(row.antibiotic)}\n{row.resistant_pct:.0f}%", ha="center", va="center",
                            fontsize=7.5, color="white" if row.resistant_pct > 65 else "black")
            ax.add_patch(plt.Rectangle((ox, oy), ow, oh, fill=False, edgecolor="black", lw=1.8))
            ax.text(ox + 0.8, oy + 1.6, oname, fontsize=10, weight="bold", va="top",
                    bbox=dict(facecolor="white", alpha=.8, pad=1.5, edgecolor="none"))
        ax.add_patch(plt.Rectangle((gx, gy), gw, gh, fill=False, edgecolor="black", lw=3.5))
        ax.text(gx + gw - 0.8, gy + gh - 0.8, gname.upper(), ha="right", va="bottom", fontsize=9, weight="bold",
                bbox=dict(facecolor="black", edgecolor="none", pad=2.5), color="white")
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")
    fig.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax, shrink=0.6, label="Resistance (%)")
    ax.set_title(f"Treemap: Gram group > organism > antibiotic, {year}\n(area = isolates tested, colour = Resistance (%); top {top_per_org} antibiotics per organism)")
    fig.tight_layout()
    return fig


# 7. Packed bubble -----------------------------------------------------------------
def fig_packed_bubbles(trends, year=2024, n=40):
    d = _year(trends, year).nlargest(n, "tested_n").reset_index(drop=True)
    radii = np.sqrt(d["tested_n"].values)
    radii = radii / radii.max() * 10
    pos = vu.pack_circles(radii)
    fig, ax = plt.subplots(figsize=(10, 8.5))
    cmap = matplotlib.colormaps[RES_CMAP]
    for (x, y), r, row in zip(pos, radii, d.itertuples()):
        ax.add_patch(plt.Circle((x, y), r, facecolor=cmap(row.resistant_pct / 100), edgecolor="white", lw=1.2))
        if r > 4.2:
            ax.text(x, y, f"{row.organism_short}\n{ab(row.antibiotic)}\n{row.resistant_pct:.0f}%", ha="center", va="center",
                    fontsize=6.5, color="white" if row.resistant_pct > 65 else "black")
    lim = np.max(np.abs(pos)) + 11
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.colorbar(cm.ScalarMappable(norm=colors.Normalize(0, 100), cmap=cmap), ax=ax, shrink=0.6, label="Resistance (%)")
    ax.set_title(f"Packed bubble chart: {n} most-tested pairs, {year}\n(bubble area = isolates tested, colour = Resistance (%))")
    fig.tight_layout()
    return fig


# 8. Violin plot -------------------------------------------------------------------
def fig_violin_organism(trends):
    """Distribution of Resistance (%) across all antibiotic-year values of each organism."""
    order = trends.groupby("organism_short")["resistant_pct"].median().sort_values().index
    fig, ax = plt.subplots(figsize=(10, 5.5))
    sns.violinplot(data=trends, x="organism_short", y="resistant_pct", order=order, hue="organism_short", palette=ORG_COLORS,
                   inner="quartile", cut=0, legend=False, ax=ax)
    sns.stripplot(data=trends, x="organism_short", y="resistant_pct", order=order, color="black", size=2, alpha=.35, ax=ax)
    ax.set_xlabel("")
    ax.set_ylabel("Resistance (%)")
    ax.set_ylim(-3, 103)
    ax.set_title("Violin plot: spread of Resistance (%) per organism\n(each dot = one antibiotic in one year; lines inside = quartiles)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def fig_violin_year(trends):
    fig, ax = plt.subplots(figsize=(10, 5.2))
    sns.violinplot(data=trends, x="year", y="resistant_pct", color="#f4a582", inner="quartile", cut=0, ax=ax)
    med = trends.groupby("year")["resistant_pct"].median()
    ax.plot(range(len(med)), med.values, color="#b2182b", marker="o", lw=1.5, label="median")
    ax.set_xlabel("Year")
    ax.set_ylabel("Resistance (%)")
    ax.set_ylim(-3, 103)
    ax.set_title("Violin plot: spread of Resistance (%) across all pairs, by year")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig
