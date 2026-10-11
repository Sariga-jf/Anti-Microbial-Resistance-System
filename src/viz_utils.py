"""Helpers for the AMR visualization unit: data loading, treemap layout,
circle packing and a self-contained HTML tooltip chart. "Resistant %" = 100 - susceptible %.
Only pandas, numpy and matplotlib are needed for the static charts."""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
CHARTS = ROOT / "outputs" / "charts"

SHORT = {
    "Escherichia coli": "E. coli", "Klebsiella pneumoniae": "K. pneumoniae",
    "Acinetobacter baumannii": "A. baumannii", "Pseudomonas aeruginosa": "P. aeruginosa",
    "Staphylococcus aureus": "S. aureus", "MRSA": "MRSA",
}
GRAM = {  # category used for hierarchy: Gram stain -> organism -> antibiotic
    "Escherichia coli": "Gram-negative", "Klebsiella pneumoniae": "Gram-negative",
    "Acinetobacter baumannii": "Gram-negative", "Pseudomonas aeruginosa": "Gram-negative",
    "Staphylococcus aureus": "Gram-positive", "MRSA": "Gram-positive",
}


def load_trends():
    d = pd.read_csv(PROCESSED / "clean_trends.csv")
    d["organism_short"] = d["organism"].map(SHORT)
    d["gram"] = d["organism"].map(GRAM)
    d["resistant_pct"] = 100 - d["susceptible_pct"]  # includes intermediate, see README limitation 3
    return d


# ---------------------------------------------------------------- treemap
def squarify(values, x, y, w, h):
    """Squarified treemap layout (Bruls et al.). values must be sorted descending.
    Returns a list of (x, y, w, h) rectangles in the same order as values."""
    values = [float(v) for v in values]
    total = sum(values)
    scale = w * h / total
    areas = [v * scale for v in values]
    rects = []

    def worst(row, side):
        s = sum(row)
        return max(max(side * side * r / (s * s), s * s / (side * side * r)) for r in row)

    def layout_row(row, x, y, w, h):
        s = sum(row)
        if w >= h:  # lay the row along the left edge (vertical strip)
            rw = s / h
            yy = y
            for r in row:
                rects.append((x, yy, rw, r / rw))
                yy += r / rw
            return x + rw, y, w - rw, h
        rh = s / w  # lay the row along the top edge (horizontal strip)
        xx = x
        for r in row:
            rects.append((xx, y, r / rh, rh))
            xx += r / rh
        return x, y + rh, w, h - rh

    row = []
    i = 0
    while i < len(areas):
        side = min(w, h)
        a = areas[i]
        if not row or worst(row + [a], side) <= worst(row, side):
            row.append(a)
            i += 1
        else:
            x, y, w, h = layout_row(row, x, y, w, h)
            row = []
    if row:
        layout_row(row, x, y, w, h)
    return rects


# ---------------------------------------------------------- packed bubbles
def pack_circles(radii, seed=0, iterations=400):
    """Simple circle packing: start on a spiral, pull circles towards the centre while
    pushing overlapping ones apart, then run extra passes with no pull until nothing overlaps.
    Returns an array of (x, y) centres."""
    rng = np.random.default_rng(seed)
    n = len(radii)
    radii = np.asarray(radii, dtype=float)
    gap = 0.02 * radii.mean()
    ang = np.arange(n) * 2.399963  # golden angle
    dist = np.sqrt(np.arange(n) + 0.5) * radii.mean() * 1.2
    pos = np.c_[dist * np.cos(ang), dist * np.sin(ang)] + rng.normal(0, 1e-3, (n, 2))

    def resolve():
        worst = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                d = pos[j] - pos[i]
                dd = math.hypot(*d) or 1e-9
                need = radii[i] + radii[j] + gap
                if dd < need:
                    worst = max(worst, need - dd)
                    push = (need - dd) / 2 * d / dd
                    pos[i] -= push
                    pos[j] += push
        return worst

    for _ in range(iterations):
        pos *= 0.99  # gravity towards the origin
        resolve()
    for _ in range(2000):  # final clean-up: no gravity, stop when no overlap remains
        if resolve() < 1e-6:
            break
    return pos


# ----------------------------------------------------------- tooltip chart
def tooltip_html_string(trends):
    """Writes a self-contained interactive HTML file (no libraries, works offline):
    one line per organism for a chosen antibiotic (Resistance %), with a hover tooltip."""
    data = {}
    for ab, g in trends.groupby("antibiotic"):
        data[ab] = {}
        for org, gg in g.groupby("organism_short"):
            gg = gg.sort_values("year")
            data[ab][org] = [[int(r.year), float(r.resistant_pct), int(r.tested_n), int(r.tested_n - r.susceptible_n)]
                             for r in gg.itertuples()]
    return TOOLTIP_TEMPLATE.replace("__DATA__", json.dumps(data))


def tooltip_html(trends, path):
    """Write the tooltip chart to a standalone .html file."""
    Path(path).write_text(tooltip_html_string(trends), encoding="utf-8")


TOOLTIP_TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>AMR tooltip visualization</title>
<style>
body{font-family:system-ui,sans-serif;margin:24px;max-width:900px}
select{font-size:15px;padding:4px}
#tip{position:fixed;pointer-events:none;background:#222;color:#fff;padding:8px 10px;border-radius:6px;
font-size:13px;line-height:1.45;display:none;box-shadow:0 2px 8px rgba(0,0,0,.3)}
.legend span{display:inline-block;margin-right:14px;font-size:13px}
.legend i{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:5px;vertical-align:-1px}
</style></head><body>
<h2>Resistance (%) by year (ICMR-AMRSN, 2017-2024)</h2>
<p>Pick an antibiotic, then hover over any point to see the organism, year, number tested and number not susceptible.</p>
<label>Antibiotic: <select id="ab"></select></label>
<div class="legend" id="legend" style="margin:10px 0"></div>
<svg id="chart" width="860" height="440"></svg>
<div id="tip"></div>
<script>
const DATA = __DATA__;
const COLORS = ["#1f77b4","#d62728","#2ca02c","#ff7f0e","#9467bd","#8c564b"];
const M = {l:55,r:20,t:15,b:40}, W=860, H=440, svg=document.getElementById("chart"), tip=document.getElementById("tip");
const sel=document.getElementById("ab");
Object.keys(DATA).sort().forEach(a=>{const o=document.createElement("option");o.value=o.textContent=a;sel.appendChild(o)});
sel.value = DATA["meropenem"] ? "meropenem" : sel.options[0].value;
function el(n,a,p){const e=document.createElementNS("http://www.w3.org/2000/svg",n);for(const k in a)e.setAttribute(k,a[k]);(p||svg).appendChild(e);return e}
function draw(){
  svg.innerHTML=""; const d=DATA[sel.value], orgs=Object.keys(d).sort();
  const x=y=>M.l+(y-2017)/7*(W-M.l-M.r), vals=orgs.flatMap(o=>d[o].map(p=>p[1]));
  const lo=Math.max(0,Math.floor((Math.min(...vals)-5)/10)*10), hi=Math.min(100,Math.ceil((Math.max(...vals)+5)/10)*10);
  const yy=v=>H-M.b-(v-lo)/(hi-lo)*(H-M.t-M.b);
  for(let v=lo;v<=hi;v+=10){el("line",{x1:M.l,x2:W-M.r,y1:yy(v),y2:yy(v),stroke:"#ddd"});
    el("text",{x:M.l-8,y:yy(v)+4,"text-anchor":"end","font-size":12,fill:"#555"}).textContent=v+"%";}
  for(let y=2017;y<=2024;y++)el("text",{x:x(y),y:H-M.b+20,"text-anchor":"middle","font-size":12,fill:"#555"}).textContent=y;
  document.getElementById("legend").innerHTML=orgs.map((o,i)=>`<span><i style="background:${COLORS[i%6]}"></i>${o}</span>`).join("");
  orgs.forEach((o,i)=>{
    const pts=d[o]; el("polyline",{points:pts.map(p=>x(p[0])+","+yy(p[1])).join(" "),fill:"none",stroke:COLORS[i%6],"stroke-width":2});
    pts.forEach(p=>{const c=el("circle",{cx:x(p[0]),cy:yy(p[1]),r:5,fill:COLORS[i%6],stroke:"#fff","stroke-width":1.5});
      c.addEventListener("mousemove",e=>{tip.style.display="block";tip.style.left=(e.clientX+14)+"px";tip.style.top=(e.clientY+14)+"px";
        tip.innerHTML=`<b>${o}</b> - ${sel.value}<br>Year: ${p[0]}<br>Resistance: ${p[1].toFixed(1)}%<br>Tested: ${p[2].toLocaleString()}<br>Not susceptible isolates: ${p[3].toLocaleString()}`});
      c.addEventListener("mouseleave",()=>tip.style.display="none");});
  });
}
sel.addEventListener("change",draw); draw();
</script></body></html>
"""
