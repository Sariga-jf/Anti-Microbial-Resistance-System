"""Dashboard theme: CSS injected once by app.py. Colours follow the chart palette used throughout the project
(navy table headers #2b4c7e, light-blue/orange panels, YlOrRd resistance scale)."""

NAVY, LIGHT_BLUE, LIGHT_ORANGE = "#2b4c7e", "#e8f0fb", "#fdf0e0"
TREND_COLORS = {"Increasing": "#d62728", "Decreasing": "#2ca02c", "Stable": "#7f7f7f", "Insufficient data": "#bbbbbb"}
RISK_COLORS = {"High Concern": "#d62728", "Moderate Concern": "#ff7f0e", "Low Concern": "#2ca02c", "Not assessed": "#bbbbbb"}
OBSERVED_COLOR, FORECAST_COLOR = "#2b4c7e", "#d62728"

CSS = f"""
<style>
.block-container {{padding-top: 2rem; padding-bottom: 2rem;}}
h1, h2, h3 {{color: {NAVY};}}
[data-testid="stMetric"] {{background: {LIGHT_BLUE}; border-radius: 8px; padding: 10px 14px; border-left: 4px solid {NAVY};}}
[data-testid="stMetricLabel"] {{color: #333;}}
[data-testid="stMetricValue"] {{color: {NAVY};}}
[data-testid="stSidebar"] {{background: #f4f6fa;}}
.note {{background: {LIGHT_ORANGE}; border-left: 4px solid #ff7f0e; border-radius: 6px; padding: 10px 14px; font-size: 0.9rem;}}
.legend-dot {{display:inline-block; width:11px; height:11px; border-radius:50%; margin-right:5px;}}
@media (max-width: 800px) {{ .block-container {{padding: 1rem;}} }}
</style>
"""

DISCLAIMER = ("Analytical screening categories for research and surveillance support only. They are not confirmed clinical "
              "risk classifications and are not a substitute for clinical judgment. Resistance percentages alone do not "
              "determine the most appropriate treatment.")
RESISTANCE_NOTE = ("Resistance (%) = 100 - susceptible (%). The ICMR reports publish susceptible percentages only, so this "
                   "counts all non-susceptible isolates (resistant + intermediate).")
