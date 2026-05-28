"""
claude_intelligence.py
Calls the Claude API for every At-Risk or Churning account.
Generates:
  1. A 3–5 sentence plain-English CS brief.
  2. A personalized outreach message draft.
"""

import anthropic
import os
from dotenv import load_dotenv
from config import CS_TEAM_NAME

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = "claude-sonnet-4-6"


def _build_prompt(row: dict) -> str:
    drivers = "\n".join(f"  - {d}" for d in row["signal_drivers"])
    trend_dir = "up" if row["ai_usage_trend_pct"] > 0 else "down"

    return f"""You are a Customer Success analyst at an AI-native SaaS company. Your platform helps teams automate workflows, generate AI-powered outputs, and integrate with the tools they already use.

Account profile:
- Company: {row['company_name']}
- Vertical: {row['vertical']}
- Months on platform: {row['months_on_platform']}
- Churn risk score: {row['churn_risk_score']}/100
- Risk tier: {row['risk_tier']}
- AI generations this week: {row['ai_runs_this_week']} (vs {row['ai_runs_last_week']} last week, {trend_dir} {abs(row['ai_usage_trend_pct'])}%)
- Workflow completion rate: {round(row['workflow_completion_rate'] * 100)}%
- Sessions per week: {row['session_frequency']}
- Integrations connected: {row['integrations_connected']} of {row['total_integrations']} available
- Seat count change: {row['seats_now']} seats now vs {row['seats_prev']} last period

Key risk signals:
{drivers}

Generate two outputs. Separate them with the headers below.

**CS BRIEF:**
Write 3–5 sentences explaining why this account is at risk. Write it for a CS rep who needs to understand the situation in 30 seconds. Be direct and specific to this account's actual numbers. Focus on what's breaking down in their AI adoption journey. No fluff.

**OUTREACH DRAFT:**
Write a short, personalized message from a CS rep to the account's main point of contact. It should feel human and specific — not a template. Reference their actual usage patterns. Offer one concrete next step that will help them get more value. Keep it under 100 words. Sign off as "— {CS_TEAM_NAME}" """


def enrich_with_intelligence(df):
    """Add cs_brief and outreach_draft columns. Only calls API for At-Risk and Churning accounts."""
    briefs = []
    drafts = []

    at_risk_mask = df["risk_tier"].isin(["At-Risk", "Churning"])
    total = at_risk_mask.sum()
    count = 0

    for _, row in df.iterrows():
        if row["risk_tier"] not in ("At-Risk", "Churning"):
            briefs.append("")
            drafts.append("")
            continue

        count += 1
        print(f"  [{count}/{total}] Generating intelligence for {row['company_name']} ({row['risk_tier']})...")

        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=600,
                messages=[{"role": "user", "content": _build_prompt(row.to_dict())}],
            )
            raw = response.content[0].text

            brief, draft = "", ""
            if "**CS BRIEF:**" in raw and "**OUTREACH DRAFT:**" in raw:
                parts = raw.split("**OUTREACH DRAFT:**")
                brief = parts[0].replace("**CS BRIEF:**", "").strip()
                draft = parts[1].strip()
            else:
                brief = raw.strip()

            briefs.append(brief)
            drafts.append(draft)

        except Exception as e:
            print(f"    Warning: API call failed for {row['company_name']}: {e}")
            briefs.append("Error generating brief.")
            drafts.append("Error generating outreach draft.")

    df = df.copy()
    df["cs_brief"] = briefs
    df["outreach_draft"] = drafts
    return df


if __name__ == "__main__":
    from generate_data import generate_dataset
    from scoring import score_accounts

    df = generate_dataset()
    df = score_accounts(df)
    test = df[df["risk_tier"].isin(["At-Risk", "Churning"])].head(1)
    result = enrich_with_intelligence(test)
    row = result.iloc[0]
    print(f"\n--- {row['company_name']} ({row['risk_tier']}) ---")
    print("\nCS BRIEF:")
    print(row["cs_brief"])
    print("\nOUTREACH DRAFT:")
    print(row["outreach_draft"])
