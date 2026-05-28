"""
activation_report.py
Activation scoring logic — no HTML generation.
HTML rendering is handled by dashboard.py.

Exports:
  score_activation(df)        — adds overdue milestone list and count per account
  compute_ttv_benchmarks(df)  — portfolio-level avg completion days per milestone
  get_expansion_pipeline(df)  — top 3 Thriving accounts with highest upsell potential
"""

import pandas as pd
from config import ACTIVATION_MILESTONES, MILESTONE_TTV_TARGETS


def _overdue_milestones(row: pd.Series) -> list[str]:
    """Return labels of milestones that are due but not yet completed."""
    overdue = []
    days = row["days_on_platform"]
    for m in ACTIVATION_MILESTONES:
        if days >= m["tier_days"] and not row.get(m["id"], False):
            overdue.append(m["label"])
    return overdue


def score_activation(df: pd.DataFrame) -> pd.DataFrame:
    """Add overdue milestone list and overdue count columns to the dataframe."""
    df = df.copy()
    df["overdue_milestones"] = df.apply(_overdue_milestones, axis=1)
    df["overdue_count"] = df["overdue_milestones"].apply(len)
    return df


def compute_ttv_benchmarks(df: pd.DataFrame) -> dict:
    """
    For each milestone, return:
      - target_days: from config
      - avg_actual_days: average days_on_platform across accounts that have completed
        the milestone and are past the due date (approximation for mock data)
    """
    benchmarks = {}
    for m in ACTIVATION_MILESTONES:
        mid = m["id"]
        due_days = m["tier_days"]
        completed_mask = (df["days_on_platform"] >= due_days) & (df[mid] == True)
        if completed_mask.sum() > 0:
            avg_actual = round(df.loc[completed_mask, "days_on_platform"].mean())
        else:
            avg_actual = None
        benchmarks[mid] = {
            "label":       m["label"],
            "target_days": MILESTONE_TTV_TARGETS[mid],
            "avg_actual":  avg_actual,
        }
    return benchmarks


def get_expansion_pipeline(df: pd.DataFrame, top_n: int = 3) -> list[dict]:
    """
    Identify the top N Thriving accounts with the highest expansion potential.
    Expansion potential = low integration depth + flat/declining seat growth.
    """
    thriving = df[df["risk_tier"] == "Thriving"].copy()
    if thriving.empty:
        return []

    # Expansion score: higher = more upsell room
    thriving["_expansion_score"] = (
        (1 - thriving["integration_depth"]) * 0.60 +
        thriving["seat_expansion"].clip(upper=0).abs() * 0.40
    )
    thriving = thriving.sort_values("_expansion_score", ascending=False)

    results = []
    for _, row in thriving.head(top_n).iterrows():
        # Pick the highest-value lever based on gaps
        if row["integration_depth"] < 0.40:
            lever_label = "API / Integration Tier"
            lever_mrr = 199
        elif row["seats_now"] < 5:
            lever_label = "Enterprise Seat Pack"
            lever_mrr = 299
        else:
            lever_label = "Advanced AI Features"
            lever_mrr = 399

        results.append({
            "company_name":      row["company_name"],
            "vertical":          row["vertical"],
            "churn_risk_score":  row["churn_risk_score"],
            "contract_value_mo": row["contract_value_mo"],
            "integration_depth": row["integration_depth"],
            "seats_now":         row.get("seats_now", "—"),
            "lever_label":       lever_label,
            "lever_mrr":         lever_mrr,
        })

    return results


if __name__ == "__main__":
    from generate_data import generate_dataset
    from scoring import score_accounts

    df = generate_dataset()
    df = score_accounts(df)
    df = score_activation(df)

    benchmarks = compute_ttv_benchmarks(df)
    expansion = get_expansion_pipeline(df)

    print("\n--- TTV Benchmarks ---")
    for mid, b in benchmarks.items():
        actual = f"{b['avg_actual']}d" if b["avg_actual"] else "no data"
        print(f"  {b['label']:<35} target: {b['target_days']}d | actual: {actual}")

    print("\n--- Expansion Pipeline ---")
    for item in expansion:
        print(f"  {item['company_name']} ({item['vertical']}) → {item['lever_label']} +${item['lever_mrr']}/mo")
