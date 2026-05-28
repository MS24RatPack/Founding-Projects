"""
generate_data.py
Creates a mock dataset of 50 AI-native SaaS accounts across 4 verticals
with weekly behavioral signals and activation milestone completion flags.
Produces realistic variance: healthy, at-risk, and churning cohorts.
"""

import random
import pandas as pd
from config import ACTIVATION_MILESTONES, VERTICALS, CONTRACT_VALUE_RANGES

random.seed(42)

TOTAL_INTEGRATIONS = 10  # integrations available on the platform

COMPANIES = [
    # Fintech (13)
    ("ClearLedger",     "Fintech"),
    ("VaultAI",         "Fintech"),
    ("FinSight Pro",    "Fintech"),
    ("Underwrite AI",   "Fintech"),
    ("Reconcile.ai",    "Fintech"),
    ("ComplianceIQ",    "Fintech"),
    ("TradePilot",      "Fintech"),
    ("AuditFlow",       "Fintech"),
    ("RiskRadar",       "Fintech"),
    ("ClaimBot",        "Fintech"),
    ("FraudGuard AI",   "Fintech"),
    ("LoanLogic",       "Fintech"),
    ("ReserveAI",       "Fintech"),
    # Healthtech (12)
    ("CareSignal",      "Healthtech"),
    ("DiagnoseAI",      "Healthtech"),
    ("ChartFlow",       "Healthtech"),
    ("PriorAuth AI",    "Healthtech"),
    ("ClinicalCopilot", "Healthtech"),
    ("MedScribe",       "Healthtech"),
    ("PathwayIQ",       "Healthtech"),
    ("TriageBot",       "Healthtech"),
    ("RxAssist",        "Healthtech"),
    ("NoteFlow",        "Healthtech"),
    ("OutcomeAI",       "Healthtech"),
    ("BillingPulse",    "Healthtech"),
    # HR & People Ops (13)
    ("HireBot AI",      "HR & People Ops"),
    ("PolicyPilot",     "HR & People Ops"),
    ("PerfReview AI",   "HR & People Ops"),
    ("OnboardIQ",       "HR & People Ops"),
    ("CompBench AI",    "HR & People Ops"),
    ("EngagePulse",     "HR & People Ops"),
    ("ScreenAI",        "HR & People Ops"),
    ("OfferLogic",      "HR & People Ops"),
    ("RetentionBot",    "HR & People Ops"),
    ("SkillMap AI",     "HR & People Ops"),
    ("HeadcountIQ",     "HR & People Ops"),
    ("PayScale AI",     "HR & People Ops"),
    ("CultureBot",      "HR & People Ops"),
    # DevTools (12)
    ("CodeScan AI",     "DevTools"),
    ("ReviewBot",       "DevTools"),
    ("DeployPilot",     "DevTools"),
    ("IncidentIQ",      "DevTools"),
    ("DocsFlow AI",     "DevTools"),
    ("TestGen",         "DevTools"),
    ("SecurityScan AI", "DevTools"),
    ("MonitorPulse",    "DevTools"),
    ("CIAssist",        "DevTools"),
    ("RefactorBot",     "DevTools"),
    ("PipelineAI",      "DevTools"),
    ("DebugFlow",       "DevTools"),
]


def _contract_value(vertical: str) -> int:
    r = CONTRACT_VALUE_RANGES[vertical]
    return random.randint(r["min"], r["max"])


def _activation_milestones(days_on_platform: int, health: str) -> dict:
    """Generate realistic milestone completion based on tenure and health tier."""
    p_base = {"healthy": 0.92, "at_risk": 0.60, "churning": 0.28}[health]
    result = {}
    for m in ACTIVATION_MILESTONES:
        if days_on_platform < m["tier_days"]:
            result[m["id"]] = False
        else:
            days_overdue = days_on_platform - m["tier_days"]
            p = min(0.97, p_base + days_overdue * 0.001)
            result[m["id"]] = random.random() < p
    return result


def _healthy(name: str, vertical: str) -> dict:
    months = random.randint(8, 36)
    days = months * 30
    seats_prev = random.randint(5, 15)
    seats_now = seats_prev + random.randint(0, 4)
    ai_prev = random.randint(180, 350)
    ai_now = ai_prev + random.randint(-10, 40)
    integrations = random.randint(4, 9)

    record = {
        "company_name":           name,
        "vertical":               vertical,
        "months_on_platform":     months,
        "days_on_platform":       days,
        "contract_value_mo":      _contract_value(vertical),
        "ai_runs_this_week":      ai_now,
        "ai_runs_last_week":      ai_prev,
        "workflow_completion_rate": round(random.uniform(0.65, 0.95), 2),
        "sessions_per_week":      random.randint(6, 14),
        "integrations_connected": integrations,
        "total_integrations":     TOTAL_INTEGRATIONS,
        "seats_now":              seats_now,
        "seats_prev":             seats_prev,
    }
    record.update(_activation_milestones(days, "healthy"))
    return record


def _at_risk(name: str, vertical: str) -> dict:
    months = random.randint(3, 18)
    days = months * 30
    seats_prev = random.randint(3, 10)
    seats_now = seats_prev + random.randint(-1, 1)
    ai_prev = random.randint(80, 200)
    ai_now = ai_prev - random.randint(15, 70)

    record = {
        "company_name":           name,
        "vertical":               vertical,
        "months_on_platform":     months,
        "days_on_platform":       days,
        "contract_value_mo":      _contract_value(vertical),
        "ai_runs_this_week":      max(ai_now, 5),
        "ai_runs_last_week":      ai_prev,
        "workflow_completion_rate": round(random.uniform(0.25, 0.50), 2),
        "sessions_per_week":      random.randint(2, 5),
        "integrations_connected": random.randint(1, 4),
        "total_integrations":     TOTAL_INTEGRATIONS,
        "seats_now":              max(seats_now, 1),
        "seats_prev":             seats_prev,
    }
    record.update(_activation_milestones(days, "at_risk"))
    return record


def _churning(name: str, vertical: str) -> dict:
    months = random.randint(2, 12)
    days = months * 30
    seats_prev = random.randint(2, 8)
    seats_now = max(1, seats_prev - random.randint(0, 3))
    ai_prev = random.randint(30, 120)
    ai_now = max(1, ai_prev - random.randint(30, 100))

    record = {
        "company_name":           name,
        "vertical":               vertical,
        "months_on_platform":     months,
        "days_on_platform":       days,
        "contract_value_mo":      _contract_value(vertical),
        "ai_runs_this_week":      ai_now,
        "ai_runs_last_week":      ai_prev,
        "workflow_completion_rate": round(random.uniform(0.05, 0.28), 2),
        "sessions_per_week":      random.randint(0, 2),
        "integrations_connected": random.randint(0, 2),
        "total_integrations":     TOTAL_INTEGRATIONS,
        "seats_now":              seats_now,
        "seats_prev":             seats_prev,
    }
    record.update(_activation_milestones(days, "churning"))
    return record


MILESTONE_IDS = [m["id"] for m in ACTIVATION_MILESTONES]

REQUIRED_CSV_COLUMNS = [
    "company_name", "vertical", "months_on_platform", "contract_value_mo",
    "ai_runs_this_week", "ai_runs_last_week", "workflow_completion_rate",
    "sessions_per_week", "integrations_connected", "total_integrations",
    "seats_now", "seats_prev",
] + MILESTONE_IDS


def _derive_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Compute derived scoring columns from raw CSV/generated inputs."""
    df["days_on_platform"] = df["months_on_platform"] * 30
    df["ai_usage_trend_pct"] = (
        (df["ai_runs_this_week"] - df["ai_runs_last_week"]) / df["ai_runs_last_week"].clip(lower=1) * 100
    ).round(1)
    df["session_frequency"]  = df["sessions_per_week"]
    df["integration_depth"]  = (df["integrations_connected"] / df["total_integrations"].clip(lower=1)).round(3)
    df["seat_expansion"]     = (
        (df["seats_now"] - df["seats_prev"]) / df["seats_prev"].clip(lower=1)
    ).round(3)
    return df


def load_from_csv(path: str) -> pd.DataFrame:
    """
    Load account data from a CSV file and return a scored-ready DataFrame.
    The CSV must contain the columns listed in REQUIRED_CSV_COLUMNS.
    Milestone columns should be True/False or 1/0.
    """
    df = pd.read_csv(path)

    missing = [c for c in REQUIRED_CSV_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")

    # Normalise boolean milestone columns
    for mid in MILESTONE_IDS:
        df[mid] = df[mid].astype(str).str.strip().str.lower().isin(["true", "1", "yes"])

    df["months_on_platform"]    = df["months_on_platform"].astype(int)
    df["contract_value_mo"]     = df["contract_value_mo"].astype(int)
    df["ai_runs_this_week"]     = df["ai_runs_this_week"].astype(int)
    df["ai_runs_last_week"]     = df["ai_runs_last_week"].astype(int)
    df["sessions_per_week"]     = df["sessions_per_week"].astype(int)
    df["integrations_connected"]= df["integrations_connected"].astype(int)
    df["total_integrations"]    = df["total_integrations"].astype(int)
    df["seats_now"]             = df["seats_now"].astype(int)
    df["seats_prev"]            = df["seats_prev"].astype(int)

    return _derive_signals(df)


def generate_dataset() -> pd.DataFrame:
    records = []
    shuffled = COMPANIES[:]
    random.shuffle(shuffled)

    # 20 healthy, 20 at-risk, 10 churning
    for name, vertical in shuffled[:20]:
        records.append(_healthy(name, vertical))
    for name, vertical in shuffled[20:40]:
        records.append(_at_risk(name, vertical))
    for name, vertical in shuffled[40:50]:
        records.append(_churning(name, vertical))

    df = pd.DataFrame(records)
    return _derive_signals(df)


if __name__ == "__main__":
    df = generate_dataset()
    print(df[["company_name", "vertical", "contract_value_mo", "churn_risk_score" if "churn_risk_score" in df.columns else "ai_usage_trend_pct"]].to_string(index=False))
    print(f"\n{len(df)} companies generated.")
