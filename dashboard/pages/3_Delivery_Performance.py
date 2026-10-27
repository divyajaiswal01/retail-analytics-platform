"""Delivery Performance: on-time delivery, impact on reviews, regions and sellers."""

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
    incomplete_months,
    pct,
    show_chart,
    show_error,
    show_table,
)

st.title("Delivery Performance")

try:
    with st.spinner("Loading data..."):
        summary_df = queries.summary()
        monthly = queries.monthly_kpis()
        impact = queries.delivery_impact()
        repeat = queries.delivery_vs_repeat()
        states = queries.states()
        sellers = queries.sellers()
except DashboardDataError as exc:
    show_error(exc)
    st.stop()

if summary_df.empty or monthly.empty:
    st.error("The KPI tables are empty. Re-run `dbt build`.")
    st.stop()
summary = summary_df.iloc[0]

cols = st.columns(4)
cols[0].metric("On-time delivery", pct(summary["on_time_pct"]), help=DEFINITIONS["on_time"])
cols[1].metric(
    "Late deliveries", pct(100 - summary["on_time_pct"]), help="100% minus the on-time rate."
)
cols[2].metric(
    "Avg delivery time",
    f"{summary['avg_delivery_days']:.1f} days",
    help=DEFINITIONS["delivery_days"],
)
cols[3].metric(
    "Avg review score", f"{summary['avg_review_score']:.2f} / 5", help=DEFINITIONS["review"]
)

st.subheader("On-time delivery over time")
left, right = st.columns(2)
with left:
    show_chart(
        charts.monthly_line(monthly, "on_time_pct", "On-time delivery % by month", "%"),
        key="ontime",
    )
with right:
    show_chart(
        charts.monthly_line(
            monthly, "avg_review_score", "Average review score by month", "score (1-5)"
        ),
        key="review",
    )
flagged = incomplete_months(monthly)
if flagged:
    st.caption(f"Grey diamond(s): {', '.join(flagged)}. {INCOMPLETE_NOTE}")

st.subheader("How lateness affects reviews")
show_chart(charts.review_by_bucket(impact), key="bucket")
st.caption(
    "Association only: late orders may also differ in distance, product or seller. "
    "See docs/insights.md (Q6) for the interpretation."
)

st.subheader("Does a late first delivery reduce repeat purchases?")
show_table(
    repeat.rename(
        columns={
            "first_delivery": "first delivery",
            "repeat_customers": "repeat customers",
            "repeat_rate_pct": "repeat rate %",
            "avg_first_review_score": "avg first review",
        }
    ),
    formats={
        "repeat rate %": "%.2f",
        "avg first review": "%.2f",
        "customers": "%d",
        "repeat customers": "%d",
    },
)
st.caption(
    "Customers whose first delivered order was late versus on time, followed for a fixed period. "
    "Association only; see docs/insights.md (Q10) for how reliable the difference is."
)

st.subheader("Regions")
max_orders = int(states["delivered_orders"].max()) if not states.empty else 0
min_orders = st.slider(
    "Only states with at least this many delivered orders",
    min_value=0,
    max_value=max(max_orders, 1),
    value=min(500, max_orders),
)
shown = states[states["delivered_orders"] >= min_orders]
left, right = st.columns(2)
with left:
    show_chart(
        tile_map(
            shown,
            "on_time_pct",
            "On-time %",
            "{:.1f}%",
            colorscale="RdYlGn",
            hover_cols={"delivered_orders": "Orders", "avg_delivery_days": "Avg days"},
        ),
        key="ontime_map",
    )
with right:
    show_table(
        shown.sort_values("on_time_pct")[
            ["state", "delivered_orders", "on_time_pct", "avg_delivery_days", "avg_review_score"]
        ],
        formats={"on_time_pct": "%.1f", "avg_delivery_days": "%.1f", "avg_review_score": "%.2f"},
        height=440,
    )

st.subheader("Weakest sellers by review score")
rankable = sellers[sellers["meets_min_volume"].astype(bool)]
st.caption(
    f"{len(rankable):,} of {len(sellers):,} sellers have enough orders to be ranked. Orders with "
    "several sellers count toward each seller, so treat this as indicative."
)
if rankable.empty:
    st.info("No seller has enough orders to be ranked.")
else:
    top_n = st.slider("Number of sellers to show", 5, 50, 10)
    first = rankable.iloc[0]
    st.write(
        f"Marketplace benchmark: {first['overall_late_pct']:.1f}% late, "
        f"average review {first['overall_avg_review_score']:.2f}."
    )
    show_table(
        rankable.sort_values("avg_review_score").head(top_n)[
            ["seller_key", "state", "orders", "revenue", "late_pct", "avg_review_score"]
        ],
        formats={"revenue": "%.0f", "late_pct": "%.1f", "avg_review_score": "%.2f"},
    )
