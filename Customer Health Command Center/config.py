"""
config.py
Single source of truth for all configurable values.
Update this file to adapt the tool to a different AI-native SaaS product.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Product identity ---
PRODUCT_NAME = "Pulse"
CS_TEAM_NAME = "Customer Success"

# --- Verticals (exactly 4) ---
VERTICALS = ["Fintech", "Healthtech", "HR & People Ops", "DevTools"]

# --- Churn scoring signals ---
# Weights must sum to 1.0. Bounds: min = worst/riskiest, max = best/healthiest.
# Column names must match columns produced by generate_data.py.
SCORING_SIGNALS = {
    "ai_usage_trend_pct": {
        "weight": 0.30,
        "label": "AI Usage Trend",
        "bounds": {"min": -60, "max": 30},
    },
    "workflow_completion_rate": {
        "weight": 0.25,
        "label": "Workflow Completion",
        "bounds": {"min": 0.0, "max": 1.0},
    },
    "session_frequency": {
        "weight": 0.20,
        "label": "Session Frequency",
        "bounds": {"min": 0, "max": 14},
    },
    "integration_depth": {
        "weight": 0.15,
        "label": "Integration Depth",
        "bounds": {"min": 0.0, "max": 1.0},
    },
    "seat_expansion": {
        "weight": 0.10,
        "label": "Seat / API Growth",
        "bounds": {"min": -0.5, "max": 0.5},
    },
}

# --- Risk tiers ---
TIER_THRESHOLDS = {
    "Churning": 70,  # score >= 70
    "At-Risk":  40,  # score 40–69
    "Thriving":  0,  # score < 40
}

# --- Activation milestones ---
# tier_days: account must have been active at least this many days for milestone to be "due"
ACTIVATION_MILESTONES = [
    {"id": "m_first_ai_output",       "label": "First AI generation",         "tier_days": 7},
    {"id": "m_workspace_configured",  "label": "Workspace fully configured",  "tier_days": 7},
    {"id": "m_first_workflow",        "label": "First workflow automated",     "tier_days": 30},
    {"id": "m_integration_connected", "label": "First integration connected", "tier_days": 30},
    {"id": "m_team_member_added",     "label": "Second seat / API key added", "tier_days": 60},
    {"id": "m_volume_threshold",      "label": "10+ AI outputs generated",    "tier_days": 60},
    {"id": "m_second_use_case",       "label": "Expanded to second use case", "tier_days": 90},
    {"id": "m_output_shared",         "label": "AI output shared externally", "tier_days": 90},
]

# Target days to complete each milestone (for TTV benchmark column)
MILESTONE_TTV_TARGETS = {
    "m_first_ai_output":       3,
    "m_workspace_configured":  5,
    "m_first_workflow":        14,
    "m_integration_connected": 21,
    "m_team_member_added":     45,
    "m_volume_threshold":      30,
    "m_second_use_case":       75,
    "m_output_shared":         60,
}

# Activation tier display groups (for the Activation tab header bands)
ACTIVATION_TIER_BANDS = [
    {"label": "Days 1–7",   "tier_days": 7,  "color": "#3B82F6"},
    {"label": "Days 8–30",  "tier_days": 30, "color": "#8B5CF6"},
    {"label": "Days 31–60", "tier_days": 60, "color": "#F59E0B"},
    {"label": "Days 61–90", "tier_days": 90, "color": "#10B981"},
]

# --- Intervention thresholds ---
INTERVENTION_THRESHOLD = 65  # churn_risk_score >= this enters the queue
RED_CUTOFF = 75              # score >= this = Red tier (urgent)

# --- Contract value ranges by vertical (monthly USD) ---
CONTRACT_VALUE_RANGES = {
    "Fintech":         {"min": 800,  "max": 1500},
    "Healthtech":      {"min": 600,  "max": 1200},
    "HR & People Ops": {"min": 400,  "max": 900},
    "DevTools":        {"min": 300,  "max": 700},
}

# --- NRR model ---
NRR_TARGET = 1.10           # 110% target
NRR_GROSS_RETENTION = 0.88  # 88% gross retention assumption

# Expansion levers (AI-native SaaS)
NRR_LEVERS = [
    {
        "id":        "lever_seats",
        "label":     "Enterprise Seat Expansion",
        "desc":      "% of customers who add a seat pack (5+ seats) · $299/mo per pack",
        "mo_value":  299,
        "max_pct":   60,
        "color":     "#3B82F6",
        "bd_label":  "+ Seat packs",
    },
    {
        "id":        "lever_api",
        "label":     "API / Integration Tier Attach",
        "desc":      "% of customers upgrading to API access tier · $199/mo",
        "mo_value":  199,
        "max_pct":   50,
        "color":     "#8B5CF6",
        "bd_label":  "+ API tier",
    },
    {
        "id":        "lever_advanced",
        "label":     "Advanced AI Features Tier",
        "desc":      "% of customers on advanced AI tier (custom models, higher limits) · $399/mo",
        "mo_value":  399,
        "max_pct":   40,
        "color":     "#10B981",
        "bd_label":  "+ Advanced AI",
    },
]

# --- Slack ---
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# --- Snapshot file for week-over-week comparison ---
SNAPSHOT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".health_snapshot.json")
