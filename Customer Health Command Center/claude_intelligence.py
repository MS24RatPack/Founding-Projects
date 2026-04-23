"""
claude_intelligence.py
Calls the Claude API for every At-Risk or Churning restaurant.
Generates:
  1. A 3–5 sentence plain-English brief for the CS rep.
  2. A personalized outreach message draft from the CS rep to the owner.
"""

import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = "claude-opus-4-5"


def _build_prompt(row: dict) -> str:
    drivers = "\n".join(f"  - {d}" for d in row["signal_drivers"])
    trend_direction = "up" if row["order_volume_trend_pct"] > 0 else "down"

    return f"""You are a Customer Success analyst at Owner.com, a platform that helps independent restaurants reduce their reliance on third-party delivery apps and grow direct ordering.

Restaurant profile:
- Name: {row['restaurant_name']}
- Cuisine: {row['cuisine_type']}
- Months on platform: {row['months_on_platform']}
- Churn risk score: {row['churn_risk_score']}/100
- Risk tier: {row['risk_tier']}
- Orders this week: {row['orders_this_week']} (vs {row['orders_last_week']} last week, {trend_direction} {abs(row['order_volume_trend_pct'])}%)
- Direct order rate: {round(row['direct_order_rate'] * 100)}%
- Logins this week: {row['logins_per_week']}
- Features used: {row['features_used']}/{row['total_features']}
- Marketing campaigns (last 30 days): {row['marketing_campaigns_30d']}

Key risk signals:
{drivers}

Generate two outputs. Separate them clearly with the headers below.

**CS BRIEF:**
Write 3–5 sentences explaining why this restaurant is at risk. Write it for a CS rep who needs to understand the situation in 30 seconds without reading a spreadsheet. Be direct and specific to this restaurant's actual numbers. No fluff.

**OUTREACH DRAFT:**
Write a short, personalized message from the CS rep to the restaurant owner. It should feel human and specific to their situation — not a template. Reference their actual usage patterns. Offer one concrete next step. Keep it under 100 words. Sign off as "— [Owner.com CS Team]"."""


def enrich_with_intelligence(df):
    """
    Add 'cs_brief' and 'outreach_draft' columns to the dataframe.
    Only calls the API for At-Risk and Churning restaurants.
    Thriving restaurants get empty strings.
    """
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
        print(f"  [{count}/{total}] Generating intelligence for {row['restaurant_name']} ({row['risk_tier']})...")

        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=600,
                messages=[{"role": "user", "content": _build_prompt(row)}]
            )
            raw = response.content[0].text

            # Parse the two sections
            brief = ""
            draft = ""
            if "**CS BRIEF:**" in raw and "**OUTREACH DRAFT:**" in raw:
                parts = raw.split("**OUTREACH DRAFT:**")
                brief = parts[0].replace("**CS BRIEF:**", "").strip()
                draft = parts[1].strip()
            else:
                # Fallback: use full response as brief
                brief = raw.strip()

            briefs.append(brief)
            drafts.append(draft)

        except Exception as e:
            print(f"    Warning: API call failed for {row['restaurant_name']}: {e}")
            briefs.append("Error generating brief.")
            drafts.append("Error generating outreach draft.")

    df = df.copy()
    df["cs_brief"] = briefs
    df["outreach_draft"] = drafts
    return df


if __name__ == "__main__":
    from generate_data import generate_dataset
    from scoring import score_restaurants

    df = generate_dataset()
    scored = score_restaurants(df)
    # Test on first at-risk restaurant only
    test = scored[scored["risk_tier"].isin(["At-Risk", "Churning"])].head(1)
    result = enrich_with_intelligence(test)
    row = result.iloc[0]
    print(f"\n--- {row['restaurant_name']} ({row['risk_tier']}) ---")
    print("\nCS BRIEF:")
    print(row["cs_brief"])
    print("\nOUTREACH DRAFT:")
    print(row["outreach_draft"])
