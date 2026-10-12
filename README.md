# Antibiotic Resistance Trend Predictor 

**Author:** Sariga Joseph Fredy,S Sreya

**Course:** Data Science, B.Tech Computer Science and Engineering, Mar Baselios College of Engineering and Technology



**Part covered in this README:** Steps 1 and 2 of structured thinking -Problem Identification and Data Collection  

**Course outcome:** 

CO1 -explain the fundamental concepts in data science
CO2 - Statistical Analysis of data
CO3 - EDA

---

## 1. Introduction

Antibiotic resistance is a growing healthcare problem. When bacteria stop responding to a drug, infections become harder to treat, and these changes are often noticed only after the drug has already stopped working. This project uses Indian surveillance data to find bacteria-antibiotic combinations where susceptibility is falling while the drug still works, forecasts their direction, and shows them in an early-warning dashboard.

**Tools:** Python, Pandas, NumPy, Matplotlib, Scikit-learn, Streamlit

---

## 2. Step 1: Problem Identification

### Problem statement

Antibiotic resistance makes common infections harder to treat, and changes in resistance are often noticed only after a drug has stopped working. This project uses Indian surveillance data to find bacteria-antibiotic combinations where susceptibility is falling while the drug still works, forecast their direction, and present them as an early-warning dashboard.

### Objectives

1. Clean and explore Indian antibiotic susceptibility data.
2. Measure how susceptibility to each antibiotic changes from year to year for each bacterium.
3. Forecast the next year's value with a simple, explainable model, and test how good that forecast is.
4. Flag combinations that still work but are getting worse.
5. Present the results in an interactive dashboard.

### Expected outcome

An early-warning table that gives, for each bacteria-antibiotic pair, the trend (change per year), a forecast for 2025, and a risk label, shown with charts on a Streamlit dashboard.

### Data science concepts used

- **Linear algebra:** data held as tables (matrices) of rows and columns.
- **Statistics:** counts, percentages, group summaries, and comparing predictions with actual values.
- **Optimisation:** linear regression finds the line that minimises the squared error (least squares).

---

## 3. Step 2: Data Collection

### Sources used

| # | Source | Type | Size | Used for |
|---|---|---|---|---|
| 1 | ICMR sample dataset (4 Stata `.dta` tables) and its metadata PDF, from the ICMR data repository | Structured, patient-level | 10 patients, 14 hospital visits, 16 samples, 140 test results (Feb to Dec 2023) | Practising data cleaning and EDA, and showing the pipeline |
| 2 | ICMR-AMRSN annual reports (2022, 2023, 2024 editions), through the `amr-tracker` GitHub project | Structured, yearly summaries | 1,286 raw rows; 478 rows after cleaning; 2017 to 2024 | Trends, forecasting and the dashboard |

### Source 1: ICMR sample dataset

Four linked tables, joined through ID columns:

| Table | One row is | Key columns |
|---|---|---|
| Patients | one patient | `patient_id`, age, gender, state |
| Hospital visits | one admission | `hospital_patient_rel_id`, ward type, infection type |
| Samples | one sample collected | `sample_id`, collection date, sample type |
| AMR results | one antibiotic tested on one organism | antibiotic, organism, test type, value, result |

The result code is `remarks`: 1 = Susceptible, 2 = Intermediate, 3 = Resistant. The metadata PDF from the same page explains every code.

**Important:** the ICMR portal says the raw dataset is not shared, only query outcomes. The files available for download are a sample, which is why it is small.

### Source 2: Yearly trend data

The `amr-tracker` project on GitHub (by Yashita Thakur) extracts the national trend tables from the ICMR-AMRSN annual reports into a CSV file. Each row holds an organism, an antibiotic, a year, the number tested, the number susceptible, and the percentage susceptible. Six organisms are covered: *E. coli*, *K. pneumoniae*, *A. baumannii*, *P. aeruginosa*, *S. aureus* and MRSA.

This is an unofficial extraction of the original reports. The original ICMR annual reports are the authoritative source.

### Structured and unstructured data

| Kind | Where it appears |
|---|---|
| Structured | IDs, dates, age, ward type, test results, yearly counts and percentages |
| Unstructured (free text) | `clinical_diagnosis`, `comorbidity`, `devices_used`, `prescribed_antibiotic` (comma-separated text that has to be converted into 0/1 columns before analysis) |

---

## 4. Limitations of the data

1. **Hospital data, not community data.** The records come from tertiary-care hospitals, so they do not describe resistance in the general population.
2. **The sample is very small.** 17 bacteria-sample rows come from only 10 patients, so group comparisons from it are descriptions, not proven findings.
3. **Percent susceptible, not percent resistant.** The yearly reports do not publish the percentage of intermediate results, so a resistant percentage cannot be calculated from them.
4. **Few time points.** About 8 yearly values per pair limits how accurate a forecast can be.
5. **Revised figures.** Later report editions sometimes revise earlier years, so only the newest edition is kept for each year.
6. **Colistin excluded.** Its reported figures are intermediate percentages, not susceptibility.

---

## 5. Files

| File | What it is |
|---|---|
| `README.md` | This document |
| `notebooks/amr_analysis.ipynb` | Analysis notebook covering CO1 to CO3 (setup, cleaning, EDA, descriptive statistics, trend data cleaning). Run it from top to bottom with Restart and Run All |
| `notebooks/amr_analysis_full_backup.ipynb` | Earlier version of the notebook, kept as a backup (includes the forecasting and early-warning work) |
| `clean_results.csv` | Cleaned patient-level results from the ICMR sample |
| `clean_trends.csv` | Cleaned yearly trend data, one row per organism, antibiotic and year |
| `alerts.csv` | Early-warning table with trend, 2025 forecast and risk label |
| `app.py` | Streamlit dashboard |

---

## 6. Data visualization

Charts for the data visualization unit, based on **% resistant** (100 minus % susceptible, so it also includes intermediate results). Topics: introduction to data visualization, introduction to dimensions and measures, bar chart, line chart, table, heat map, treemap, packed bubble, tooltip and violin plot.

| File | What it is |
|---|---|
| `docs/visualization_notes.md` | Introduction, dimensions and measures, and notes and findings for each chart |
| `notebooks/amr_visualization.ipynb` | Notebook that draws every chart (Restart and Run All) |
| `src/viz_utils.py` | Data loading, own treemap layout, own circle packing, tooltip HTML writer |
| `src/charts.py` | One function per chart |
| `src/make_charts.py` | Regenerates everything in `outputs/charts/` (about 5 seconds) |
| `outputs/charts/` | 12 PNG charts and the interactive tooltip chart `11_tooltip_interactive.html` |
| `outputs/dimensions_measures.csv`, `outputs/resistance_trend_table.csv` | Field roles, and the resistance trend for each pair |

## 7. Sources and citations

- ICMR National Health Research Data Repository: Antimicrobial Resistance Surveillance Network sample dataset and AMR metadata.
- ICMR-AMRSN Annual Reports, 2022 (6th), 2023 (7th) and 2024 (8th) editions.
- `yashita-thakur/amr-tracker` on GitHub: structured extraction of the ICMR-AMRSN and NCDC NARS-Net annual reports (code under the MIT licence; see `DATA_LICENSE.md` in that repository for the data terms).

---


---

## Resistance-based dashboard (Streamlit)

Run: `python -m streamlit run app.py`

- **Metric:** Resistance (%) = 100 - susceptible (%) (non-susceptible, includes intermediate; see limitation 3).
- **Pages:** Overview (summary tiles, distribution and yearly resistance trend of observed data) and Comparative Visualizations (interactive comparison plus the full chart gallery).
- **Modules:** `src/data_processing.py` (loading, validation, resistance), `src/pages.py`, `src/theme.py`, plus `src/charts.py` and `src/viz_utils.py`.
- **Descriptive only:** the dashboard shows observed resistance. It has no forecasting, machine-learning model, trend labels or risk categories. The only fixed threshold is the "high observed resistance" flag (latest resistance of 70% or more) in the Selected combinations table, set as `HIGH_RESISTANCE` in `src/pages.py`.
- Research and surveillance support only, not a substitute for clinical judgment.
