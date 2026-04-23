"""
scoring.py
Weighted churn risk scoring engine.

Signal weights (must sum to 1.0):
  - Order volume trend (WoW % change): 0.30  — clearest revenue signal
  - Direct order rate:                 0.25  — platform stickiness signal
  - Login frequency:                   0.20  — engagement signal
  - Feature adoption:                  0.15  — depth of platform use
  - Marketing campaigns (30d):         0.10  — proactive use of platform

Score: 0 = perfect health, 100 = about to churn
Tiers: 0–39 = Thriving, 40–69 = At-Risk, 70–100 = Churning
"""

import pandas as pd

# --- Weights ---
WEIGHTS = {
    "order_volume_trend": 0.30,
    "direct_order_rate":  0.25,
    "login_frequency":    0.20,
    "feature_adoption":   0.15,
    "marketing_campaigns": 0.10,
}

# --- Normalization bounds (min = worst/riskiest, max = best/healthiest) ---
BOUNDS = {
    "order_volume_trend":  {"min": -60, "max": 20},   # % WoW change
    "direct_order_rate":   {"min": 0.05, "max": 0.85},
    "login_frequency":     {"min": 0, "max": 14},
    "feature_adoption":    {"min": 0, "max": 1.0},
    "marketing_campaigns": {"min": 0, "max": 8},
}


def _normalize(value, signal_name):
    """Normalize a raw signal to 0–1 health score (1 = best)."""
    lo = BOUNDS[signal_name]["min"]
    hi = BOUNDS[signal_name]["max"]
    clamped = max(lo, min(hi, value))
    return (clamped - lo) / (hi - lo)


def _signal_drivers(row):
    """
    Return the 2–3 most impactful risk signals for this restaurant,
    each with a plain-English description and direction.
    """
    signals = []

    trend = row["order_volume_trend_pct"]
    if trend <= -20:
        signals.append(f"order volume down {abs(round(trend))}% week-over-week")
    elif trend <= -5:
        signals.append(f"order volume declining ({round(trend, 1)}% WoW)")

    dor = row["direct_order_rate"]
    if dor < 0.30:
        signals.append(f"direct order rate critically low ({round(dor*100)}%, heavy 3rd-party dependency)")
    elif dor < 0.50:
        signals.append(f"direct order rate weak ({round(dor*100)}%)")

    logins = row["logins_per_week"]
    if logins <= 1:
        signals.append(f"login frequency near zero ({logins} login(s) this week)")
    elif logins <= 3:
        signals.append(f"low login activity ({logins} logins/week)")

    features = row["features_used"]
    total = row["total_features"]
    if features <= 2:
        signals.append(f"feature adoption minimal ({features}/{total} features used)")
    elif features <= 4:
        signals.append(f"feature adoption low ({features}/{total} features used)")

    campaigns = row["marketing_campaigns_30d"]
    if campaigns == 0:
        signals.append("no marketing campaigns sent in last 30 days")
    elif campaigns == 1:
        signals.append("only 1 marketing campaign in last 30 days")

    # Return top 3 by priority order (already ordered by weight above)
    return signals[:3] if signals else ["signals within normal range"]


def score_restaurants(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Compute order volume trend %
    df["order_volume_trend_pct"] = (
        (df["orders_this_week"] - df["orders_last_week"]) / df["orders_last_week"] * 100
    ).round(1)

    # Normalize each signal to 0–1 health (higher = healthier)
    df["n_trend"]     = df["order_volume_trend_pct"].apply(lambda x: _normalize(x, "order_volume_trend"))
    df["n_dor"]       = df["direct_order_rate"].apply(lambda x: _normalize(x, "direct_order_rate"))
    df["n_logins"]    = df["logins_per_week"].apply(lambda x: _normalize(x, "login_frequency"))
    df["n_features"]  = df["feature_adoption_rate"].apply(lambda x: _normalize(x, "feature_adoption"))
    df["n_campaigns"] = df["marketing_campaigns_30d"].apply(lambda x: _normalize(x, "marketing_campaigns"))

    # Weighted health score (0–1), then invert to get churn risk (0–100)
    df["health_score"] = (
        df["n_trend"]     * WEIGHTS["order_volume_trend"] +
        df["n_dor"]       * WEIGHTS["direct_order_rate"] +
        df["n_logins"]    * WEIGHTS["login_frequency"] +
        df["n_features"]  * WEIGHTS["feature_adoption"] +
        df["n_campaigns"] * WEIGHTS["marketing_campaigns"]
    )
    df["churn_risk_score"] = ((1 - df["health_score"]) * 100).round(1)

    # Assign tiers
    def _tier(score):
        if score >= 70:
            return "Churning"
        elif score >= 40:
            return "At-Risk"
        else:
            return "Thriving"

    df["risk_tier"] = df["churn_risk_score"].apply(_tier)

    # Top signal drivers
    df["signal_drivers"] = df.apply(_signal_drivers, axis=1)

    # Sort by churn risk descending
    df = df.sort_values("churn_risk_score", ascending=False).reset_index(drop=True)

    # Drop internal normalization columns
    df.drop(columns=["n_trend", "n_dor", "n_logins", "n_features", "n_campaigns", "health_score"], inplace=True)

    return df


if __name__ == "__main__":
    from generate_data import generate_dataset
    df = generate_dataset()
    scored = score_restaurants(df)
    cols = ["restaurant_name", "risk_tier", "churn_risk_score", "signal_drivers"]
    print(scored[cols].to_string(index=False))
