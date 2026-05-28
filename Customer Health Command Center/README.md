# Customer Health Command Center

## What It Does

An AI-powered customer health platform built for AI-native B2B SaaS companies. Drop in your account data, run one command, and get a unified dashboard that scores every customer for churn risk, tracks activation against key milestones, surfaces an AI-generated intervention queue with ready-to-send outreach, and models the revenue impact of your expansion levers.

## The Problem It Solves

CS teams at high-growth SaaS companies are reactive by default. Churn is discovered on the renewal call, not 60 days before it. Activation gaps go undiagnosed until it's too late. And when someone does spot an at-risk account, drafting the right outreach email takes another 20 minutes they don't have.

This tool flips that. Run it weekly, get a ranked view of your entire portfolio, know exactly which accounts need attention and why, and have a personalized CS email ready to copy before the page finishes loading.

---

## Live Demo

Two sample datasets are included — each tells a different story.

**Scenario A — Early stage, focused niche (20 accounts)**
A Series A Fintech/HR company with good product-market fit. Mostly healthy, a few at-risk accounts that haven't completed key activation steps.

```
py main.py --input sample_early_stage.csv --skip-ai --skip-slack
```

**Scenario B — Growth stage, scaling pains (40 accounts)**
A Series B company that grew fast across 4 verticals. Onboarding is breaking down. The intervention queue is full, the NRR model shows a retention gap, and several accounts are in freefall.

```
py main.py --input sample_growth_stage.csv --skip-ai --skip-slack
```

Then open `dashboard.html` in your browser.

Want Claude-generated CS briefs and outreach drafts? Drop your Anthropic API key in `.env` and remove `--skip-ai`.

---

## The Five Tabs

### 1. Overview — Executive Summary
The view CS leadership and RevOps open first. Shows the full portfolio split (Thriving / At-Risk / Churning) weighted by ARR — not account count — with week-over-week trend arrows versus the prior run. Includes a segment breakdown by vertical and a top-3 expansion pipeline card flagging the highest upsell opportunities among your healthiest accounts.

### 2. Churn Risk
Every account ranked by churn risk score (0–100). Toggle between sorting by score or by ARR at risk to shift the lens from volume to revenue impact. At-risk and churning accounts expand to show a Claude-generated CS brief — a 3–5 sentence plain-English diagnosis of what's breaking down.

### 3. Activation Tracker
Which customers haven't completed key adoption milestones, and how overdue are they? Eight milestones across four tenure bands (Days 1–7 / 8–30 / 31–60 / 61–90) shown as pills per account, sorted by overdue count. A sticky TTV benchmark sidebar shows the portfolio average completion time versus target for each milestone — where adoption is systematically slow is a product problem, not a CS problem.

### 4. Intervention Queue
Every account scoring ≥ 65 enters the queue. The system diagnoses which activation steps are incomplete, assigns a play (Red = urgent save, Yellow = re-engagement), and displays a Claude-drafted outreach email specific to that account's gaps. One-click copy. Ready to send.

### 5. NRR Model
Revenue planning in one view. A live churn trajectory banner shows the ARR impact if all churning accounts leave in the next 90 days. Below it, three interactive expansion sliders (seat packs, API tier, advanced AI features) let you model what it takes to hit 110% NRR. Numbers update live as you move the sliders.

---

## How the Churn Score Works

Five behavioral signals, each normalized and weighted:

| Signal | Weight | What it measures |
|--------|--------|-----------------|
| AI usage trend (WoW %) | 30% | Is the team generating more or fewer AI outputs week over week? |
| Workflow completion rate | 25% | Are users finishing the workflows they start, or abandoning them? |
| Session frequency | 20% | How often is the team logging in? Disengagement is pre-churn. |
| Integration depth | 15% | Deeper integrations = harder to leave. |
| Seat expansion | 10% | Is the team growing or contracting? |

Risk tiers: **Thriving** (0–39) · **At-Risk** (40–69) · **Churning** (70–100)

---

## Bring Your Own Data

The tool accepts any CSV with the following columns. Drop it in the project folder and point the `--input` flag at it.

```
company_name, vertical, months_on_platform, contract_value_mo,
ai_runs_this_week, ai_runs_last_week, workflow_completion_rate,
sessions_per_week, integrations_connected, total_integrations,
seats_now, seats_prev,
m_first_ai_output, m_workspace_configured, m_first_workflow,
m_integration_connected, m_team_member_added, m_volume_threshold,
m_second_use_case, m_output_shared
```

Milestone columns accept `True`/`False` or `1`/`0`. Verticals: `Fintech`, `Healthtech`, `HR & People Ops`, `DevTools`. See the included sample CSVs for the exact format.

---

## Setup

**1. Install dependencies**
```
py -m pip install -r requirements.txt
```

**2. Configure environment variables**
```
cp .env.example .env
```
Add your `ANTHROPIC_API_KEY`. Add a `SLACK_WEBHOOK_URL` if you want daily Slack digests.

**3. Run it**
```
# Fast run, no API calls
py main.py --input sample_growth_stage.csv --skip-ai --skip-slack

# Full run with Claude-generated CS briefs and outreach emails
py main.py --input sample_growth_stage.csv --skip-slack

# Use generated mock data instead of a CSV
py main.py --skip-ai --skip-slack
```

**4. Open `dashboard.html` in your browser**

---

## File Structure

```
├── main.py                 # Pipeline orchestrator — run this
├── config.py               # All configurable values: signals, weights, milestones, NRR levers
├── generate_data.py        # Mock data generator + CSV loader
├── scoring.py              # Churn risk scoring engine
├── activation_report.py    # Activation scoring, TTV benchmarks, expansion pipeline
├── claude_intelligence.py  # Claude API — CS briefs + outreach drafts
├── intervention_queue.py   # Intervention tiers + email drafting
├── slack_alerts.py         # Slack webhook digest
├── dashboard.py            # Unified 5-tab HTML dashboard generator
├── sample_early_stage.csv  # Demo: 20-account Series A portfolio
├── sample_growth_stage.csv # Demo: 40-account Series B with scaling pains
├── requirements.txt
└── .env.example
```

---

## Stack

- **Python + Pandas** — scoring engine, activation logic, pipeline orchestration
- **Anthropic SDK** (claude-sonnet-4-6) — CS briefs, intervention email drafts
- **HTML / CSS / Vanilla JS** — unified tabbed dashboard, interactive NRR model
- **Slack Webhooks** — daily health digest (stdlib only, no extra dependencies)

---

## Author

Nick Roland | Built with Claude Code
