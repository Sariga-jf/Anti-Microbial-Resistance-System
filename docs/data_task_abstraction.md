# Data Abstraction, Task Abstraction and the Four Levels of Validation

**Part of:** Data Visualization unit (CO4)
**Framework:** Munzner's nested model (*Visualization Analysis and Design*)
**Read with:** `docs/visualization_notes.md`, which describes each chart and its findings, and gives the dimensions and measures table.

---

## 1. Why this document exists

`visualization_notes.md` explains each chart. This document explains **why those charts were chosen**: what the data is in generic terms (data abstraction), what the viewer wants to do (task abstraction), and how each design decision can be checked (four levels of validation).

---

## 2. Data abstraction

Both sources are **tables**: one row per item, one column per attribute. Neither is a network, tree, field or geometry dataset.

### 2.1 Yearly national trends (`data/processed/clean_trends.csv`)

All charts in `visualization_notes.md` use this file.

| Item | Value |
|---|---|
| Dataset type | Table |
| Size | 466 rows, 6 organisms, 24 antibiotics |
| Time span | 2017 to 2024 |
| Key | `organism` + `antibiotic` + `year` |

| Attribute | Type | Role |
|---|---|---|
| `organism`, `antibiotic` | Categorical | Dimension |
| `year` | Temporal, ordered | Dimension |
| `tested_n`, `susceptible_n`, `susceptible_pct` | Quantitative | Measure |
| `source_report_year`, `source_table`, `source_url` | Categorical (provenance) | Not plotted; kept for traceability |

For the full dimensions and measures table, including derived fields, see section 2 of `visualization_notes.md`.

### 2.2 ICMR sample data (`data/processed/clean_results.csv`)

| Item | Value |
|---|---|
| Dataset type | Table |
| Size | 129 rows, 16 samples, collected Feb to Dec 2023 |
| Key | `sample_id` + `organism` + `antibiotic` |

| Attribute | Type |
|---|---|
| `organism`, `antibiotic` | Categorical |
| `remarks` | **Ordinal** (1 Susceptible, 2 Intermediate, 3 Resistant) |
| `collection_date`, `month` | Temporal |
| `is_resistant` | Derived, binary (1 if `remarks` is 3) |

This file is not used in the charts. It is a very small sample and is only used for the cleaning and EDA part of the project.

## 2.3 Derived attributes

| Attribute | Type | Where | How it is made |
|---|---|---|---|
| `gram` | Categorical | Charts | Gram-positive or Gram-negative group assigned to each organism (see `src/viz_utils.py`) |
| `resistant_pct` | Quantitative | Charts | 100 - `susceptible_pct` |
| `change_per_year` | Quantitative | Charts | Slope of `resistant_pct` against year. **Positive means worse** |
| `change_per_year` (forecast) | Quantitative | `amr_analysis_full_backup.ipynb` | Slope of `susceptible_pct` against year. **Negative means worse** |
| `latest_pct`, `forecast_2025` | Quantitative | `amr_analysis_full_backup.ipynb` | Latest year and one-year-ahead line, as % **susceptible** |
| `trend`, `status` | Ordinal | `amr_analysis_full_backup.ipynb` | Falling fast / Falling / Stable or rising; Below 40% / 40% or above |
| `risk` | Ordinal | `amr_analysis_full_backup.ipynb` | Low < Medium < High |

> **Sign convention warning.** The forecasting notebook (`notebooks/amr_analysis_full_backup.ipynb`) fits its trend line to % **susceptible**, so a **negative** `change_per_year` means worse. The charts in `visualization_notes.md` use % **resistant**, so a **positive** `change_per_year` means worse. Any dashboard that shows both should label which one it is.

### 2.4 Properties that affect design

- % resistant is 100 minus % susceptible, so it includes intermediate results (the reports do not publish them separately).
- About 8 yearly values per pair, so trends are indications, not proof.
- `tested_n` varies widely, so a percentage from a small number of tests should not be read as precisely as one from a large number.
- There is no location column, so no spatial chart is possible (section 5).

---

### 3. Task abstraction

The project's guiding question is: *which bacteria-antibiotic combinations have high resistance, and which are getting worse?* It has two parts:

- **Part A, high resistance now:** which pairs and organisms are the most resistant?
- **Part B, getting worse:** which pairs are rising, and which are rising from a still-moderate level?

Each task below is a generic action on a target (the "why" and "what" of Munzner's framework) that helps answer one or both parts.

| # | Question the viewer has | Part of project question | Action | Target | Charts that serve it |
|---|---|---|---|---|---|
| T1 | What is the exact resistance for this pair? | A and B | Lookup | One value | 06 table, 11 tooltip |
| T2 | Which pairs or organisms are most resistant? | A | Compare | Values across categories | 02, 03 bar charts |
| T3 | Is resistance rising or falling over time? | B | Identify | Trend | 04, 05 line charts, 08 heat map over years, 13 violin by year |
| T4 | Which pairs are still moderate but rising fastest? | B | Identify | Extreme trends | 06 table |
| T5 | What does the whole picture look like? | A | Summarize | Overview of two dimensions or a hierarchy | 07 heat map, 09 treemap, 10 packed bubble |
| T6 | How spread out are the values within a group? | A and B | Summarize | Distribution | 12 violin by organism, 13 violin by year |

`notebooks/amr_visualization.ipynb` opens with the guiding question, and its findings answer the two parts: bar chart and violin plot for Part A, line chart, table and violin plot for Part B. The action and target labels are Munzner's terms, applied by us to the finished charts.

---

## 4. Four levels of validation

Each level feeds the next, so an error at the top is passed down to everything below it.

| Level | Question | Main threat | How it is handled in this project |
|---|---|---|---|
| 1. Domain situation | Who is the user and what do they need? | Solving a problem nobody has | The intended users are people who work on antimicrobial stewardship and infection control, who need to know which drugs are losing effectiveness. The guiding question, *which bacteria-antibiotic combinations have high resistance, and which are getting worse?*, comes from the project goal of finding resistance patterns early. It has not yet been checked with a real user |
| 2. Data and task abstraction | Right data, right tasks? | Wrong data or tasks | The charts use the yearly national trend data, which has the organism, antibiotic and year needed to answer both parts of the question. Every chart except 01 (the dimensions and measures table, which explains the data) serves at least one task in section 3 |
| 3. Visual encoding and interaction | Can people read it correctly? | Misleading or confusing chart | Chosen from perceptual principles: position and length are used where exact comparison matters (bar chart, table); area and colour, which are less precise, are used for overview (treemap, bubble, heat map). A tooltip gives exact values, and the notes state each chart's limits. It has not yet been tested with viewers |
| 4. Algorithm | Is the code correct and fast? | Wrong result or slow code | `make_charts.py` regenerates every chart in about 5 seconds, and the circle packing is checked in the notebook to make sure no circles overlap |

---

## 5. Data representation: chart families

| Family | Supported by the data? | Charts in the repo |
|---|---|---|
| Categorical | Yes | 02, 03 bar; 06 table; 07 heat map; 12 violin by organism |
| Temporal | Yes | 04, 05 line; 08 heat map by year; 13 violin by year |
| Hierarchical | Yes | 09 treemap (Gram group, organism, antibiotic); 10 packed bubble (size comparison) |
| Relational | Not directly | None. The data has no links between entities. An antibiotic-by-antibiotic correlation matrix could be derived, but it is not in the repo |
| Spatial | **No** | None. Neither dataset has a location. The patient table has `state` for only 10 patients, which is too few for a map |

Stating why relational and spatial are missing is part of the analysis. Choosing a chart family should follow the data, not the other way round.

---

## 6. Link to the dashboard

The dashboard panels should follow the tasks in section 3, so that each panel answers a question the viewer actually has. The dashboard is built separately; see the README for its status.

---

## 7. Known data notes

1. `clean_results.csv` has trailing spaces in some organism names, which breaks matching with the trends file.
2. The README says 478 rows after cleaning, but the file and `visualization_notes.md` say 466. The README should be updated.
3. Organism and antibiotic names differ between the two files (for example cotrimoxazole and trimethoprim-sulfamethoxazole), so joining them needs a mapping table.
