import pandas as pd
import numpy as np

def compute_buy_signals(zhvi_df, redfin_df, macros):
    """Return a dict of simple buy-timing signals based on available data."""
    signals = {}
    if zhvi_df.empty and redfin_df.empty:
        return signals

    # Latest values
    if not zhvi_df.empty:
        latest_zhvi = zhvi_df.iloc[-1]
        prev_zhvi = zhvi_df.iloc[-13] if len(zhvi_df) > 13 else zhvi_df.iloc[0]
        signals["current_zhvi"] = latest_zhvi.get("zhvi", None)
        signals["zhvi_yoy"] = ((latest_zhvi["zhvi"] / prev_zhvi["zhvi"]) - 1) * 100 if prev_zhvi["zhvi"] else None

    if not redfin_df.empty:
        latest_rf = redfin_df.iloc[-1]
        signals["median_sale_price"] = latest_rf.get("median_sale_price")
        signals["months_of_supply"] = latest_rf.get("months_of_supply")
        signals["median_dom"] = latest_rf.get("median_dom")
        signals["inventory"] = latest_rf.get("inventory")
        signals["price_drops"] = latest_rf.get("price_drops")

    # Mortgage rate context
    if not macros.get("mortgage_rate", pd.DataFrame()).empty:
        rate_df = macros["mortgage_rate"]
        signals["current_mortgage_rate"] = rate_df.iloc[-1]["value"]
        # Simple: rates falling is better for buyers
        if len(rate_df) > 4:
            signals["rate_change_4w"] = rate_df.iloc[-1]["value"] - rate_df.iloc[-5]["value"]

    # Buy signal rules (simple heuristics)
    mos = signals.get("months_of_supply")
    yoy = signals.get("zhvi_yoy")
    rate_chg = signals.get("rate_change_4w")

    buy_score = 0
    reasons = []
    if mos is not None and mos >= 5:
        buy_score += 2
        reasons.append(f"Months of supply {mos:.1f} favors buyers")
    elif mos is not None and mos <= 3:
        buy_score -= 1
        reasons.append(f"Months of supply {mos:.1f} favors sellers")

    if yoy is not None and yoy < 0:
        buy_score += 1
        reasons.append(f"Prices down {yoy:.1f}% YoY")
    elif yoy is not None and yoy > 8:
        buy_score -= 1
        reasons.append(f"Strong price growth {yoy:.1f}% YoY")

    if rate_chg is not None and rate_chg < -0.2:
        buy_score += 1
        reasons.append("Mortgage rates falling recently")

    signals["buy_score"] = buy_score
    signals["buy_reasons"] = reasons
    if buy_score >= 2:
        signals["market_bias"] = "Buyer-friendly"
    elif buy_score <= -1:
        signals["market_bias"] = "Seller-friendly"
    else:
        signals["market_bias"] = "Balanced / Neutral"

    return signals

def listing_evaluator(listing_price, zip_zhvi, metro_zhvi, mortgage_rate=6.5, down_pct=0.20, term_years=30):
    """Compare a user-entered listing price against local medians and estimate payment."""
    result = {}
    result["listing_price"] = listing_price
    if zip_zhvi is not None and not np.isnan(zip_zhvi):
        result["vs_zip_zhvi_pct"] = ((listing_price / zip_zhvi) - 1) * 100
        result["zip_zhvi"] = zip_zhvi
    if metro_zhvi is not None and not np.isnan(metro_zhvi):
        result["vs_metro_zhvi_pct"] = ((listing_price / metro_zhvi) - 1) * 100
        result["metro_zhvi"] = metro_zhvi

    # Simple monthly payment estimate (principal + interest only)
    loan = listing_price * (1 - down_pct)
    monthly_rate = (mortgage_rate / 100) / 12
    n_payments = term_years * 12
    if monthly_rate > 0:
        payment = loan * (monthly_rate * (1 + monthly_rate)**n_payments) / ((1 + monthly_rate)**n_payments - 1)
    else:
        payment = loan / n_payments
    result["est_monthly_pi"] = payment
    result["down_payment"] = listing_price * down_pct
    result["mortgage_rate_used"] = mortgage_rate
    return result
