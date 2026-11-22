import streamlit as st
import pandas as pd
import plotly.express as px
from data import (
    load_zillow_metro_zhvi, load_zillow_zip_zhvi,
    load_redfin_metro, load_redfin_zip, load_macros
)
from signals import compute_buy_signals, listing_evaluator

st.set_page_config(page_title="Seattle Housing Monitor", layout="wide")
st.title("Seattle Housing Market Monitor")
st.caption("Public data from Zillow Research, Redfin, and FRED. Refreshes when sources update. Not financial advice.")

# Sidebar controls
st.sidebar.header("Settings")
fred_key = st.sidebar.text_input("FRED API Key (optional, for macros)", type="password", help="Get a free key at fred.stlouisfed.org")
selected_zip = st.sidebar.text_input("ZIP code (optional)", placeholder="e.g. 98101")
show_forecasts = st.sidebar.checkbox("Show Zillow forecasts (if available)", value=True)

# Load data
with st.spinner("Loading latest public data..."):
    metro_zhvi = load_zillow_metro_zhvi()
    redfin_metro = load_redfin_metro()
    macros = load_macros(fred_key) if fred_key else {}

    zip_zhvi = pd.DataFrame()
    redfin_zip = pd.DataFrame()
    if selected_zip:
        zip_zhvi = load_zillow_zip_zhvi(selected_zip)
        redfin_zip = load_redfin_zip(selected_zip)

# Buy signals
signals = compute_buy_signals(
    zip_zhvi if not zip_zhvi.empty else metro_zhvi,
    redfin_zip if not redfin_zip.empty else redfin_metro,
    macros
)

# Overview metrics
st.header("Market Overview")
col1, col2, col3, col4 = st.columns(4)
with col1:
    zhvi_val = signals.get("current_zhvi")
    st.metric("Typical Home Value (ZHVI)", f"${zhvi_val:,.0f}" if zhvi_val else "—",
              delta=f"{signals.get('zhvi_yoy', 0):.1f}% YoY" if signals.get("zhvi_yoy") else None)
with col2:
    mos = signals.get("months_of_supply")
    st.metric("Months of Supply", f"{mos:.1f}" if mos else "—")
with col3:
    rate = signals.get("current_mortgage_rate")
    st.metric("30-yr Mortgage Rate", f"{rate:.2f}%" if rate else "—")
with col4:
    bias = signals.get("market_bias", "—")
    st.metric("Market Bias", bias)

if signals.get("buy_reasons"):
    st.subheader("Buy Timing Notes")
    for r in signals["buy_reasons"]:
        st.write(f"- {r}")
    st.caption(f"Simple score: {signals.get('buy_score', 0)} (higher = more buyer-friendly)")

# Charts
st.header("Trends")
tab1, tab2 = st.tabs(["Home Values", "Redfin Market Metrics"])

with tab1:
    chart_df = zip_zhvi if not zip_zhvi.empty else metro_zhvi
    if not chart_df.empty:
        fig = px.line(chart_df, x="date", y="zhvi", title="Zillow Home Value Index")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No ZHVI data available.")

with tab2:
    rf_df = redfin_zip if not redfin_zip.empty else redfin_metro
    if not rf_df.empty:
        fig2 = px.line(rf_df, x="period_begin", y="median_sale_price", title="Median Sale Price (Redfin)")
        st.plotly_chart(fig2, use_container_width=True)
        if "months_of_supply" in rf_df.columns:
            fig3 = px.line(rf_df, x="period_begin", y="months_of_supply", title="Months of Supply")
            st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No Redfin data available.")

# Listing evaluator
st.header("Listing Evaluator")
st.write("Enter a listing price to compare against local typical values and estimate a payment.")
lcol1, lcol2 = st.columns(2)
with lcol1:
    listing_price = st.number_input("Listing price ($)", min_value=100000, value=750000, step=10000)
with lcol2:
    rate_input = st.number_input("Assumed mortgage rate (%)", min_value=0.0, value=float(signals.get("current_mortgage_rate") or 6.5), step=0.1)

if st.button("Evaluate listing"):
    latest_zip = zip_zhvi.iloc[-1]["zhvi"] if not zip_zhvi.empty else None
    latest_metro = metro_zhvi.iloc[-1]["zhvi"] if not metro_zhvi.empty else None
    eval_result = listing_evaluator(listing_price, latest_zip, latest_metro, rate_input)
    st.subheader("Comparison")
    if "vs_zip_zhvi_pct" in eval_result:
        st.write(f"Vs ZIP ZHVI: {eval_result['vs_zip_zhvi_pct']:.1f}%")
    if "vs_metro_zhvi_pct" in eval_result:
        st.write(f"Vs Metro ZHVI: {eval_result['vs_metro_zhvi_pct']:.1f}%")
    st.write(f"Estimated monthly P&I (20% down): ${eval_result['est_monthly_pi']:,.0f}")
    st.write(f"Down payment: ${eval_result['down_payment']:,.0f}")

# Macro panel
if macros:
    st.header("Macro Indicators")
    mcol1, mcol2 = st.columns(2)
    with mcol1:
        if not macros.get("mortgage_rate", pd.DataFrame()).empty:
            fig_m = px.line(macros["mortgage_rate"].tail(104), x="date", y="value", title="30-Year Mortgage Rate")
            st.plotly_chart(fig_m, use_container_width=True)
    with mcol2:
        if not macros.get("seattle_unemp", pd.DataFrame()).empty:
            fig_u = px.line(macros["seattle_unemp"].tail(60), x="date", y="value", title="Seattle MSA Unemployment Rate")
            st.plotly_chart(fig_u, use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.caption("Data sources: Zillow Research, Redfin Data Center, FRED. Attribution required for Zillow data.")
