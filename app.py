"""
app.py — Entry point. Routing e sidebar.
"""
import streamlit as st
from config import CSS, BUDGET_DEFAULT, C
from auth import check_auth, render_login, render_auth_sidebar

st.set_page_config(
    page_title="Investment Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CSS, unsafe_allow_html=True)

role = check_auth()
if role is None:
    render_login()
    st.stop()

is_admin = role == "admin"

st.sidebar.title("📈 Dashboard")
render_auth_sidebar(is_admin)

if "budget" not in st.session_state:
    st.session_state["budget"] = BUDGET_DEFAULT
st.sidebar.number_input("Monthly Budget (€)", min_value=0.0,
                         step=50.0, format="%.0f", key="budget")
budget = st.session_state["budget"]

st.sidebar.markdown("---")
page = st.sidebar.radio("Navigate", [
    "💼 My Portfolio",
    "📊 Metrics",
    "🔍 Screening",
    "🔬 Scenario Builder",
    "🌍 Macro & News",
])

if page == "💼 My Portfolio":
    from pages.page_portfolio import render
    render(is_admin, budget)

elif page == "📊 Metrics":
    from pages.page_metrics import render
    render(budget)

elif page == "🔍 Screening":
    from pages.page_screening import render
    render(is_admin)

elif page == "🔬 Scenario Builder":
    from pages.page_scenario import render
    render(budget)

elif page == "🌍 Macro & News":
    from pages.page_macro import render
    render()

st.sidebar.markdown("---")
st.sidebar.caption("Yahoo Finance · FRED · ECB  |  Not financial advice.")
