"""Retail Analytics & Demand Forecasting: dashboard entry point.

Run from the project root:  streamlit run dashboard/app.py

This file only sets up navigation (so pages get clean names in the sidebar) and shows a small
data-status block under the page filters. All content lives in dashboard/pages/.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # dashboard/app.py -> project root
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from dashboard.components import queries  # noqa: E402
from dashboard.components.data import DashboardDataError  # noqa: E402
from dashboard.components.ui import date_str  # noqa: E402

st.set_page_config(page_title="Retail Analytics", page_icon="🛒", layout="wide")

if not hasattr(st, "navigation"):
    st.error("This dashboard needs Streamlit 1.36 or newer. Run: pip install --upgrade streamlit")
    st.stop()


def render_status() -> None:
    """A compact data-status block at the bottom of the sidebar. Never raises."""
    with st.sidebar:
        st.divider()
        st.caption("**Data status**")
        try:
            summary = queries.summary().iloc[0]
        except (DashboardDataError, IndexError):
            return  # the page itself shows what is wrong
        st.caption(
            f"Window: {date_str(summary['window_start'])} to {date_str(summary['window_end'])}"
        )
        st.caption(f"Purchases complete through: {date_str(summary['data_complete_through'])}")
        try:
            run = queries.forecast_run().iloc[0]
            st.caption(f"Forecast generated: {run['run_at_utc']} UTC")
        except (DashboardDataError, IndexError):
            st.caption("Forecast: not generated yet")
        st.caption("BRL, delivered orders. Definitions are in the metric tooltips.")


pages = [
    st.Page("pages/1_Executive_Overview.py", title="Executive Overview", icon="📊", default=True),
    st.Page("pages/2_Category_Drilldown.py", title="Category Drill-down", icon="🔎"),
    st.Page("pages/3_Delivery_Performance.py", title="Delivery Performance", icon="🚚"),
    st.Page("pages/4_Forecast.py", title="Forecast", icon="📈"),
]
current_page = st.navigation(pages)
current_page.run()
render_status()
