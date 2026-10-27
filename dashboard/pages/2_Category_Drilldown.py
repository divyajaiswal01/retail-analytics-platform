"""Category Drill-down: filter delivered items and revenue by month, category and state."""

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
    money,
    money_short,
    num,
    pct,
    show_chart,
    show_error,
    show_table,
)

st.title("Category Drill-down")
st.caption(
    "Delivered items and revenue by purchase month, category and customer state "
    "(BRL, excluding freight)."
)

try:
    with st.spinner("Loading data..."):
        cube = queries.sales_cube()
except DashboardDataError as exc:
    show_error(exc)
    st.stop()

if cube.empty:
    st.error("The sales cube is empty. Re-run `dbt build`.")
    st.stop()

months = sorted(cube["year_month"].unique())
by_category = cube.groupby("category")["revenue"].sum().sort_values(ascending=False)
all_states = sorted(cube["state"].unique())

with st.sidebar:
    st.header("Filters")
    if len(months) > 1:
        month_from, month_to = st.select_slider(
            "Months", options=months, value=(months[0], months[-1])
        )
    else:
        month_from = month_to = months[0]
    chosen_categories = st.multiselect(
        "Categories", options=list(by_category.index), default=list(by_category.index[:5])
    )
    chosen_states = st.multiselect("States", options=all_states, default=all_states)

if not chosen_categories or not chosen_states:
    st.info("Select at least one category and one state in the sidebar.")
    st.stop()

selection = cube[
    (cube["year_month"] >= month_from)
    & (cube["year_month"] <= month_to)
    & cube["category"].isin(chosen_categories)
    & cube["state"].isin(chosen_states)
]
if selection.empty:
    st.warning("No sales match these filters.")
    st.stop()

revenue = selection["revenue"].sum()
items = selection["items_sold"].sum()
cols = st.columns(4)
cols[0].metric("Revenue", money_short(revenue), help=DEFINITIONS["revenue"])
cols[1].metric("Items sold", num(items), help=DEFINITIONS["items"])
cols[2].metric("Share of all delivered revenue", pct(100 * revenue / cube["revenue"].sum()))
cols[3].metric(
    "Categories x states", f"{selection['category'].nunique()} x {selection['state'].nunique()}"
)

monthly = selection.groupby("year_month", as_index=False).agg(
    revenue=("revenue", "sum"),
    items_sold=("items_sold", "sum"),
    is_complete_month=("is_complete_month", "all"),
)
show_chart(charts.monthly_bars(monthly, "revenue", "Revenue by month", "BRL"), key="dd_month")
flagged = incomplete_months(monthly)
if flagged:
    st.caption(f"Grey bar(s): {', '.join(flagged)}. {INCOMPLETE_NOTE}")

left, right = st.columns(2)
with left:
    cat_totals = (
        selection.groupby("category", as_index=False)["revenue"].sum().nlargest(15, "revenue")
    )
    show_chart(
        charts.horizontal_bar(cat_totals, "revenue", "category", "Revenue by category", "BRL"),
        key="dd_cat",
    )
with right:
    state_totals = selection.groupby("state", as_index=False).agg(
        revenue=("revenue", "sum"), items_sold=("items_sold", "sum")
    )
    show_chart(
        tile_map(
            state_totals, "revenue", "Revenue (BRL)", "{:,.0f}", hover_cols={"items_sold": "Items"}
        ),
        key="dd_state",
    )

if selection["category"].nunique() > 1 and selection["state"].nunique() > 1:
    top_c = selection.groupby("category")["revenue"].sum().nlargest(12).index
    top_s = selection.groupby("state")["revenue"].sum().nlargest(12).index
    pivot = selection[
        selection["category"].isin(top_c) & selection["state"].isin(top_s)
    ].pivot_table(index="category", columns="state", values="revenue", aggfunc="sum", fill_value=0)
    show_chart(charts.category_heatmap(pivot), key="dd_heat")
    st.caption("Shows up to 12 categories and 12 states with the most revenue in the selection.")

st.subheader("Detail")
detail = selection.sort_values(["year_month", "revenue"], ascending=[True, False])[
    ["year_month", "category", "state", "items_sold", "revenue"]
]
show_table(detail.head(1000), formats={"revenue": "%.2f"}, height=360)
if len(detail) > 1000:
    st.caption(f"Showing the first 1,000 of {len(detail):,} rows. The download has all of them.")
st.download_button(
    "Download selection as CSV",
    detail.to_csv(index=False).encode("utf-8"),
    "sales_selection.csv",
    "text/csv",
)
st.caption(f"Total revenue in selection: {money(revenue)}")
