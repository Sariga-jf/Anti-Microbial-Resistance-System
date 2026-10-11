# Data Visualization: Antibiotic Resistance Trend Predictor

All charts are made by `python src/make_charts.py` and saved in `outputs/charts/`. They use `data/processed/clean_trends.csv` (ICMR-AMRSN annual reports, 2017 to 2024; 466 rows, 6 organisms, 24 antibiotics). Every chart is based on **% resistant**.

**Note on "% resistant".** The reports publish % susceptible. Resistance here is calculated as 100 - % susceptible, so it also includes the small share of intermediate results, which the reports do not publish separately (README, limitation 3).

---

## 1. Introduction to data visualization

Data visualization turns data into shapes, positions and colours so that people can see patterns that a table of numbers hides. Each value is drawn with a **mark** (a bar, line, point, area or cell) and a **channel** (position, length, area or colour). Some channels are read more accurately than others: position and length are the most accurate, while area and colour are less exact, so they are used for overview rather than precise comparison.

A good visualization has a clear question, the right chart type for that question, an honest scale, labelled axes with units, and a title that says what to look at.

**Question for this project:** *which bacteria-antibiotic combinations have high resistance, and which are getting worse?* This matches the project goal of finding resistance patterns early. The trend table has 466 rows, which is hard to read but quick to scan as a heat map or treemap.

## 2. Introduction to dimensions and measures

- A **dimension** is a category used to group, slice or label the data. It answers "which one?" or "when?".
- A **measure** is a number that can be added, averaged or compared. It answers "how much?".

| Field | Role | Data type | Meaning |
|---|---|---|---|
| organism | Dimension | Categorical | Which bacterium |
| antibiotic | Dimension | Categorical | Which drug |
| year | Dimension | Ordered | 2017 to 2024 |
| gram (derived) | Dimension | Categorical | Gram-positive or Gram-negative |
| tested_n | Measure | Quantitative | Isolates tested |
| susceptible_n | Measure | Quantitative | Isolates susceptible |
| susceptible_pct | Measure | Quantitative | susceptible_n / tested_n x 100 |
| resistant_pct (derived) | Measure | Quantitative | 100 - susceptible_pct |
| change_per_year (derived) | Measure | Quantitative | Slope of resistant_pct against year |

**How they are used:** dimensions go on the axes, rows, columns or groups; measures become length, area, height or colour. Example: in the heat map, antibiotic and organism (dimensions) are the rows and columns, and % resistant (measure) is the colour. Figure: `01_dimensions_measures_table.png`; also saved as `outputs/dimensions_measures.csv`.

---

## 3. Bar chart

**What it is:** one bar per category, with bar length showing the measure. **Why use it:** length on a common baseline is the most accurate way to compare categories, so it is the best choice when exact comparison matters.

- `02_bar_highest_resistance_pairs.png`: the 12 pairs with the highest resistance in 2024.
- `03_bar_resistance_by_organism.png`: average resistance per organism, weighted by isolates tested.

**Findings (2024):** MRSA with oxacillin and cefoxitin is 100% resistant, which is how MRSA is defined. Among the others, *A. baumannii* leads with imipenem (91.6%), cefepime (91.1%) and meropenem (91.0%). By organism, *A. baumannii* averages 82.6% resistance, *K. pneumoniae* 70.6%, *E. coli* 56.0%, MRSA 50.9%, *P. aeruginosa* 36.4% and *S. aureus* 31.5%.

## 4. Line chart

**What it is:** points joined in order of time. **Why use it:** a line shows direction and speed of change, so it is the standard chart for trends.

- `04_line_klebsiella_drugs.png`: *K. pneumoniae* resistance to four antibiotics, 2017 to 2024.
- `05_line_meropenem_by_organism.png`: meropenem resistance for each organism.

**Findings:** *K. pneumoniae* resistance to meropenem rose from 51.9% in 2017 to 64.9% in 2024, with the steepest rise after 2020 (52.9% in 2020 to 62.4% in 2023). *A. baumannii* meropenem resistance was already high in 2017 and has stayed above 77% since.

## 5. Table

**What it is:** exact values in rows and columns. **Why use it:** when the reader needs the actual numbers, a table is more precise than any shape.

- `06_table_rising_resistance.png` and `outputs/resistance_trend_table.csv`.

The table gives the first-year %, latest %, the change in percentage points per year (slope of a straight line fitted to the years), and the number tested. The picture shows pairs that are still at or below 50% resistant in 2024 but rising fastest. These are the early-warning candidates for this project: *E. coli* imipenem (18.6% to 42.4%, about +2.6 points a year), *S. aureus* oxacillin (28.3% to 48.0%) and *P. aeruginosa* imipenem (26.4% to 43.1%). Across all 58 pairs with at least 6 years of data, 44 have a rising trend.

## 6. Heat map

**What it is:** a grid of cells where colour shows the measure. **Why use it:** it shows a measure across two dimensions at once, so a large grid can be scanned in seconds.

- `07_heatmap_antibiotic_organism_2024.png`: antibiotic x organism for 2024. Darker red means higher resistance. A dash means the pair is not reported.
- `08_heatmap_klebsiella_over_years.png`: antibiotic x year for *K. pneumoniae*.

**Findings:** the darkest block is *A. baumannii* with carbapenems and cephalosporins (about 88% to 92%), followed by *E. coli* and *K. pneumoniae* with ciprofloxacin (89% and 80%). Rows near the bottom (vancomycin, teicoplanin, tigecycline, linezolid) are pale, so these drugs still work in the groups reported.

## 7. Treemap

**What it is:** nested rectangles whose area shows a measure. It suits hierarchical data. **Why use it:** it shows part-to-whole and a hierarchy in one picture.

- `09_treemap_gram_organism_antibiotic.png`: hierarchy Gram group > organism > antibiotic. Area is the number of isolates tested and colour is % resistant (top six antibiotics per organism, 2024). The layout uses a squarified treemap algorithm written for this project (`src/viz_utils.py`).

**Findings:** Gram-negative organisms make up 78% of the isolates tested in 2024. The largest dark-red areas sit inside *A. baumannii* and *K. pneumoniae*, so the problem is both widespread and heavily tested.

## 8. Packed bubble chart

**What it is:** circles packed together with area showing a measure. **Why use it:** it shows size and a second measure (colour) compactly, without the rigid grid of a treemap.

- `10_packed_bubble_most_tested.png`: the 40 most-tested pairs in 2024. Bubble area is isolates tested, colour is % resistant.

**Findings:** the most-tested pairs include amikacin in *K. pneumoniae* and *E. coli* and ciprofloxacin in *E. coli*. The dark-red bubbles are mostly *A. baumannii* and ciprofloxacin pairs. Bubbles are harder to compare exactly than bars, so use the bar chart or table for exact values. The circle packing is also written for this project, and the notebook checks that no circles overlap.

## 9. Tooltip

**What it is:** a small box that appears when the pointer hovers over a mark. **Why use it:** it keeps the chart clean while exact values are one hover away (details on demand).

- `11_tooltip_interactive.html`: open it in any browser (no internet needed). Choose an antibiotic from the drop-down, then hover over a point to see organism, year, % resistant, number tested and number not susceptible.

## 10. Violin plot

**What it is:** a mirrored density curve showing how values are spread. The wider the shape, the more values lie at that level. Lines inside mark the quartiles (25th, 50th and 75th percentiles), and dots show the individual values. **Why use it:** a bar of averages hides the spread, but a violin shows whether values are bunched together or split into groups.

- `12_violin_by_organism.png`: % resistant per organism. Each dot is one antibiotic in one year.
- `13_violin_by_year.png`: % resistant across all pairs for each year, with the median shown as a line.

**Findings:** *A. baumannii* is compressed near the top (median 86.4%), so almost every drug is weak against it. MRSA stretches from 0% to 100% (some drugs work completely, others not at all), and *E. coli* has two humps, one around 30% and one above 80%, so their averages hide large differences between antibiotics. *P. aeruginosa* is narrow (about 26% to 53%), so its resistance is moderate across drugs. The median resistance of all pairs rose from 40.7% in 2017 to 55.5% in 2024, with the largest step in 2022.

---

## Limitations

- The data are national summaries from a hospital network, so they do not describe resistance in the community.
- % resistant is 100 - % susceptible and includes intermediate results.
- Area and colour are weaker channels than length and position, so exact comparisons should use the bar chart or table.
- Violin plots pool all antibiotics and years of an organism, so each dot is a pair-year, not a patient.
