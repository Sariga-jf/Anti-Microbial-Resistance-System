"""Antibiotic Resistance Trend Predictor (resistance-based).  Run with:  python -m streamlit run app.py"""
import streamlit as st

from src import pages
from src.data_processing import DataError, load_trends
from src.theme import CSS

st.set_page_config(page_title="Antibiotic Resistance Trend Predictor", page_icon="🧪", layout="wide", initial_sidebar_state="expanded")
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner="Loading data...")
def get_data():
    return load_trends()


try:
    full = get_data()
except DataError as err:
    st.error(f"The dashboard cannot start because the data could not be loaded.\n\n{err}")
    st.stop()

PAGES = {
    "Overview": pages.overview,
    "Comparative Visualizations": pages.compare,
}
ALL_ORGS = sorted(full["organism_short"].unique())
ALL_ABX = sorted(full["antibiotic"].unique())
YEAR_MIN, YEAR_MAX = int(full["year"].min()), int(full["year"].max())


def reset_filters():
    st.session_state.update(f_orgs=ALL_ORGS, f_abx=ALL_ABX, f_years=(YEAR_MIN, YEAR_MAX), f_minn=30)


for key, default in [("f_orgs", ALL_ORGS), ("f_abx", ALL_ABX), ("f_years", (YEAR_MIN, YEAR_MAX)), ("f_minn", 30)]:
    st.session_state.setdefault(key, default)

with st.sidebar:
    st.markdown("## AMR Trends")
    page = st.radio("Navigate", list(PAGES), label_visibility="collapsed")
    st.markdown("---")
    st.markdown("**Filters** (apply to every page)")
    orgs = st.multiselect("Organism", ALL_ORGS, key="f_orgs")
    abx = st.multiselect("Antibiotic", ALL_ABX, key="f_abx")
    years = st.slider("Years", YEAR_MIN, YEAR_MAX, key="f_years")
    min_n = st.slider("Minimum isolates tested", 0, 500, step=10, key="f_minn",
                      help="Hides results based on fewer isolates than this. Very small samples give unreliable percentages.")
    st.button("Reset filters", on_click=reset_filters)

filtered = full[full["organism_short"].isin(orgs) & full["antibiotic"].isin(abx)
                & full["year"].between(*years) & (full["tested_n"] >= min_n)]

with st.sidebar:
    st.caption(f"{len(filtered):,} of {len(full):,} records selected")

PAGES[page](filtered, full)
