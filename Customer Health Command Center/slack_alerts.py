"""
slack_alerts.py
Slack webhook alerting agent.
Posts a daily customer health digest to a configured Slack channel.

Requires SLACK_WEBHOOK_URL in .env. If not set, logs a warning and skips gracefully.
Uses only Python stdlib — no new dependencies.
"""

import json
import urllib.request
import urllib.error
from datetime import date
from config import SLACK_WEBHOOK_URL, INTERVENTION_THRESHOLD


def _intervention_action(row) -> str:
    """Return a one-line recommended action based on top signal driver."""
    drivers = row.get("signal_drivers", [])
    top = drivers[0] if drivers else ""

    if "AI generation volume" in top or "AI usage" in top:
        return "Schedule a check-in call to understand AI usage blockers"
    if "workflow completion" in top:
        return "Share workflow quick-start guide and offer a live walkthrough"
    if "login" in top or "session" in top:
        return "Re-engage with a personalized value recap email"
    if "integration" in top:
        return "Send integration setup guide + offer a setup call"
    if "seat" in top:
        return "Flag for expansion risk review before renewal"
    return "Review account health and schedule proactive outreach"


def send_slack_digest(df, intervention_items: list) -> bool:
    """
    Post a daily health digest to Slack.
    Returns True if sent, False if skipped or failed.
    """
    if not SLACK_WEBHOOK_URL:
        print("  [Slack] No SLACK_WEBHOOK_URL configured — skipping alert.")
        return False

    today = date.today().strftime("%B %d, %Y")
    total = len(df)
    thriving = (df["risk_tier"] == "Thriving").sum()
    at_risk  = (df["risk_tier"] == "At-Risk").sum()
    churning = (df["risk_tier"] == "Churning").sum()

    arr_at_risk = df[df["churn_risk_score"] >= INTERVENTION_THRESHOLD]["contract_value_mo"].sum()

    # Top 3 accounts needing attention
    top_accounts = []
    for item in intervention_items[:3]:
        row = item["row"]
        action = _intervention_action(row)
        drivers = row.get("signal_drivers", ["unknown signal"])
        top_accounts.append(
            f"• *{row['company_name']}* ({row['vertical']}) — score: {row['churn_risk_score']} — "
            f"{drivers[0]} → _{action}_"
        )

    accounts_text = "\n".join(top_accounts) if top_accounts else "_No accounts above intervention threshold._"

    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 Daily Customer Health Digest — {today}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Thriving*\n✅ {thriving} accounts"},
                    {"type": "mrkdwn", "text": f"*At-Risk*\n⚠️ {at_risk} accounts"},
                    {"type": "mrkdwn", "text": f"*Churning*\n🔴 {churning} accounts"},
                    {"type": "mrkdwn", "text": f"*Revenue at Risk*\n💸 ${arr_at_risk:,}/mo"},
                ],
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Top accounts needing attention:*\n{accounts_text}",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Run `python main.py` to regenerate the full dashboard. "
                                f"Total portfolio: {total} accounts.",
                    }
                ],
            },
        ]
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            SLACK_WEBHOOK_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                print(f"  [Slack] Digest posted successfully.")
                return True
            else:
                print(f"  [Slack] Unexpected response: {resp.status}")
                return False
    except urllib.error.URLError as e:
        print(f"  [Slack] Failed to post digest: {e}")
        return False
