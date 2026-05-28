"""
scoring.py
Signal-agnostic churn risk scoring engine.
All signals, weights, and thresholds are read from config.py.

Score: 0 = perfect health, 100 = about to churn
Tiers: 0–39 = Thriving, 40–69 = At-Risk, 70–100 = Churning
"""

import pandas as pd
from config import SCORING_SIGNALS, TIER_THRESHOLDS


def _normalize(value: float, bounds: dict) -> float:
    """Normalize a raw signal value to 0–1 health score (1 = best/healthiest)."""
    lo, hi = bounds["min"], bounds["max"]
    clamped = max(lo, min(hi, value))
    return (clamped - lo) / (hi - lo)


def _signal_drivers(row: pd.Series) -> list[str]:
    """Return up to 3 plain-English descriptions of the top risk signals."""
    signals = []

    trend = row.get("ai_usage_trend_pct", 0)
    if trend <= -30:
        signals.append(f"AI generation volume down {abs(round(trend))}% week-over-week")
    elif trend <= -10:
        signals.append(f"AI usage declining ({round(trend, 1)}% WoW)")

    wcr = row.get("workflow_completion_rate", 1.0)
    if wcr < 0.20:
        signals.append(f"workflow completion critically low ({round(wcr * 100)}%)")
    elif wcr < 0.45:
        signals.append(f"workflow completion rate weak ({round(wcr * 100)}%)")

    freq = row.get("session_frequency", 0)
    if freq <= 1:
        signals.append(f"login frequency near zero ({freq} session(s)/week)")
    elif freq <= 3:
        signals.append(f"low session activity ({freq} sessions/week)")

    depth = row.get("integration_depth", 1.0)
    if depth < 0.15:
        signals.append("no meaningful integrations connected")
    elif depth < 0.40:
        connected = row.get("integrations_connected", 0)
        total = row.get("total_integrations", 10)
        signals.append(f"integration depth low ({connected}/{total} integrations)")

    seat_exp = row.get("seat_expansion", 0)
    if seat_exp < -0.10:
        signals.append(f"team seat count declining ({round(seat_exp * 100)}%)")
    elif seat_exp < 0:
        signals.append("no seat growth — team may be contracting")

    return signals[:3] if signals else ["all signals within normal range"]


def score_accounts(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Normalize each signal and accumulate weighted health score
    health = pd.Series(0.0, index=df.index)
    for col, cfg in SCORING_SIGNALS.items():
        normalized = df[col].apply(lambda v: _normalize(v, cfg["bounds"]))
        health += normalized * cfg["weight"]

    # Invert health → churn risk (0–100)
    df["churn_risk_score"] = ((1 - health) * 100).round(1)

    # Assign risk tier
    def _tier(score: float) -> str:
        if score >= TIER_THRESHOLDS["Churning"]:
            return "Churning"
        elif score >= TIER_THRESHOLDS["At-Risk"]:
            return "At-Risk"
        return "Thriving"

    df["risk_tier"] = df["churn_risk_score"].apply(_tier)

    # ARR at risk per account (annualized)
    df["arr_at_risk"] = df["contract_value_mo"] * 12

    # Top signal drivers
    df["signal_drivers"] = df.apply(_signal_drivers, axis=1)

    # Sort by churn risk descending
    df = df.sort_values("churn_risk_score", ascending=False).reset_index(drop=True)

    return df


if __name__ == "__main__":
    from generate_data import generate_dataset
    df = generate_dataset()
    scored = score_accounts(df)
    cols = ["company_name", "vertical", "risk_tier", "churn_risk_score", "contract_value_mo"]
    print(scored[cols].to_string(index=False))
