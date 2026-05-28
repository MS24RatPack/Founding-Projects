"""
main.py
Orchestrates the full Customer Health Command Center pipeline.

Usage:
  python main.py                        # Full run with AI + Slack
  python main.py --skip-ai              # Skip Claude API calls (faster, no cost)
  python main.py --skip-slack           # Skip Slack alert
  python main.py --skip-ai --skip-slack # Fastest, no external calls
"""

import sys
import os
import json
import argparse
import time
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_data      import generate_dataset, load_from_csv
from scoring            import score_accounts
from activation_report  import score_activation, compute_ttv_benchmarks, get_expansion_pipeline
from claude_intelligence import enrich_with_intelligence
from intervention_queue import build_intervention_queue
from slack_alerts       import send_slack_digest
from dashboard          import export_dashboard
from config             import SNAPSHOT_PATH

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_snapshot() -> dict | None:
    if os.path.exists(SNAPSHOT_PATH):
        try:
            with open(SNAPSHOT_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _save_snapshot(df) -> None:
    snap = {
        "date":           date.today().isoformat(),
        "thriving_count": int((df["risk_tier"] == "Thriving").sum()),
        "at_risk_count":  int((df["risk_tier"] == "At-Risk").sum()),
        "churning_count": int((df["risk_tier"] == "Churning").sum()),
        "avg_score":      float(round(df["churn_risk_score"].mean(), 1)),
        "total_arr_mo":   int(df["contract_value_mo"].sum()),
    }
    with open(SNAPSHOT_PATH, "w") as f:
        json.dump(snap, f, indent=2)


def run(skip_ai: bool = False, skip_slack: bool = False, input_csv: str | None = None, output: str = "dashboard.html"):
    print("=" * 58)
    print("  Customer Health Command Center")
    print("=" * 58)

    # Load previous snapshot for WoW comparison
    snapshot = _load_snapshot()
    if snapshot:
        print(f"\n  Prior snapshot found: {snapshot.get('date', 'unknown date')}")

    # Step 1: Data
    if input_csv:
        print(f"\n[1/6] Loading account data from {input_csv}...")
        df = load_from_csv(input_csv)
    else:
        print("\n[1/6] Generating account dataset...")
        df = generate_dataset()
    print(f"      {len(df)} accounts loaded across 4 verticals.")

    # Step 2: Churn scoring
    print("\n[2/6] Scoring churn risk...")
    df = score_accounts(df)
    churning = (df["risk_tier"] == "Churning").sum()
    at_risk  = (df["risk_tier"] == "At-Risk").sum()
    thriving = (df["risk_tier"] == "Thriving").sum()
    print(f"      Churning: {churning}  |  At-Risk: {at_risk}  |  Thriving: {thriving}")

    # Step 3: Activation scoring
    print("\n[3/6] Scoring activation depth...")
    df = score_activation(df)
    underactivated = (df["overdue_count"] > 0).sum()
    benchmarks     = compute_ttv_benchmarks(df)
    expansion      = get_expansion_pipeline(df)
    print(f"      {underactivated} accounts underactivated. {len(expansion)} expansion candidates identified.")

    # Step 4: Claude intelligence
    if skip_ai:
        print(f"\n[4/6] Skipping AI intelligence layer (--skip-ai).")
        df["cs_brief"]      = ""
        df["outreach_draft"] = ""
    else:
        n_at_risk = churning + at_risk
        print(f"\n[4/6] Generating Claude intelligence for {n_at_risk} at-risk accounts...")
        t0 = time.time()
        df = enrich_with_intelligence(df)
        print(f"      Done in {round(time.time() - t0, 1)}s.")

    # Step 5: Intervention queue
    n_queue = (df["churn_risk_score"] >= 65).sum()
    if skip_ai:
        print(f"\n[5/6] Building intervention queue ({n_queue} accounts, email drafts skipped)...")
    else:
        print(f"\n[5/6] Drafting intervention emails for {n_queue} accounts...")
    intervention_items = build_intervention_queue(df, skip_ai=skip_ai)

    # Step 6: Export dashboard + Slack
    print("\n[6/6] Exporting unified dashboard...")
    dashboard_path = os.path.join(OUTPUT_DIR, output)
    export_dashboard(
        df=df,
        intervention_items=intervention_items,
        activation_benchmarks=benchmarks,
        expansion_pipeline=expansion,
        path=dashboard_path,
        snapshot=snapshot,
    )

    # Save snapshot for next run's WoW comparison
    _save_snapshot(df)

    # Slack alert
    if skip_slack:
        print("\n  [Slack] Skipping alert (--skip-slack).")
    else:
        print("\n  Sending Slack digest...")
        send_slack_digest(df, intervention_items)

    total_arr = df["contract_value_mo"].sum()
    print("\n" + "=" * 58)
    print(f"  Done. Portfolio: {thriving} Thriving / {at_risk} At-Risk / {churning} Churning")
    print(f"  Total ARR: ${total_arr * 12:,.0f}/yr")
    print(f"\n  Open {output} in your browser to view.")
    print("=" * 58 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Customer Health Command Center")
    parser.add_argument("--skip-ai",    action="store_true", help="Skip all Claude API calls")
    parser.add_argument("--skip-slack", action="store_true", help="Skip Slack digest")
    parser.add_argument("--input",  type=str, default=None, metavar="FILE.csv",
                        help="Path to a CSV file to analyse instead of generated mock data")
    parser.add_argument("--output", type=str, default="dashboard.html", metavar="FILE.html",
                        help="Output filename for the dashboard (default: dashboard.html)")
    args = parser.parse_args()
    run(skip_ai=args.skip_ai, skip_slack=args.skip_slack, input_csv=args.input, output=args.output)
