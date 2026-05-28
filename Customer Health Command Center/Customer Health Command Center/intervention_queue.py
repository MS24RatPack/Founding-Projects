"""
intervention_queue.py
Agentic intervention loop — data and email drafting only.
HTML rendering is handled by dashboard.py.

For every account with churn_risk_score >= THRESHOLD:
  1. Diagnose which activation milestones are incomplete
  2. Assign intervention tier (Red = urgent, Yellow = gentle re-engagement)
  3. Draft a personalized outreach email via Claude API
"""

import anthropic
import os
from dotenv import load_dotenv
from config import (
    ACTIVATION_MILESTONES,
    INTERVENTION_THRESHOLD,
    RED_CUTOFF,
    CS_TEAM_NAME,
)

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = f"""You are a customer success assistant at an AI-native SaaS company. \
Write short, warm, specific outreach emails to team leads who appear to be underusing the platform. \
Reference the specific activation step they have not yet completed. \
Keep emails under 150 words. Never sound automated. Sign off as "— {CS_TEAM_NAME}"."""


def _intervention_tier(score: float) -> str:
    return "Red" if score >= RED_CUTOFF else "Yellow"


def _incomplete_milestones(row) -> list[tuple[str, str]]:
    """Return (id, label) pairs for milestones that are due but not completed."""
    incomplete = []
    days = row["days_on_platform"]
    for m in ACTIVATION_MILESTONES:
        if days >= m["tier_days"] and not row.get(m["id"], False):
            incomplete.append((m["id"], m["label"]))
    return incomplete


def _draft_email(row, tier: str, gaps: list[tuple[str, str]]) -> str:
    gap_labels = [label for _, label in gaps]
    gap_str = ", ".join(gap_labels) if gap_labels else "general platform engagement"

    urgency = (
        "This is a high-urgency situation — the account is showing critical churn signals "
        "and needs an immediate, warm save play."
        if tier == "Red"
        else "This is a gentle re-engagement — the account is slipping but not yet critical."
    )

    user_msg = f"""Draft an outreach email for the following account:

Company: {row['company_name']} ({row['vertical']})
Months on platform: {row['months_on_platform']}
Churn risk tier: {tier} (score: {row['churn_risk_score']}/100)
AI usage this week: {row['ai_runs_this_week']} generations (vs {row['ai_runs_last_week']} last week)
Workflow completion rate: {round(row['workflow_completion_rate'] * 100)}%
Activation steps not yet completed: {gap_str}
Context: {urgency}

Write the email from a CS rep's perspective. Address the team's main point of contact directly. \
Reference 1–2 specific incomplete activation steps by name. End with a clear, low-friction next step."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    return response.content[0].text.strip()


def build_intervention_queue(df, skip_ai: bool = False) -> list[dict]:
    """
    Filter, diagnose, and enrich at-risk accounts.
    Returns a list of dicts with: row, tier, gaps, email.
    """
    queue = df[df["churn_risk_score"] >= INTERVENTION_THRESHOLD].copy()
    queue = queue.sort_values("churn_risk_score", ascending=False).reset_index(drop=True)

    total = len(queue)
    results = []

    for i, (_, row) in enumerate(queue.iterrows()):
        tier = _intervention_tier(row["churn_risk_score"])
        gaps = _incomplete_milestones(row)

        if skip_ai:
            email = "[Email draft skipped — run without --skip-ai to generate]"
        else:
            print(f"  [{i+1}/{total}] Drafting email for {row['company_name']} ({tier})...")
            try:
                email = _draft_email(row, tier, gaps)
            except Exception as e:
                email = f"Error generating email: {e}"

        results.append({
            "row":   row,
            "tier":  tier,
            "gaps":  gaps,
            "email": email,
        })

    return results
