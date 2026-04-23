"""
activation_report.py
Generates the Activation Depth Tracker report (activation_report.html).

Logic:
- Each restaurant is evaluated against 8 milestones across 30/60/90/120-day tiers.
- A restaurant is "underactivated" if it has missed any milestone due by its current tenure.
- The report shows one card per customer with milestone status and overdue flags.
"""

import os
import pandas as pd
from datetime import date

from generate_data import MILESTONES

# Milestone metadata grouped by tier
TIERS = [
    {
        "label": "Day 30",
        "due_month": 1,
        "color": "#3B82F6",
        "milestones": [m for m in MILESTONES if m[2] == 1],
    },
    {
        "label": "Day 60",
        "due_month": 2,
        "color": "#8B5CF6",
        "milestones": [m for m in MILESTONES if m[2] == 2],
    },
    {
        "label": "Day 90",
        "due_month": 3,
        "color": "#F59E0B",
        "milestones": [m for m in MILESTONES if m[2] == 3],
    },
    {
        "label": "Day 120+",
        "due_month": 4,
        "color": "#10B981",
        "milestones": [m for m in MILESTONES if m[2] == 4],
    },
]

RISK_COLORS = {
    "Thriving": {"badge_bg": "#DCFCE7", "badge_text": "#15803D"},
    "At-Risk":  {"badge_bg": "#FEF3C7", "badge_text": "#B45309"},
    "Churning": {"badge_bg": "#FFE4E6", "badge_text": "#BE123C"},
}

NAV_HTML = """
<div style="background:white;border-bottom:1px solid #E2E8F0;padding:0 40px;display:flex;align-items:center;height:60px;gap:0;">
  <div style="font-size:18px;font-weight:700;color:#0F172A;letter-spacing:-.02em;margin-right:40px;">owner<span style="color:#0066FF;">.</span>com</div>
  <a href="churn_report.html" style="text-decoration:none;padding:0 16px;height:60px;display:flex;align-items:center;font-size:13px;font-weight:500;color:#64748B;border-bottom:2px solid transparent;">Churn Risk</a>
  <a href="activation_report.html" style="text-decoration:none;padding:0 16px;height:60px;display:flex;align-items:center;font-size:13px;font-weight:500;color:#0066FF;border-bottom:2px solid #0066FF;">Activation Depth</a>
  <a href="nrr_model.html" style="text-decoration:none;padding:0 16px;height:60px;display:flex;align-items:center;font-size:13px;font-weight:500;color:#64748B;border-bottom:2px solid transparent;">NRR Scenario</a>
  <a href="intervention_queue.html" style="text-decoration:none;padding:0 16px;height:60px;display:flex;align-items:center;font-size:13px;font-weight:500;color:#64748B;border-bottom:2px solid transparent;">Intervention Queue</a>
</div>
"""


def _overdue_milestones(row) -> list[str]:
    """Return labels of milestones that are due but not completed."""
    overdue = []
    for col, label, due_month in MILESTONES:
        if row["months_on_platform"] >= due_month and not row[col]:
            overdue.append(label)
    return overdue


def _tenure_band(months: int) -> str:
    if months <= 1:
        return "0-30 days"
    elif months <= 2:
        return "30-60 days"
    elif months <= 3:
        return "60-90 days"
    else:
        return f"{months} months"


def _milestone_pill(label: str, completed: bool, overdue: bool) -> str:
    if completed:
        bg, text, icon = "#DCFCE7", "#15803D", "&#10003;"
    elif overdue:
        bg, text, icon = "#FFE4E6", "#BE123C", "&#10005;"
    else:
        bg, text, icon = "#F1F5F9", "#94A3B8", "&middot;"
    return (
        f'<span style="background:{bg};color:{text};padding:3px 9px;border-radius:20px;'
        f'font-size:11px;font-weight:600;white-space:nowrap;">{icon} {label}</span>'
    )


def _restaurant_card(row, overdue: list) -> str:
    months = row["months_on_platform"]
    risk_tier = row.get("risk_tier", "Thriving")
    rc = RISK_COLORS.get(risk_tier, RISK_COLORS["Thriving"])
    is_underactivated = len(overdue) > 0

    underactivation_badge = ""
    if is_underactivated:
        count = len(overdue)
        underactivation_badge = (
            f'<span style="background:#FFF1F2;color:#BE123C;padding:3px 10px;border-radius:20px;'
            f'font-size:11px;font-weight:600;">&#9888; {count} overdue</span>'
        )
    else:
        underactivation_badge = (
            '<span style="background:#F0FDF4;color:#15803D;padding:3px 10px;border-radius:20px;'
            'font-size:11px;font-weight:600;">&#10003; On track</span>'
        )

    risk_badge = (
        f'<span style="background:{rc["badge_bg"]};color:{rc["badge_text"]};padding:3px 10px;'
        f'border-radius:20px;font-size:11px;font-weight:600;">{risk_tier}</span>'
    )

    # Build tier columns
    tier_cols = []
    for tier in TIERS:
        due_month = tier["due_month"]
        is_tier_due = months >= due_month
        pills_html = ""
        for col, label, _ in tier["milestones"]:
            completed = bool(row[col])
            is_overdue = is_tier_due and not completed
            pills_html += f'<div style="margin-bottom:6px;">{_milestone_pill(label, completed, is_overdue)}</div>'

        tier_status_color = tier["color"] if is_tier_due else "#CBD5E1"
        tier_cols.append(f"""
        <div style="flex:1;min-width:160px;">
          <div style="font-size:10px;font-weight:700;letter-spacing:.08em;color:{tier_status_color};
               text-transform:uppercase;margin-bottom:8px;padding-bottom:6px;
               border-bottom:2px solid {tier_status_color};">{tier['label']}</div>
          {pills_html}
        </div>""")

    tiers_html = "".join(tier_cols)

    border_color = "#FDA4AF" if is_underactivated else "#E2E8F0"
    bg_color = "#FFF9F9" if is_underactivated else "white"

    return f"""
    <div style="background:{bg_color};border:1px solid {border_color};border-radius:12px;
         padding:18px 20px;margin-bottom:10px;">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;flex-wrap:wrap;">
        <span style="font-size:15px;font-weight:700;color:#0F172A;">{row['restaurant_name']}</span>
        {risk_badge}
        {underactivation_badge}
        <span style="font-size:12px;color:#94A3B8;margin-left:auto;">{row['cuisine_type']} &middot;{_tenure_band(months)}</span>
      </div>
      <div style="display:flex;gap:20px;flex-wrap:wrap;">
        {tiers_html}
      </div>
    </div>"""


def export_activation_html(df: pd.DataFrame, path: str):
    today = date.today().strftime("%B %d, %Y")

    # Compute overdue milestones per row
    df = df.copy()
    df["_overdue"] = df.apply(lambda r: _overdue_milestones(r), axis=1)

    total = len(df)
    underactivated = (df["_overdue"].apply(len) > 0).sum()
    on_track = total - underactivated

    # Sort: underactivated first, then by overdue count desc
    df["_overdue_count"] = df["_overdue"].apply(len)
    df = df.sort_values("_overdue_count", ascending=False).reset_index(drop=True)

    cards_html = "".join(
        _restaurant_card(row, row["_overdue"])
        for _, row in df.iterrows()
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Activation Depth Tracker &mdash;{today}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Inter', -apple-system, sans-serif; background: #F8FAFC; color: #0F172A; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 32px 24px; }}
</style>
</head>
<body>

{NAV_HTML}

<div class="container">
  <div style="margin-bottom:28px;">
    <div style="font-size:24px;font-weight:700;color:#0F172A;letter-spacing:-.02em;">Activation Depth Tracker</div>
    <div style="font-size:14px;color:#64748B;margin-top:4px;">
      Which customers are underactivated &mdash;and how far along are they? &middot;{total} restaurants &middot;{today}
    </div>
  </div>

  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:28px;">
    <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;padding:18px 20px;">
      <div style="font-size:12px;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;margin-bottom:6px;">Total Portfolio</div>
      <div style="font-size:28px;font-weight:700;color:#0F172A;">{total}</div>
    </div>
    <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;padding:18px 20px;">
      <div style="font-size:12px;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;margin-bottom:6px;">Underactivated</div>
      <div style="font-size:28px;font-weight:700;color:#F43F5E;">{underactivated}</div>
    </div>
    <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;padding:18px 20px;">
      <div style="font-size:12px;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;margin-bottom:6px;">On Track</div>
      <div style="font-size:28px;font-weight:700;color:#22C55E;">{on_track}</div>
    </div>
    <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;padding:18px 20px;">
      <div style="font-size:12px;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;margin-bottom:6px;">Activation Rate</div>
      <div style="font-size:28px;font-weight:700;color:#0066FF;">{round(on_track/total*100)}%</div>
    </div>
  </div>

  <div style="font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.1em;color:#94A3B8;margin-bottom:12px;">
    Sorted by overdue milestone count &mdash;most critical first
  </div>

  {cards_html}

</div>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Activation report saved -> {path}")


if __name__ == "__main__":
    from scoring import score_restaurants
    df = generate_dataset()

    from generate_data import generate_dataset
    df = generate_dataset()
    df = score_restaurants(df)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "activation_report.html")
    export_activation_html(df, out)
