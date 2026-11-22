import streamlit as st
import pandas as pd
import requests
from io import BytesIO
import gzip
from datetime import datetime
import os

# Known public URLs
ZILLOW_METRO_ZHVI = "https://files.zillowstatic.com/research/public_csvs/zhvi/Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
ZILLOW_ZIP_ZHVI = "https://files.zillowstatic.com/research/public_csvs/zhvi/Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
ZILLOW_METRO_INV = "https://files.zillowstatic.com/research/public_csvs/invt_fs/Metro_invt_fs_uc_sfrcondo_sm_month.csv"
ZILLOW_METRO_ZHVF = "https://files.zillowstatic.com/research/public_csvs/zhvf_growth/Metro_zhvf_growth_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"

REDFIN_METRO = "https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker/redfin_metro_market_tracker.tsv000.gz"
REDFIN_ZIP = "https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker/zip_code_market_tracker.tsv000.gz"

SEATTLE_METRO_NAME = "Seattle, WA"
SEATTLE_MSA_KEYWORDS = ["Seattle", "Tacoma", "Bellevue"]

@st.cache_data(ttl=60*60*12)  # 12 hours
def load_zillow_metro_zhvi():
    try:
        df = pd.read_csv(ZILLOW_METRO_ZHVI)
        # Melt to long format
        id_cols = [c for c in df.columns if not c[0].isdigit()]
        df_long = df.melt(id_vars=id_cols, var_name="date", value_name="zhvi")
        df_long["date"] = pd.to_datetime(df_long["date"])
        df_long = df_long.dropna(subset=["zhvi"])
        # Filter Seattle metro
        seattle = df_long[df_long["RegionName"].str.contains("Seattle", case=False, na=False)]
        return seattle.sort_values("date")
    except Exception as e:
        st.warning(f"Could not load Zillow metro ZHVI: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60*60*12)
def load_zillow_zip_zhvi(zip_code=None):
    try:
        df = pd.read_csv(ZILLOW_ZIP_ZHVI)
        id_cols = [c for c in df.columns if not str(c)[0].isdigit()]
        df_long = df.melt(id_vars=id_cols, var_name="date", value_name="zhvi")
        df_long["date"] = pd.to_datetime(df_long["date"])
        df_long = df_long.dropna(subset=["zhvi"])
        # Prefer WA ZIPs for Seattle area
        if "State" in df_long.columns:
            df_long = df_long[df_long["State"] == "WA"]
        if zip_code:
            zip_data = df_long[df_long["RegionName"].astype(str) == str(zip_code)]
            return zip_data.sort_values("date")
        return df_long.sort_values("date")
    except Exception as e:
        st.warning(f"Could not load Zillow ZIP ZHVI: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60*60*12)
def load_redfin_metro():
    try:
        r = requests.get(REDFIN_METRO, timeout=60)
        r.raise_for_status()
        df = pd.read_csv(BytesIO(r.content), compression="gzip", sep="\t")
        df["period_begin"] = pd.to_datetime(df["period_begin"])
        # Filter Seattle metro
        seattle = df[df["region"].str.contains("Seattle", case=False, na=False)]
        # Prefer monthly, All Residential
        seattle = seattle[(seattle["period_duration"] == "monthly") & (seattle["property_type"] == "All Residential")]
        return seattle.sort_values("period_begin")
    except Exception as e:
        st.warning(f"Could not load Redfin metro: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60*60*12)
def load_redfin_zip(zip_code=None):
    try:
        r = requests.get(REDFIN_ZIP, timeout=90)
        r.raise_for_status()
        df = pd.read_csv(BytesIO(r.content), compression="gzip", sep="\t")
        df["period_begin"] = pd.to_datetime(df["period_begin"])
        df = df[(df["period_duration"] == "monthly") & (df["property_type"] == "All Residential")]
        if zip_code:
            zip_data = df[df["region"].astype(str) == str(zip_code)]
            return zip_data.sort_values("period_begin")
        # Limit to WA for performance if no specific ZIP
        if "state_code" in df.columns:
            df = df[df["state_code"] == "WA"]
        return df.sort_values("period_begin")
    except Exception as e:
        st.warning(f"Could not load Redfin ZIP: {e}")
        return pd.DataFrame()

def get_fred_series(series_id, api_key):
    if not api_key:
        return pd.DataFrame()
    try:
        from fredapi import Fred
        fred = Fred(api_key=api_key)
        series = fred.get_series(series_id)
        df = series.reset_index()
        df.columns = ["date", "value"]
        df["date"] = pd.to_datetime(df["date"])
        return df.dropna()
    except Exception as e:
        st.warning(f"FRED error for {series_id}: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60*60*6)
def load_macros(fred_key):
    macros = {}
    macros["mortgage_rate"] = get_fred_series("MORTGAGE30US", fred_key)
    macros["national_unemp"] = get_fred_series("UNRATE", fred_key)
    # Seattle MSA unemployment (common series ID)
    macros["seattle_unemp"] = get_fred_series("SEAT353URN", fred_key)
    macros["case_shiller"] = get_fred_series("SEXRSA", fred_key)
    return macros
