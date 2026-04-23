"""
main.py
Orchestrates the full Customer Health Command Center pipeline:
  1. Generate mock restaurant data
  2. Score each restaurant for churn risk
  3. Call Claude API for churn briefs + intervention emails (skip with --skip-ai)
  4. Export all four reports:
       churn_report.html        — Churn Risk
       activation_report.html  — Activation Depth Tracker
       nrr_model.html           — NRR Scenario (static)
       intervention_queue.html — Daily Intervention Queue (V2)
       churn_report.csv         — Full data export

Usage:
  python main.py
  python main.py --skip-ai    # skip all Claude API calls (faster, no cost)
"""

import sys
import os
import argparse
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_data import generate_dataset
from scoring import score_restaurants
from claude_intelligence import enrich_with_intelligence
from report import export_csv, export_html
from activation_report import export_activation_html
from intervention_queue import export_intervention_html

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def run(skip_ai: bool = False):
    print("=" * 55)
    print("  Customer Health Command Center")
    print("=" * 55)

    # Step 1: Data
    print("\n[1/5] Generating restaurant dataset...")
    df = generate_dataset()
    print(f"      {len(df)} restaurants loaded.")

    # Step 2: Scoring
    print("\n[2/5] Scoring churn risk...")
    df = score_restaurants(df)
    churning = (df["risk_tier"] == "Churning").sum()
    at_risk  = (df["risk_tier"] == "At-Risk").sum()
    thriving = (df["risk_tier"] == "Thriving").sum()
    print(f"      Churning: {churning}  |  At-Risk: {at_risk}  |  Thriving: {thriving}")

    # Step 3: Claude intelligence (churn briefs)
    if skip_ai:
        print("\n[3/5] Skipping AI intelligence layer (--skip-ai flag set).")
        df["cs_brief"] = ""
        df["outreach_draft"] = ""
    else:
        print(f"\n[3/5] Generating Claude intelligence for {churning + at_risk} at-risk restaurants...")
        t0 = time.time()
        df = enrich_with_intelligence(df)
        elapsed = round(time.time() - t0, 1)
        print(f"      Done in {elapsed}s.")

    # Step 4: Intervention queue (V2 email drafting)
    queue_threshold = (df["churn_risk_score"] >= 65).sum()
    if skip_ai:
        print(f"\n[4/5] Skipping intervention email drafting (--skip-ai flag set).")
    else:
        print(f"\n[4/5] Drafting intervention emails for {queue_threshold} accounts (score >= 65)...")

    # Step 5: Reports
    print("\n[5/5] Exporting reports...")
    export_csv(df,  os.path.join(OUTPUT_DIR, "churn_report.csv"))
    export_html(df, os.path.join(OUTPUT_DIR, "churn_report.html"))
    export_activation_html(df, os.path.join(OUTPUT_DIR, "activation_report.html"))
    export_intervention_html(df, os.path.join(OUTPUT_DIR, "intervention_queue.html"), skip_ai=skip_ai)
    print("      nrr_model.html is static — no generation needed.")

    print("\n" + "=" * 55)
    print("  Done. Open any of the following in your browser:")
    print("    churn_report.html")
    print("    activation_report.html")
    print("    nrr_model.html")
    print("    intervention_queue.html")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Customer Health Command Center")
    parser.add_argument("--skip-ai", action="store_true", help="Skip all Claude API calls")
    args = parser.parse_args()
    run(skip_ai=args.skip_ai)
