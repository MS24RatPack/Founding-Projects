"""
report.py
Generates the weekly churn report as:
  - churn_report.csv  (full data export)
  - churn_report.html (Owner.com-style visual report)
"""

import pandas as pd
from datetime import date

NAV_HTML = """
<div style="background:white;border-bottom:1px solid #E2E8F0;padding:0 40px;display:flex;align-items:center;height:60px;gap:0;">
  <div style="font-size:18px;font-weight:700;color:#0F172A;letter-spacing:-.02em;margin-right:40px;">owner<span style="color:#0066FF;">.</span>com</div>
  <a href="churn_report.html" style="text-decoration:none;padding:0 16px;height:60px;display:flex;align-items:center;font-size:13px;font-weight:500;color:#0066FF;border-bottom:2px solid #0066FF;">Churn Risk</a>
  <a href="activation_report.html" style="text-decoration:none;padding:0 16px;height:60px;display:flex;align-items:center;font-size:13px;font-weight:500;color:#64748B;border-bottom:2px solid transparent;">Activation Depth</a>
  <a href="nrr_model.html" style="text-decoration:none;padding:0 16px;height:60px;display:flex;align-items:center;font-size:13px;font-weight:500;color:#64748B;border-bottom:2px solid transparent;">NRR Scenario</a>
  <a href="intervention_queue.html" style="text-decoration:none;padding:0 16px;height:60px;display:flex;align-items:center;font-size:13px;font-weight:500;color:#64748B;border-bottom:2px solid transparent;">Intervention Queue</a>
</div>
"""

TIER_COLORS = {
    "Thriving": {"bg": "#F0FDF4", "border": "#86EFAC", "badge_bg": "#DCFCE7", "badge_text": "#15803D"},
    "At-Risk":  {"bg": "#FFFBEB", "border": "#FCD34D", "badge_bg": "#FEF3C7", "badge_text": "#B45309"},
    "Churning": {"bg": "#FFF1F2", "border": "#FDA4AF", "badge_bg": "#FFE4E6", "badge_text": "#BE123C"},
}


def export_csv(df: pd.DataFrame, path: str = "churn_report.csv"):
    export_cols = [
        "restaurant_name", "cuisine_type", "risk_tier", "churn_risk_score",
        "orders_this_week", "orders_last_week", "order_volume_trend_pct",
        "direct_order_rate", "logins_per_week", "features_used", "total_features",
        "feature_adoption_rate", "marketing_campaigns_30d", "months_on_platform",
    ]
    df[export_cols].to_csv(path, index=False)
    print(f"CSV saved -> {path}")


def _tier_badge(tier):
    c = TIER_COLORS[tier]
    icons = {"Thriving": "&#9650;", "At-Risk": "&#9888;", "Churning": "&#10005;"}
    return (
        f'<span style="background:{c["badge_bg"]};color:{c["badge_text"]};'
        f'padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;'
        f'letter-spacing:.04em;">{icons[tier]} {tier.upper()}</span>'
    )


def _score_bar(score):
    if score >= 70:
        color = "#F43F5E"
    elif score >= 40:
        color = "#F59E0B"
    else:
        color = "#22C55E"
    return (
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<div style="flex:1;height:6px;background:#F1F5F9;border-radius:3px;">'
        f'<div style="width:{score}%;height:100%;background:{color};border-radius:3px;"></div>'
        f'</div>'
        f'<span style="font-size:13px;font-weight:600;color:#0F172A;min-width:34px;">{score}</span>'
        f'</div>'
    )


def _restaurant_row(row):
    tier = row["risk_tier"]
    c = TIER_COLORS[tier]
    drivers_html = "".join(
        f'<div style="font-size:12px;color:#64748B;padding:3px 0;border-left:2px solid #E2E8F0;padding-left:10px;margin-bottom:4px;">&#9873; {d}</div>'
        for d in row["signal_drivers"]
    )

    # Intelligence section (only for At-Risk / Churning)
    intel_html = ""
    if tier in ("At-Risk", "Churning") and row.get("cs_brief"):
        intel_html = f"""
        <div style="margin-top:16px;display:grid;grid-template-columns:1fr 1fr;gap:16px;">
          <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;padding:14px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:.08em;color:#94A3B8;text-transform:uppercase;margin-bottom:8px;">CS Brief</div>
            <div style="font-size:13px;color:#334155;line-height:1.6;">{row['cs_brief']}</div>
          </div>
          <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;padding:14px;">
            <div style="font-size:10px;font-weight:700;letter-spacing:.08em;color:#94A3B8;text-transform:uppercase;margin-bottom:8px;">Outreach Draft</div>
            <div style="font-size:13px;color:#334155;line-height:1.6;font-style:italic;">{row['outreach_draft']}</div>
          </div>
        </div>"""

    trend_pct = row["order_volume_trend_pct"]
    trend_color = "#16A34A" if trend_pct >= 0 else "#DC2626"
    trend_arrow = "&#8593;" if trend_pct >= 0 else "&#8595;"

    return f"""
    <div style="background:{c['bg']};border:1px solid {c['border']};border-radius:12px;padding:20px;margin-bottom:12px;">
      <div style="display:flex;align-items:flex-start;gap:16px;">
        <div style="flex:1;">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
            <span style="font-size:16px;font-weight:700;color:#0F172A;">{row['restaurant_name']}</span>
            {_tier_badge(tier)}
          </div>
          <div style="font-size:12px;color:#94A3B8;font-weight:500;">{row['cuisine_type']} &middot;{row['months_on_platform']} months on platform</div>
        </div>
        <div style="min-width:180px;">
          <div style="font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;font-weight:600;">Churn Risk</div>
          {_score_bar(row['churn_risk_score'])}
        </div>
      </div>

      <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-top:16px;">
        <div style="background:white;border:1px solid #E2E8F0;border-radius:8px;padding:10px;">
          <div style="font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:.06em;font-weight:600;">Orders/Wk</div>
          <div style="font-size:18px;font-weight:700;color:#0F172A;margin-top:2px;">{row['orders_this_week']}</div>
          <div style="font-size:11px;color:{trend_color};font-weight:600;">{trend_arrow} {abs(trend_pct)}%</div>
        </div>
        <div style="background:white;border:1px solid #E2E8F0;border-radius:8px;padding:10px;">
          <div style="font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:.06em;font-weight:600;">Direct Rate</div>
          <div style="font-size:18px;font-weight:700;color:#0F172A;margin-top:2px;">{round(row['direct_order_rate']*100)}%</div>
          <div style="font-size:11px;color:#94A3B8;">of orders</div>
        </div>
        <div style="background:white;border:1px solid #E2E8F0;border-radius:8px;padding:10px;">
          <div style="font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:.06em;font-weight:600;">Logins/Wk</div>
          <div style="font-size:18px;font-weight:700;color:#0F172A;margin-top:2px;">{row['logins_per_week']}</div>
          <div style="font-size:11px;color:#94A3B8;">sessions</div>
        </div>
        <div style="background:white;border:1px solid #E2E8F0;border-radius:8px;padding:10px;">
          <div style="font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:.06em;font-weight:600;">Features</div>
          <div style="font-size:18px;font-weight:700;color:#0F172A;margin-top:2px;">{row['features_used']}<span style="font-size:12px;color:#94A3B8;">/{row['total_features']}</span></div>
          <div style="font-size:11px;color:#94A3B8;">adopted</div>
        </div>
        <div style="background:white;border:1px solid #E2E8F0;border-radius:8px;padding:10px;">
          <div style="font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:.06em;font-weight:600;">Campaigns</div>
          <div style="font-size:18px;font-weight:700;color:#0F172A;margin-top:2px;">{row['marketing_campaigns_30d']}</div>
          <div style="font-size:11px;color:#94A3B8;">last 30 days</div>
        </div>
      </div>

      <div style="margin-top:14px;">
        <div style="font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;margin-bottom:6px;">Risk Signals</div>
        {drivers_html}
      </div>
      {intel_html}
    </div>"""


def export_html(df: pd.DataFrame, path: str = "churn_report.html"):
    today = date.today().strftime("%B %d, %Y")
    total = len(df)
    churning_count = (df["risk_tier"] == "Churning").sum()
    at_risk_count = (df["risk_tier"] == "At-Risk").sum()
    thriving_count = (df["risk_tier"] == "Thriving").sum()

    rows_html = "".join(_restaurant_row(row) for _, row in df.iterrows())

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Churn Risk Report &mdash;{today}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Inter', -apple-system, sans-serif; background: #F8FAFC; color: #0F172A; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 32px 24px; }}
  .page-header {{ margin-bottom: 28px; }}
  .page-title {{ font-size: 24px; font-weight: 700; color: #0F172A; letter-spacing: -.02em; }}
  .page-sub {{ font-size: 14px; color: #64748B; margin-top: 4px; }}
  .summary-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 28px; }}
  .summary-card {{ background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 18px 20px; }}
  .summary-label {{ font-size: 12px; color: #94A3B8; text-transform: uppercase; letter-spacing: .08em; font-weight: 600; margin-bottom: 6px; }}
  .summary-num {{ font-size: 28px; font-weight: 700; color: #0F172A; }}
  .summary-num.red {{ color: #F43F5E; }}
  .summary-num.amber {{ color: #F59E0B; }}
  .summary-num.green {{ color: #22C55E; }}
  .section-label {{ font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .1em; color: #94A3B8; margin-bottom: 12px; margin-top: 24px; }}
</style>
</head>
<body>

{NAV_HTML}

<div class="container">
  <div class="page-header">
    <div class="page-title">Churn Risk Report</div>
    <div class="page-sub">Portfolio ranked by churn risk &middot;{total} restaurants &middot;Generated {today}</div>
  </div>

  <div class="summary-grid">
    <div class="summary-card">
      <div class="summary-label">Total Portfolio</div>
      <div class="summary-num">{total}</div>
    </div>
    <div class="summary-card">
      <div class="summary-label">Churning</div>
      <div class="summary-num red">{churning_count}</div>
    </div>
    <div class="summary-card">
      <div class="summary-label">At-Risk</div>
      <div class="summary-num amber">{at_risk_count}</div>
    </div>
    <div class="summary-card">
      <div class="summary-label">Thriving</div>
      <div class="summary-num green">{thriving_count}</div>
    </div>
  </div>

  <div class="section-label">Churning &mdash;{churning_count} restaurants</div>
  {"".join(_restaurant_row(row) for _, row in df[df['risk_tier'] == 'Churning'].iterrows())}

  <div class="section-label">At-Risk &mdash;{at_risk_count} restaurants</div>
  {"".join(_restaurant_row(row) for _, row in df[df['risk_tier'] == 'At-Risk'].iterrows())}

  <div class="section-label">Thriving &mdash;{thriving_count} restaurants</div>
  {"".join(_restaurant_row(row) for _, row in df[df['risk_tier'] == 'Thriving'].iterrows())}

</div>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML report saved -> {path}")
