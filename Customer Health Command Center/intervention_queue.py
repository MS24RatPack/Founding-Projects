"""
intervention_queue.py
V2: Agentic Intervention Loop

For every restaurant with churn_risk_score >= THRESHOLD:
  1. Diagnose which activation milestones are incomplete
  2. Select intervention tier (Red = urgent save-play, Yellow = gentle re-engagement)
  3. Draft a personalized outreach email via Claude API
  4. Render the Daily Intervention Queue as intervention_queue.html
"""

import os
import anthropic
from datetime import date
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

THRESHOLD   = 65   # churn_risk_score >= this enters the queue
RED_CUTOFF  = 75   # churn_risk_score >= this = Red tier (urgent)
MODEL       = "claude-sonnet-4-20250514"
MRR_AT_RISK = 499  # $ per account for revenue-at-risk estimate

SYSTEM_PROMPT = """You are a customer success assistant for a restaurant SaaS platform. Write short, warm, specific outreach emails to restaurant owners who appear to be underusing the platform. Reference the specific feature they have not yet activated. Keep emails under 150 words. Never sound automated."""

from generate_data import MILESTONES

NAV_HTML = """
<div style="background:white;border-bottom:1px solid #E2E8F0;padding:0 40px;display:flex;align-items:center;height:60px;gap:0;">
  <div style="font-size:18px;font-weight:700;color:#0F172A;letter-spacing:-.02em;margin-right:40px;">owner<span style="color:#0066FF;">.</span>com</div>
  <a href="churn_report.html" style="text-decoration:none;padding:0 16px;height:60px;display:flex;align-items:center;font-size:13px;font-weight:500;color:#64748B;border-bottom:2px solid transparent;">Churn Risk</a>
  <a href="activation_report.html" style="text-decoration:none;padding:0 16px;height:60px;display:flex;align-items:center;font-size:13px;font-weight:500;color:#64748B;border-bottom:2px solid transparent;">Activation Depth</a>
  <a href="nrr_model.html" style="text-decoration:none;padding:0 16px;height:60px;display:flex;align-items:center;font-size:13px;font-weight:500;color:#64748B;border-bottom:2px solid transparent;">NRR Scenario</a>
  <a href="intervention_queue.html" style="text-decoration:none;padding:0 16px;height:60px;display:flex;align-items:center;font-size:13px;font-weight:500;color:#0066FF;border-bottom:2px solid #0066FF;">Intervention Queue</a>
</div>
"""


def _intervention_tier(score: float) -> str:
    return "Red" if score >= RED_CUTOFF else "Yellow"


def _incomplete_milestones(row) -> list[tuple[str, str]]:
    """Return (col, label) pairs for milestones that are due but not completed."""
    incomplete = []
    for col, label, due_month in MILESTONES:
        if row["months_on_platform"] >= due_month and not row[col]:
            incomplete.append((col, label))
    return incomplete


def _draft_email(row, tier: str, gaps: list[tuple[str, str]]) -> str:
    """Call Claude API to draft the intervention email."""
    gap_labels = [label for _, label in gaps]
    gap_str = ", ".join(gap_labels) if gap_labels else "general platform engagement"

    urgency = (
        "This is a high-urgency situation &mdash;the restaurant is showing critical churn signals "
        "and needs an immediate, warm save play."
        if tier == "Red"
        else "This is a gentle re-engagement &mdash;the restaurant is slipping but not yet critical."
    )

    user_msg = f"""Draft an outreach email for the following restaurant:

Restaurant: {row['restaurant_name']} ({row['cuisine_type']})
Months on platform: {row['months_on_platform']}
Churn risk tier: {tier} (score: {row['churn_risk_score']}/100)
Features not yet activated: {gap_str}
Context: {urgency}

Write the email from a CS rep's perspective. Address the owner directly. Reference 1-2 specific unactivated features by name. End with a clear, low-friction next step."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    return response.content[0].text.strip()


def _tier_colors(tier: str) -> dict:
    if tier == "Red":
        return {
            "border": "#FDA4AF",
            "bg": "#FFF1F2",
            "badge_bg": "#FFE4E6",
            "badge_text": "#BE123C",
            "label": "Urgent Save-Play",
            "icon": "&#x1F534;",
            "pill_bg": "#FEE2E2",
            "pill_text": "#991B1B",
        }
    return {
        "border": "#FCD34D",
        "bg": "#FFFBEB",
        "badge_bg": "#FEF3C7",
        "badge_text": "#B45309",
        "label": "Gentle Re-Engagement",
        "icon": "&#x1F7E1;",
        "pill_bg": "#FEF3C7",
        "pill_text": "#92400E",
    }


def _score_bar(score: float) -> str:
    color = "#F43F5E" if score >= RED_CUTOFF else "#F59E0B"
    return (
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<div style="flex:1;height:6px;background:#F1F5F9;border-radius:3px;min-width:80px;">'
        f'<div style="width:{score}%;height:100%;background:{color};border-radius:3px;"></div>'
        f'</div>'
        f'<span style="font-size:13px;font-weight:700;color:#0F172A;min-width:32px;">{score}</span>'
        f'</div>'
    )


def _intervention_card(row, tier: str, gaps: list, email: str) -> str:
    c = _tier_colors(tier)
    gap_pills = "".join(
        f'<span style="background:{c["pill_bg"]};color:{c["pill_text"]};padding:3px 9px;'
        f'border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap;">&#10005; {label}</span> '
        for _, label in gaps
    ) or '<span style="color:#94A3B8;font-size:12px;">No specific gaps flagged</span>'

    email_escaped = email.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")

    return f"""
    <div style="background:{c['bg']};border:1px solid {c['border']};border-radius:12px;
         padding:20px 22px;margin-bottom:14px;">

      <!-- Header row -->
      <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:14px;flex-wrap:wrap;">
        <div style="flex:1;">
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:4px;">
            <span style="font-size:16px;font-weight:700;color:#0F172A;">{row['restaurant_name']}</span>
            <span style="background:{c['badge_bg']};color:{c['badge_text']};padding:3px 10px;
              border-radius:20px;font-size:11px;font-weight:600;">{c['icon']} {c['label'].upper()}</span>
          </div>
          <div style="font-size:12px;color:#94A3B8;">{row['cuisine_type']} &middot; {row['months_on_platform']} months on platform</div>
        </div>
        <div style="min-width:180px;">
          <div style="font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em;
               font-weight:600;margin-bottom:6px;">Churn Risk Score</div>
          {_score_bar(row['churn_risk_score'])}
        </div>
      </div>

      <!-- Activation gaps -->
      <div style="margin-bottom:14px;">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
             color:#94A3B8;margin-bottom:8px;">Diagnosed Activation Gaps</div>
        <div style="display:flex;flex-wrap:wrap;gap:6px;">{gap_pills}</div>
      </div>

      <!-- Signal drivers -->
      <div style="margin-bottom:16px;">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
             color:#94A3B8;margin-bottom:6px;">Risk Signals</div>
        {"".join(f'<div style="font-size:12px;color:#64748B;padding:2px 0 2px 10px;border-left:2px solid #E2E8F0;margin-bottom:3px;">- {d}</div>' for d in row.get("signal_drivers", []))}
      </div>

      <!-- Drafted email (collapsible) -->
      <details style="background:white;border:1px solid #E2E8F0;border-radius:8px;">
        <summary style="display:flex;justify-content:space-between;align-items:center;padding:12px 16px;
                        cursor:pointer;list-style:none;user-select:none;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="font-size:11px;color:#94A3B8;transition:transform .2s;" class="chevron">&#9654;</span>
            <span style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#94A3B8;">
              Drafted Outreach Email
            </span>
          </div>
          <button onclick="event.preventDefault();event.stopPropagation();copyEmail(this)"
            data-text="{email.replace(chr(10), chr(92) + 'n').replace(chr(34), '&quot;')}"
            style="background:#0066FF;color:white;border:none;border-radius:6px;padding:5px 12px;
                   font-size:11px;font-weight:600;cursor:pointer;font-family:inherit;">
            Copy
          </button>
        </summary>
        <div style="padding:0 16px 16px;border-top:1px solid #F1F5F9;">
          <div style="font-size:13px;color:#334155;line-height:1.7;white-space:pre-wrap;padding-top:12px;">{email_escaped}</div>
        </div>
      </details>

    </div>"""


def build_intervention_queue(df, skip_ai: bool = False) -> list[dict]:
    """
    Filter, diagnose, and enrich at-risk restaurants.
    Returns list of dicts with tier, gaps, and email.
    """
    queue = df[df["churn_risk_score"] >= THRESHOLD].copy()
    queue = queue.sort_values("churn_risk_score", ascending=False).reset_index(drop=True)

    total = len(queue)
    results = []

    for i, (_, row) in enumerate(queue.iterrows()):
        tier = _intervention_tier(row["churn_risk_score"])
        gaps = _incomplete_milestones(row)

        if skip_ai:
            email = "[Email draft skipped &mdash;run without --skip-ai to generate]"
        else:
            print(f"  [{i+1}/{total}] Drafting email for {row['restaurant_name']} ({tier})...")
            try:
                email = _draft_email(row, tier, gaps)
            except Exception as e:
                email = f"Error generating email: {e}"

        results.append({
            "row": row,
            "tier": tier,
            "gaps": gaps,
            "email": email,
        })

    return results


def export_intervention_html(df, path: str, skip_ai: bool = False):
    today = date.today().strftime("%B %d, %Y")

    print(f"\n  Building intervention queue (threshold: {THRESHOLD})...")
    items = build_intervention_queue(df, skip_ai=skip_ai)

    total_at_risk = len(items)
    revenue_at_risk = total_at_risk * MRR_AT_RISK
    red_count    = sum(1 for i in items if i["tier"] == "Red")
    yellow_count = sum(1 for i in items if i["tier"] == "Yellow")

    cards_html = "".join(
        _intervention_card(i["row"], i["tier"], i["gaps"], i["email"])
        for i in items
    )

    if not items:
        cards_html = '<div style="text-align:center;color:#94A3B8;padding:48px;font-size:14px;">No restaurants above the intervention threshold this week.</div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Daily Intervention Queue &mdash;{today}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Inter', -apple-system, sans-serif; background: #F8FAFC; color: #0F172A; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 32px 24px; }}
  .copy-toast {{
    position: fixed; bottom: 24px; right: 24px;
    background: #0F172A; color: white;
    padding: 10px 18px; border-radius: 8px;
    font-size: 13px; font-weight: 500;
    opacity: 0; transform: translateY(8px);
    transition: all .2s ease; pointer-events: none;
  }}
  .copy-toast.show {{ opacity: 1; transform: translateY(0); }}
</style>
</head>
<body>

{NAV_HTML}

<div class="container">

  <!-- Page header -->
  <div style="margin-bottom:28px;">
    <div style="font-size:24px;font-weight:700;color:#0F172A;letter-spacing:-.02em;">Daily Intervention Queue</div>
    <div style="font-size:14px;color:#64748B;margin-top:4px;">
      Accounts above risk threshold &middot; Emails ready to send &middot; Generated {today}
    </div>
  </div>

  <!-- Summary stats -->
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:28px;">
    <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;padding:18px 20px;">
      <div style="font-size:12px;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;margin-bottom:6px;">At-Risk Accounts</div>
      <div style="font-size:28px;font-weight:700;color:#0F172A;">{total_at_risk}</div>
      <div style="font-size:12px;color:#94A3B8;margin-top:2px;">score &ge; {THRESHOLD}</div>
    </div>
    <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;padding:18px 20px;">
      <div style="font-size:12px;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;margin-bottom:6px;">Revenue at Risk</div>
      <div style="font-size:28px;font-weight:700;color:#F43F5E;">${revenue_at_risk:,}</div>
      <div style="font-size:12px;color:#94A3B8;margin-top:2px;">${MRR_AT_RISK}/mo per account</div>
    </div>
    <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;padding:18px 20px;">
      <div style="font-size:12px;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;margin-bottom:6px;">Urgent Save-Play</div>
      <div style="font-size:28px;font-weight:700;color:#BE123C;">{red_count}</div>
      <div style="font-size:12px;color:#94A3B8;margin-top:2px;">score &ge; {RED_CUTOFF}</div>
    </div>
    <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;padding:18px 20px;">
      <div style="font-size:12px;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;margin-bottom:6px;">Gentle Re-Engagement</div>
      <div style="font-size:28px;font-weight:700;color:#B45309;">{yellow_count}</div>
      <div style="font-size:12px;color:#94A3B8;margin-top:2px;">score 65&ndash;74</div>
    </div>
  </div>

  <!-- Queue -->
  <div style="font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.1em;color:#94A3B8;margin-bottom:12px;">
    Sorted by highest risk first &mdash;{total_at_risk} accounts
  </div>

  {cards_html}

</div>

<div class="copy-toast" id="toast">Copied to clipboard</div>

<script>
function copyEmail(btn) {{
  const text = btn.getAttribute('data-text').replace(/\\n/g, '\n');
  navigator.clipboard.writeText(text).then(() => {{
    const toast = document.getElementById('toast');
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2000);
  }});
}}
</script>

</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Intervention queue saved -> {path}")
