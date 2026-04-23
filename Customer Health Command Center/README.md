# Customer Health Command Center

## What It Does
An AI-powered customer health platform for a restaurant SaaS business (modeled on Owner.com). It ingests a portfolio of 50 restaurants, scores each one for churn risk across five behavioral signals, tracks activation depth against 30/60/90/120-day milestones, models the NRR impact of upsell levers, and generates a daily intervention queue with Claude-drafted outreach emails for every at-risk account.

## Why It Is Useful
Customer Success teams at restaurant tech companies spend hours manually triaging accounts. This system automates the full CS workflow: weekly churn scoring, activation gap diagnosis, revenue scenario modeling, and personalized outreach drafts ready to copy and send. It demonstrates end-to-end thinking across retention analytics, product adoption, and revenue expansion — the core responsibilities of a Customer Strategy Analytics role.

## How To Run It

**1. Install dependencies:**
```bash
pip install -r requirements.txt
```

**2. Add your Anthropic API key to `.env`:**
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**3. Run the pipeline:**
```bash
python main.py
```

**4. Open any report in your browser:**
```
churn_report.html        — Churn Risk (ranked portfolio)
activation_report.html   — Activation Depth Tracker
nrr_model.html           — NRR Scenario Model (interactive)
intervention_queue.html  — Daily Intervention Queue
churn_report.csv         — Full data export
```

**Skip AI calls for a faster run (no API cost):**
```bash
python main.py --skip-ai
```

---

## The Four Pages

### 1. Churn Risk Report
50 restaurants ranked by churn risk score (0-100). Each card shows the 5 behavioral signals, WoW order volume trend, direct order rate, login frequency, feature adoption, and marketing activity. At-risk and churning accounts include a Claude-generated CS brief and personalized outreach draft.

### 2. Activation Depth Tracker
Answers: *which customers are underactivated, and how far along are they?* Each restaurant is evaluated against 8 activation milestones across 30/60/90/120-day tenure tiers. Overdue milestones are flagged in red. Portfolio sorted by most critical gaps first.

### 3. NRR Scenario Model
Answers: *what would it take to cross 110% NRR?* Three interactive sliders model expansion revenue from SMS tier attach, multi-location expansion, and payment monetization. The blended NRR updates live as sliders move, with a gap callout showing how far from target.

**Fixed assumptions:**
- 50 restaurants, $600 avg MRR, $360K total ARR, 88% gross retention
- SMS add-on: $199/mo | Multi-location: $399/mo | Payments: $149/mo

### 4. Daily Intervention Queue (V2 Agentic Loop)
Every account with churn_risk_score >= 65 enters the queue. The system:
1. Diagnoses which activation milestones are incomplete
2. Assigns a play: Red (score >= 75) = urgent save-play, Yellow (65-74) = gentle re-engagement
3. Calls Claude (claude-sonnet-4-20250514) to draft a personalized outreach email specific to that restaurant's gaps
4. Displays each card with risk score, diagnosed gaps, risk signals, and a collapsible email draft with one-click copy

Summary stats at top: total at-risk accounts, revenue at risk ($499/mo per account), Red vs Yellow split.

---

## How the Churn Scoring Works

Each restaurant is scored on 5 behavioral signals. Score runs 0-100 (higher = more likely to churn).

| Signal | Weight | Rationale |
|--------|--------|-----------|
| Order volume trend (WoW %) | 30% | Clearest leading revenue indicator |
| Direct order rate | 25% | Core platform value metric -- low = 3P dependency |
| Login frequency | 20% | Engagement proxy -- disengaged = pre-churn |
| Feature adoption | 15% | Depth of use; more features = harder to leave |
| Marketing campaigns (30d) | 10% | Active use of growth tools |

**Risk tiers:**
- **Thriving** (0-39): Healthy engagement, growing or stable
- **At-Risk** (40-69): Declining signals, needs CS attention
- **Churning** (70-100): Critical -- immediate outreach required

---

## File Structure

```
├── main.py                   # Pipeline orchestrator -- run this
├── generate_data.py          # Mock dataset of 50 restaurants + activation milestones
├── scoring.py                # Weighted churn risk engine
├── claude_intelligence.py    # Claude API -- CS briefs + outreach drafts (churn page)
├── activation_report.py      # Activation Depth Tracker report generator
├── intervention_queue.py     # V2 agentic loop -- email drafting + queue HTML
├── report.py                 # Churn Risk HTML + CSV generator
├── nrr_model.html            # NRR Scenario Model (static, interactive JS)
├── requirements.txt
└── README.md
```

---

## Stack
- Python + Pandas -- data generation, scoring, report generation
- Anthropic SDK (claude-opus-4-5 + claude-sonnet-4-20250514) -- CS intelligence and intervention emails
- HTML/CSS/JS -- Owner.com-style visual reports, interactive NRR model

## Author
Nick Roland | Built with Claude Code
