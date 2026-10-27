"""Executive Overview: headline KPIs, revenue trend, top categories and states."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # dashboard/pages/<file> -> project root
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from dashboard.components import charts, queries  # noqa: E402
from dashboard.components.brazil_map import tile_map  # noqa: E402
from dashboard.components.data import DashboardDataError  # noqa: E402
from dashboard.components.definitions import DEFINITIONS, INCOMPLETE_NOTE  # noqa: E402
from dashboard.components.ui import (  # noqa: E402
    date_str,
    incomplete_months,
    money_short,
    num,
    pct,
    show_chart,
    show_error,
    show_table,
)

st.title("Executive Overview")

try:
    with st.spinner("Loading data..."):
        summary_df = queries.summary()
        monthly = queries.monthly_kpis()
        categories = queries.categories()
        states = queries.states()
except DashboardDataError as exc:
    show_error(exc)
    st.stop()

if summary_df.empty or monthly.empty:
    st.error("The KPI tables are empty. Re-run `dbt build`.")
    st.stop()
summary = summary_df.iloc[0]

window = f"{date_str(summary['window_start'])} to {date_str(summary['window_end'])}"
through = date_str(summary["data_complete_through"])
st.info(
    f"Window {window}. Purchases are fully captured only through {through}. "
    "All figures are delivered orders, in BRL."
)

row1 = st.columns(4)
row1[0].metric(
    "Delivered revenue", money_short(summary["delivered_revenue"]), help=DEFINITIONS["revenue"]
)
row1[1].metric("Delivered orders", num(summary["delivered_orders"]), help=DEFINITIONS["orders"])
row1[2].metric("Average order value", f"R$ {summary['aov']:,.2f}", help=DEFINITIONS["aov"])
row1[3].metric("Customers", num(summary["customers"]), help=DEFINITIONS["customers"])
row2 = st.columns(4)
row2[0].metric("Repeat rate", pct(summary["repeat_rate_pct"], 2), help=DEFINITIONS["repeat_rate"])
row2[1].metric("On-time delivery", pct(summary["on_time_pct"], 1), help=DEFINITIONS["on_time"])
row2[2].metric(
    "Avg delivery time",
    f"{summary['avg_delivery_days']:.1f} days",
    help=DEFINITIONS["delivery_days"],
)
row2[3].metric(
    "Avg review score", f"{summary['avg_review_score']:.2f} / 5", help=DEFINITIONS["review"]
)

st.subheader("Revenue trend")
show_chart(
    charts.monthly_bars(monthly, "delivered_revenue", "Delivered revenue by month", "BRL"),
    key="rev",
)
flagged = incomplete_months(monthly)
if flagged:
    st.caption(f"Grey bar(s): {', '.join(flagged)}. {INCOMPLETE_NOTE}")

left, right = st.columns(2)
with left:
    show_chart(charts.customers_new_vs_returning(monthly), key="cust")
    st.caption(
        "Most customers each month are new: growth comes from acquisition more than repeat buying."
    )
with right:
    show_chart(
        charts.monthly_line(monthly, "aov", "Average order value by month", "BRL"), key="aov"
    )

st.subheader("Where the revenue comes from")
left, right = st.columns(2)
with left:
    show_chart(charts.top_categories(categories.head(10)), key="topcat")
with right:
    show_chart(
        tile_map(
            states,
            "revenue_share_pct",
            "Revenue share (%)",
            "{:.1f}%",
            hover_cols={"delivered_revenue": "Revenue (BRL)", "delivered_orders": "Orders"},
        ),
        key="statemap",
    )
    st.caption("Each square is a state, placed roughly where it is on the map.")

with st.expander("Top 10 states by revenue"):
    show_table(
        states.head(10)[
            ["state", "delivered_revenue", "revenue_share_pct", "delivered_orders", "on_time_pct"]
        ],
        formats={"delivered_revenue": "%.0f", "revenue_share_pct": "%.2f", "on_time_pct": "%.1f"},
    )
