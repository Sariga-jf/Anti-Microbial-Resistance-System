"""Run:  python src/make_charts.py   ->  writes every chart to outputs/charts/"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import charts as c
import viz_utils as vu

vu.CHARTS.mkdir(parents=True, exist_ok=True)
trends = vu.load_trends()

JOBS = [
    ("01_dimensions_measures_table", lambda: c.fig_dimensions_measures()),
    ("02_bar_highest_resistance_pairs", lambda: c.fig_bar_highest_resistance(trends)),
    ("03_bar_resistance_by_organism", lambda: c.fig_bar_by_organism(trends)),
    ("04_line_klebsiella_drugs", lambda: c.fig_line_pair(trends)),
    ("05_line_meropenem_by_organism", lambda: c.fig_line_organisms(trends)),
    ("06_table_rising_resistance", lambda: c.fig_table_rising(trends)),
    ("07_heatmap_antibiotic_organism_2024", lambda: c.fig_heatmap(trends)),
    ("08_heatmap_klebsiella_over_years", lambda: c.fig_heatmap_years(trends)),
    ("09_treemap_gram_organism_antibiotic", lambda: c.fig_treemap(trends)),
    ("10_packed_bubble_most_tested", lambda: c.fig_packed_bubbles(trends)),
    ("12_violin_by_organism", lambda: c.fig_violin_organism(trends)),
    ("13_violin_by_year", lambda: c.fig_violin_year(trends)),
]
for name, make in JOBS:
    fig = make()
    fig.savefig(vu.CHARTS / f"{name}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("saved", name)

vu.tooltip_html(trends, vu.CHARTS / "11_tooltip_interactive.html")
c.DIM_MEASURE_TABLE.to_csv(vu.ROOT / "outputs" / "dimensions_measures.csv", index=False)
c.risk_table(trends).round(2).to_csv(vu.ROOT / "outputs" / "resistance_trend_table.csv", index=False)
print("saved tooltip html + csv tables")
