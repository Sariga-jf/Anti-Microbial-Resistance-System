# Visualization Workflow, Periodic Table and Visualization Selection

**Part of:** Data Visualization unit (CO4)
**Read with:** `docs/visualization_notes.md` (chart notes) and `docs/data_task_abstraction.md` (data and task analysis).

---

## 1. Workflow followed in this project

The same steps were used for every chart.

| Step | What is done | Where in the repo |
|---|---|---|
| 1. Question | Decide what the viewer should learn | `docs/data_task_abstraction.md`, sections 3 and 4 |
| 2. Acquire | Load the ICMR sample tables and the yearly trend file | `notebooks/amr_analysis.ipynb`, Parts 2 and 7 |
| 3. Clean | Fix dates, text, duplicates, names and missing values | `notebooks/amr_analysis.ipynb`, Parts 3, 4 and 7; saved in `data/processed/` |
| 4. Derive | Create the fields that are drawn (`resistant_pct`, `gram`, `change_per_year`) | `src/viz_utils.py` |
| 5. Choose a representation | Match data type and task to a chart family | `docs/data_task_abstraction.md`, section 5 |
| 6. Draw | Build each chart in code | `src/charts.py`, run by `src/make_charts.py`; shown in `notebooks/amr_visualization.ipynb` |
| 7. Check and refine | Read each chart back against its task; fix labels, scales and colour | `docs/visualization_notes.md` (findings and limitations) |

**Output:** 12 PNG charts and one interactive tooltip chart in `outputs/charts/`, regenerated in about 5 seconds.

### Rules applied while drawing

- Every chart uses **% resistant**, and the notes explain how it is calculated.
- Exact comparison uses position and length (bar chart, table); area and colour are used only for overview.
- Axes are labelled with the measure and unit, and each chart has a title that says what to look at.
- Pairs that are not reported are shown as blanks, not as zero.

---

## 2. Visualization periodic table and visualization selection

In this course the periodic table is a **metaphor**. The chemical periodic table organizes many elements into one structured, understandable layout, and the same idea can organize data science concepts, techniques and tools. The practical use is **visualization selection**: a chart should be chosen by the question being asked.

The table below applies the course's selection rules to this project.

| Question | Suitable visualization (course) | Used in this project |
|---|---|---|
| Which category is largest? | Bar chart | 02, 03 bar charts |
| How does something change over time? | Line chart | 04, 05 line charts; 08 heat map by year |
| What is the distribution? | Histogram / box plot | 12, 13 violin plots (a violin shows the shape that a box plot hides); histogram and box plot of patient age in `notebooks/amr_analysis.ipynb` |
| Are two variables related? | Scatter plot | Not used in the charts so far |
| How is a total divided? | Pie chart | One pie chart of test results in `notebooks/amr_analysis.ipynb`; the charts use bars and a treemap instead because lengths compare more accurately than angles |
| How is hierarchical data organized? | Treemap | 09 treemap (Gram group, organism, antibiotic); 10 packed bubble |
| Where does something occur? | Map | Not used: the data has no location column |
| What are the exact values? | Table | 06 table; 11 tooltip |

Two rows have no chart in the project, scatter plot and map, and each has a reason:
- **Scatter plot:** none of the questions here compares two measures directly. One could be added, for example % resistant against number tested per pair.
- **Map:** neither dataset has a location (see `docs/data_task_abstraction.md`, section 5).

The heat map (07, 08) is not in the course's selection table. It answers "how does a measure vary across two categories at once?", so it is used for the overview task (T5).

---

## 3. Summary

1. Start from the viewer's question, not from a chart.
2. Describe the data and tasks in generic terms.
3. Match each task to a chart family and a strong visual channel.
4. Check every level, and state what the data cannot show (relational and spatial).
