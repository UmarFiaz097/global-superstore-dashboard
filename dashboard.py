"""
Global Superstore Interactive Dashboard
========================================
A Streamlit app to analyze Sales, Profit, and Segment-wise performance.
Run with: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# Always resolve the data file relative to this script's location.
# "Global_Superstore.txt" alone fails on Streamlit Cloud because the
# working directory is not guaranteed to be the repo root.
DATA_PATH = Path(__file__).parent / "Global_Superstore.txt"

# ─────────────────────────────────────────────
# STEP 1: PAGE CONFIG
# ─────────────────────────────────────────────
# Sets the browser tab title, icon, and wide layout so charts have room to breathe.
st.set_page_config(
    page_title="Global Superstore Dashboard",
    page_icon="🛒",
    layout="wide"
)

st.title("🛒 Global Superstore — Sales & Profit Dashboard")
st.markdown("Explore sales performance across regions, categories, and customer segments.")

# ─────────────────────────────────────────────
# STEP 2: LOAD & CLEAN DATA
# ─────────────────────────────────────────────
# @st.cache_data means the file is only read once; re-renders skip the disk read.
# This is critical for a 15 MB file — without it the app would re-read on every click.
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH, sep="\t")

    # --- Cleaning ---
    # Convert date strings to proper datetime so we can sort/filter by year later
    df["Order Date"] = pd.to_datetime(df["Order Date"])

    # Drop the Chinese-language column (记录数) — it's just a row counter
    df.drop(columns=["记录数"], inplace=True, errors="ignore")

    # Ensure numeric columns are floats (they load as objects if commas/quotes sneak in)
    df["Sales"]  = pd.to_numeric(df["Sales"],  errors="coerce").fillna(0)
    df["Profit"] = pd.to_numeric(df["Profit"], errors="coerce").fillna(0)

    return df

df = load_data()

# ─────────────────────────────────────────────
# STEP 3: SIDEBAR FILTERS
# ─────────────────────────────────────────────
# Filters are placed in the sidebar so they don't crowd the main chart area.
# Each filter defaults to "All" — users only narrow down if they want to.
st.sidebar.header("🔍 Filter Data")

# Region filter
all_regions = sorted(df["Region"].dropna().unique())
selected_regions = st.sidebar.multiselect(
    "Region", all_regions, default=all_regions
)

# Category filter
all_categories = sorted(df["Category"].dropna().unique())
selected_categories = st.sidebar.multiselect(
    "Category", all_categories, default=all_categories
)

# Sub-Category filter (dynamically depends on Category selection)
# Insight: Cascading filters prevent impossible combinations like
# "Furniture > Phones" which don't exist in the data.
sub_cats = sorted(
    df[df["Category"].isin(selected_categories)]["Sub-Category"].dropna().unique()
)
selected_subcats = st.sidebar.multiselect(
    "Sub-Category", sub_cats, default=sub_cats
)

# ─────────────────────────────────────────────
# STEP 4: APPLY FILTERS
# ─────────────────────────────────────────────
filtered = df[
    df["Region"].isin(selected_regions) &
    df["Category"].isin(selected_categories) &
    df["Sub-Category"].isin(selected_subcats)
]

# Warn if the filter returns no rows — helps users spot accidental over-filtering
if filtered.empty:
    st.warning("⚠️ No data matches the current filters. Try broadening your selection.")
    st.stop()

# ─────────────────────────────────────────────
# STEP 5: KPI CARDS (TOP ROW)
# ─────────────────────────────────────────────
# KPI cards give executives an instant at-a-glance summary before they look at charts.
# Profit Margin = Profit / Sales × 100  (tells efficiency, not just raw numbers)
total_sales   = filtered["Sales"].sum()
total_profit  = filtered["Profit"].sum()
total_orders  = filtered["Order ID"].nunique()
profit_margin = (total_profit / total_sales * 100) if total_sales else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Total Sales",    f"${total_sales:,.0f}")
col2.metric("📈 Total Profit",   f"${total_profit:,.0f}")
col3.metric("📦 Unique Orders",  f"{total_orders:,}")
col4.metric("📊 Profit Margin",  f"{profit_margin:.1f}%")

st.divider()

# ─────────────────────────────────────────────
# STEP 6: SALES BY REGION (BAR CHART)
# ─────────────────────────────────────────────
# Insight: A horizontal bar sorted by Sales immediately reveals which
# regions drive the most revenue — no mental sorting required.
st.subheader("📍 Total Sales by Region")

region_sales = (
    filtered.groupby("Region")["Sales"]
    .sum()
    .reset_index()
    .sort_values("Sales", ascending=True)   # ascending=True → tallest bar at top
)

fig_region = px.bar(
    region_sales, x="Sales", y="Region", orientation="h",
    color="Sales", color_continuous_scale="Blues",
    labels={"Sales": "Total Sales ($)"},
    text_auto=".2s"   # Shows abbreviated values like "1.2M" on each bar
)
fig_region.update_layout(showlegend=False, coloraxis_showscale=False, height=380)
st.plotly_chart(fig_region, use_container_width=True)

# ─────────────────────────────────────────────
# STEP 7: PROFIT BY CATEGORY (PIE CHART)
# ─────────────────────────────────────────────
# Insight: A pie chart is ideal here because we want to show *share* of total
# profit across only 3 categories — simple enough that a pie isn't misleading.
st.subheader("🗂️ Profit Share by Category")

col_a, col_b = st.columns(2)

with col_a:
    cat_profit = filtered.groupby("Category")["Profit"].sum().reset_index()
    fig_pie = px.pie(
        cat_profit, values="Profit", names="Category",
        color_discrete_sequence=px.colors.qualitative.Pastel,
        hole=0.35   # Donut style — easier to read the center label
    )
    fig_pie.update_traces(textinfo="percent+label")
    st.plotly_chart(fig_pie, use_container_width=True)

# ─────────────────────────────────────────────
# STEP 8: SEGMENT-WISE SALES & PROFIT (GROUPED BAR)
# ─────────────────────────────────────────────
# Insight: Plotting Sales and Profit side-by-side per segment reveals
# which segments are high-revenue but low-margin (a red flag).
with col_b:
    st.subheader("👥 Segment: Sales vs Profit")
    seg = filtered.groupby("Segment")[["Sales", "Profit"]].sum().reset_index()
    fig_seg = px.bar(
        seg.melt(id_vars="Segment", value_vars=["Sales", "Profit"]),
        x="Segment", y="value", color="variable", barmode="group",
        labels={"value": "Amount ($)", "variable": "Metric"},
        color_discrete_sequence=["#4C72B0", "#DD8452"]
    )
    st.plotly_chart(fig_seg, use_container_width=True)

st.divider()

# ─────────────────────────────────────────────
# STEP 9: TOP 5 CUSTOMERS BY SALES (HORIZONTAL BAR)
# ─────────────────────────────────────────────
# Insight: Identifying top customers helps prioritize account management.
# The color encoding of Profit quickly flags if a top-sales customer
# is actually unprofitable (negative Profit = red).
st.subheader("🏆 Top 5 Customers by Sales")

top_customers = (
    filtered.groupby("Customer Name")
    .agg(Total_Sales=("Sales", "sum"), Total_Profit=("Profit", "sum"))
    .reset_index()
    .sort_values("Total_Sales", ascending=False)
    .head(5)
)

fig_cust = px.bar(
    top_customers.sort_values("Total_Sales"),
    x="Total_Sales", y="Customer Name", orientation="h",
    color="Total_Profit",
    color_continuous_scale="RdYlGn",   # Red = loss, Green = high profit
    labels={"Total_Sales": "Total Sales ($)", "Total_Profit": "Profit ($)"},
    text_auto=".2s"
)
fig_cust.update_layout(height=320, coloraxis_colorbar_title="Profit")
st.plotly_chart(fig_cust, use_container_width=True)

# ─────────────────────────────────────────────
# STEP 10: SALES TREND OVER TIME (LINE CHART)
# ─────────────────────────────────────────────
# Insight: Monthly aggregation smooths daily noise while still showing
# seasonal patterns (e.g., Q4 holiday spikes in retail data).
st.subheader("📅 Monthly Sales Trend")

filtered["Month"] = filtered["Order Date"].dt.to_period("M").astype(str)
monthly = filtered.groupby("Month")["Sales"].sum().reset_index().sort_values("Month")

fig_line = px.line(
    monthly, x="Month", y="Sales",
    labels={"Sales": "Sales ($)", "Month": ""},
    markers=True
)
fig_line.update_traces(line_color="#4C72B0", line_width=2)
fig_line.update_layout(height=320)
st.plotly_chart(fig_line, use_container_width=True)

# ─────────────────────────────────────────────
# STEP 11: RAW DATA PREVIEW (OPTIONAL)
# ─────────────────────────────────────────────
# Hidden behind an expander so it doesn't clutter the main view,
# but analysts who want to spot-check raw rows can expand it.
with st.expander("🔎 Preview Filtered Raw Data"):
    st.dataframe(
        filtered[["Order Date", "Customer Name", "Region", "Category",
                   "Sub-Category", "Segment", "Sales", "Profit"]].head(200),
        use_container_width=True
    )

st.caption("Data: Global Superstore | Built with Streamlit & Plotly")
