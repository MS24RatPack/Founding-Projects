"""
dashboard.py
Generates a single unified dashboard.html with 5 tab sections.
Pulls all rendered content from the scored dataframe and supporting data structures.
"""

import json
from datetime import date
import pandas as pd
from config import (
    PRODUCT_NAME,
    ACTIVATION_MILESTONES,
    ACTIVATION_TIER_BANDS,
    NRR_TARGET,
    NRR_GROSS_RETENTION,
    NRR_LEVERS,
    INTERVENTION_THRESHOLD,
    RED_CUTOFF,
    SCORING_SIGNALS,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _fmt_dollar(n: float) -> str:
    return f"${int(round(n)):,}"


def _risk_colors(tier: str) -> dict:
    return {
        "Thriving": {"badge_bg": "#DCFCE7", "badge_text": "#15803D", "bar": "#22C55E"},
        "At-Risk":  {"badge_bg": "#FEF3C7", "badge_text": "#B45309", "bar": "#F59E0B"},
        "Churning": {"badge_bg": "#FFE4E6", "badge_text": "#BE123C", "bar": "#F43F5E"},
    }.get(tier, {"badge_bg": "#F1F5F9", "badge_text": "#64748B", "bar": "#94A3B8"})


def _tier_badge(tier: str) -> str:
    c = _risk_colors(tier)
    return (
        f'<span style="background:{c["badge_bg"]};color:{c["badge_text"]};'
        f'padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;">'
        f'{tier}</span>'
    )


def _score_bar(score: float, tier: str) -> str:
    color = _risk_colors(tier)["bar"]
    return (
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<div style="flex:1;height:5px;background:#F1F5F9;border-radius:3px;min-width:60px;">'
        f'<div style="width:{score}%;height:100%;background:{color};border-radius:3px;"></div>'
        f'</div>'
        f'<span style="font-size:13px;font-weight:700;color:#0F172A;min-width:28px;">{score}</span>'
        f'</div>'
    )


def _trend_arrow(current, previous, higher_is_better: bool = True) -> str:
    if previous is None:
        return '<span style="color:#94A3B8;">—</span>'
    delta = current - previous
    if abs(delta) < 0.5:
        return '<span style="color:#94A3B8;">—</span>'
    improved = (delta > 0) == higher_is_better
    arrow = "▲" if delta > 0 else "▼"
    color = "#22C55E" if improved else "#F43F5E"
    return f'<span style="color:{color};font-size:12px;font-weight:700;">{arrow} {abs(int(delta))}</span>'


# ---------------------------------------------------------------------------
# Tab 1: Overview
# ---------------------------------------------------------------------------

def _render_overview(df: pd.DataFrame, expansion_pipeline: list, snapshot: dict | None) -> str:
    total = len(df)
    thriving_df = df[df["risk_tier"] == "Thriving"]
    at_risk_df  = df[df["risk_tier"] == "At-Risk"]
    churning_df = df[df["risk_tier"] == "Churning"]

    thriving_count = len(thriving_df)
    at_risk_count  = len(at_risk_df)
    churning_count = len(churning_df)

    thriving_arr = thriving_df["contract_value_mo"].sum()
    at_risk_arr  = at_risk_df["contract_value_mo"].sum()
    churning_arr = churning_df["contract_value_mo"].sum()
    total_arr    = df["contract_value_mo"].sum()

    avg_score = round(df["churn_risk_score"].mean(), 1)

    prev = snapshot or {}
    t_arrow = _trend_arrow(thriving_count, prev.get("thriving_count"), higher_is_better=True)
    r_arrow = _trend_arrow(at_risk_count, prev.get("at_risk_count"),   higher_is_better=False)
    c_arrow = _trend_arrow(churning_count, prev.get("churning_count"), higher_is_better=False)

    # Segment breakdown
    seg_rows = ""
    for vertical in ["Fintech", "Healthtech", "HR & People Ops", "DevTools"]:
        vdf = df[df["vertical"] == vertical]
        if vdf.empty:
            continue
        v_thriving = (vdf["risk_tier"] == "Thriving").sum()
        v_at_risk  = (vdf["risk_tier"] == "At-Risk").sum()
        v_churning = (vdf["risk_tier"] == "Churning").sum()
        v_avg      = round(vdf["churn_risk_score"].mean(), 1)
        health_color = "#22C55E" if v_avg < 40 else ("#F59E0B" if v_avg < 70 else "#F43F5E")
        seg_rows += f"""
        <tr>
          <td style="padding:10px 12px;font-size:13px;font-weight:600;color:#0F172A;">{vertical}</td>
          <td style="padding:10px 12px;font-size:13px;color:#64748B;text-align:center;">{len(vdf)}</td>
          <td style="padding:10px 12px;font-size:13px;font-weight:700;color:{health_color};text-align:center;">{v_avg}</td>
          <td style="padding:10px 12px;font-size:13px;color:#22C55E;text-align:center;">{v_thriving}</td>
          <td style="padding:10px 12px;font-size:13px;color:#F59E0B;text-align:center;">{v_at_risk}</td>
          <td style="padding:10px 12px;font-size:13px;color:#F43F5E;text-align:center;">{v_churning}</td>
        </tr>"""

    # Expansion pipeline
    exp_cards = ""
    for item in expansion_pipeline:
        exp_cards += f"""
        <div style="background:#F0F9FF;border:1px solid #BAE6FD;border-radius:10px;padding:14px 16px;margin-bottom:8px;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
            <span style="font-size:14px;font-weight:700;color:#0F172A;">{item['company_name']}</span>
            <span style="font-size:12px;font-weight:700;color:#0066FF;">+{_fmt_dollar(item['lever_mrr'])}/mo</span>
          </div>
          <div style="font-size:12px;color:#64748B;margin-bottom:6px;">{item['vertical']} &middot; Health score: {item['churn_risk_score']}</div>
          <div style="font-size:11px;font-weight:600;background:#DBEAFE;color:#1D4ED8;display:inline-block;padding:2px 8px;border-radius:20px;">
            &#8599; {item['lever_label']}
          </div>
        </div>"""

    if not exp_cards:
        exp_cards = '<div style="color:#94A3B8;font-size:13px;padding:16px 0;">No Thriving accounts with expansion signals identified.</div>'

    return f"""
    <div class="container">
      <div style="margin-bottom:28px;">
        <div style="font-size:24px;font-weight:700;color:#0F172A;letter-spacing:-.02em;">Portfolio Health Overview</div>
        <div style="font-size:14px;color:#64748B;margin-top:4px;">Executive summary &middot; {total} accounts &middot; {_fmt_dollar(total_arr)}/mo total ARR &middot; Avg risk score: {avg_score}</div>
      </div>

      <!-- Stat cards -->
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:28px;">
        <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;padding:20px 22px;">
          <div style="font-size:11px;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;margin-bottom:6px;">Thriving</div>
          <div style="display:flex;align-items:baseline;gap:10px;">
            <div style="font-size:36px;font-weight:700;color:#22C55E;">{thriving_count}</div>
            {t_arrow}
          </div>
          <div style="font-size:12px;color:#64748B;margin-top:4px;">{_fmt_dollar(thriving_arr)}/mo ARR</div>
        </div>
        <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;padding:20px 22px;">
          <div style="font-size:11px;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;margin-bottom:6px;">At-Risk</div>
          <div style="display:flex;align-items:baseline;gap:10px;">
            <div style="font-size:36px;font-weight:700;color:#F59E0B;">{at_risk_count}</div>
            {r_arrow}
          </div>
          <div style="font-size:12px;color:#64748B;margin-top:4px;">{_fmt_dollar(at_risk_arr)}/mo ARR</div>
        </div>
        <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;padding:20px 22px;">
          <div style="font-size:11px;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;margin-bottom:6px;">Churning</div>
          <div style="display:flex;align-items:baseline;gap:10px;">
            <div style="font-size:36px;font-weight:700;color:#F43F5E;">{churning_count}</div>
            {c_arrow}
          </div>
          <div style="font-size:12px;color:#64748B;margin-top:4px;">{_fmt_dollar(churning_arr)}/mo ARR at risk</div>
        </div>
      </div>

      <!-- Lower row: segment breakdown + expansion pipeline -->
      <div style="display:grid;grid-template-columns:1.6fr 1fr;gap:20px;margin-bottom:28px;">

        <!-- Segment breakdown -->
        <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;overflow:hidden;">
          <div style="padding:16px 20px;border-bottom:1px solid #F1F5F9;">
            <div style="font-size:13px;font-weight:700;color:#0F172A;">Segment Breakdown</div>
            <div style="font-size:12px;color:#94A3B8;margin-top:2px;">Health by vertical</div>
          </div>
          <table style="width:100%;border-collapse:collapse;">
            <thead>
              <tr style="background:#F8FAFC;">
                <th style="padding:8px 12px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#94A3B8;text-align:left;">Vertical</th>
                <th style="padding:8px 12px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#94A3B8;text-align:center;">Accounts</th>
                <th style="padding:8px 12px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#94A3B8;text-align:center;">Avg Score</th>
                <th style="padding:8px 12px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#22C55E;text-align:center;">&#10003;</th>
                <th style="padding:8px 12px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#F59E0B;text-align:center;">&#9888;</th>
                <th style="padding:8px 12px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#F43F5E;text-align:center;">&#9888;&#9888;</th>
              </tr>
            </thead>
            <tbody style="divide-y:#F1F5F9;">
              {seg_rows}
            </tbody>
          </table>
        </div>

        <!-- Expansion pipeline -->
        <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;padding:16px 20px;">
          <div style="font-size:13px;font-weight:700;color:#0F172A;margin-bottom:4px;">Expansion Pipeline</div>
          <div style="font-size:12px;color:#94A3B8;margin-bottom:14px;">Top healthy accounts with upsell room</div>
          {exp_cards}
        </div>

      </div>
    </div>"""


# ---------------------------------------------------------------------------
# Tab 2: Churn Risk
# ---------------------------------------------------------------------------

def _churn_card(row: pd.Series) -> str:
    tier = row["risk_tier"]
    rc = _risk_colors(tier)
    drivers_html = "".join(
        f'<div style="font-size:12px;color:#64748B;padding:2px 0 2px 10px;'
        f'border-left:2px solid #E2E8F0;margin-bottom:3px;">&#8212; {d}</div>'
        for d in row.get("signal_drivers", [])
    )
    brief = row.get("cs_brief", "")
    brief_section = ""
    if brief:
        brief_escaped = brief.replace("<", "&lt;").replace(">", "&gt;")
        brief_section = f"""
        <details style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;margin-top:12px;">
          <summary style="padding:10px 14px;cursor:pointer;list-style:none;font-size:10px;
                          font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#94A3B8;
                          user-select:none;">&#9654; CS Brief (AI-generated)</summary>
          <div style="padding:0 14px 14px;font-size:13px;color:#334155;line-height:1.6;">{brief_escaped}</div>
        </details>"""

    score = row["churn_risk_score"]
    arr_mo = row["contract_value_mo"]
    border = "#FDA4AF" if tier == "Churning" else ("#FCD34D" if tier == "At-Risk" else "#E2E8F0")

    return f"""
    <div class="churn-card" data-score="{score}" data-arr="{arr_mo * 12}"
         style="background:white;border:1px solid {border};border-radius:12px;
                padding:18px 20px;margin-bottom:10px;">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap;">
        <span style="font-size:15px;font-weight:700;color:#0F172A;">{row['company_name']}</span>
        {_tier_badge(tier)}
        <span style="font-size:12px;color:#94A3B8;">{row['vertical']} &middot; {row['months_on_platform']}mo on platform</span>
        <span style="font-size:12px;font-weight:600;color:#0F172A;margin-left:auto;">{_fmt_dollar(arr_mo)}/mo</span>
      </div>
      <div style="display:flex;align-items:center;gap:16px;margin-bottom:10px;flex-wrap:wrap;">
        <div style="min-width:200px;">{_score_bar(score, tier)}</div>
      </div>
      {drivers_html}
      {brief_section}
    </div>"""


def _render_churn_risk(df: pd.DataFrame) -> str:
    df_by_score = df.sort_values("churn_risk_score", ascending=False)
    df_by_arr   = df.sort_values("arr_at_risk", ascending=False)

    cards_score = "".join(_churn_card(row) for _, row in df_by_score.iterrows())
    cards_arr   = "".join(_churn_card(row) for _, row in df_by_arr.iterrows())

    churning_arr = df[df["risk_tier"] == "Churning"]["contract_value_mo"].sum() * 12
    at_risk_arr  = df[df["risk_tier"] == "At-Risk"]["contract_value_mo"].sum() * 12

    return f"""
    <div class="container">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:12px;">
        <div>
          <div style="font-size:24px;font-weight:700;color:#0F172A;letter-spacing:-.02em;">Churn Risk</div>
          <div style="font-size:14px;color:#64748B;margin-top:4px;">
            All {len(df)} accounts ranked by risk &middot;
            <span style="color:#F43F5E;font-weight:600;">{_fmt_dollar(churning_arr)}/yr churning ARR</span> &middot;
            <span style="color:#F59E0B;font-weight:600;">{_fmt_dollar(at_risk_arr)}/yr at-risk ARR</span>
          </div>
        </div>
        <div style="display:flex;gap:8px;">
          <button onclick="setSortChurn('score')" id="sort-score-btn"
                  style="background:#0066FF;color:white;border:none;border-radius:8px;
                         padding:8px 16px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;">
            Sort by Score
          </button>
          <button onclick="setSortChurn('arr')" id="sort-arr-btn"
                  style="background:#F1F5F9;color:#64748B;border:none;border-radius:8px;
                         padding:8px 16px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;">
            Sort by ARR at Risk
          </button>
        </div>
      </div>

      <div id="churn-view-score">{cards_score}</div>
      <div id="churn-view-arr" style="display:none;">{cards_arr}</div>
    </div>"""


# ---------------------------------------------------------------------------
# Tab 3: Activation
# ---------------------------------------------------------------------------

def _milestone_pill(label: str, completed: bool, overdue: bool) -> str:
    if completed:
        bg, text, icon = "#DCFCE7", "#15803D", "&#10003;"
    elif overdue:
        bg, text, icon = "#FFE4E6", "#BE123C", "&#10005;"
    else:
        bg, text, icon = "#F1F5F9", "#CBD5E1", "&middot;"
    return (
        f'<span style="background:{bg};color:{text};padding:3px 9px;border-radius:20px;'
        f'font-size:11px;font-weight:600;white-space:nowrap;">{icon} {label}</span>'
    )


def _render_activation(df: pd.DataFrame, benchmarks: dict) -> str:
    df = df.copy()
    df = df.sort_values("overdue_count", ascending=False).reset_index(drop=True)

    total = len(df)
    underactivated = (df["overdue_count"] > 0).sum()
    on_track = total - underactivated
    activation_rate = round(on_track / total * 100)

    # TTV benchmark table
    bench_rows = ""
    for m in ACTIVATION_MILESTONES:
        mid = m["id"]
        b = benchmarks.get(mid, {})
        target = b.get("target_days", "—")
        actual = b.get("avg_actual")
        actual_str = f"{actual}d" if actual else "—"
        actual_color = "#0F172A"
        if actual and target and isinstance(actual, (int, float)) and isinstance(target, (int, float)):
            actual_color = "#22C55E" if actual <= target * 1.2 else "#F43F5E"
        bench_rows += f"""
        <tr>
          <td style="padding:9px 12px;font-size:13px;color:#334155;">{m['label']}</td>
          <td style="padding:9px 12px;font-size:13px;color:#94A3B8;text-align:center;">{target}d</td>
          <td style="padding:9px 12px;font-size:13px;font-weight:600;color:{actual_color};text-align:center;">{actual_str}</td>
        </tr>"""

    # Account cards
    account_cards = ""
    for _, row in df.iterrows():
        overdue_count = row["overdue_count"]
        days = row["days_on_platform"]
        tier_badge = _tier_badge(row["risk_tier"])

        if overdue_count > 0:
            status_badge = (
                f'<span style="background:#FFF1F2;color:#BE123C;padding:3px 10px;border-radius:20px;'
                f'font-size:11px;font-weight:600;">&#9888; {overdue_count} overdue</span>'
            )
        else:
            status_badge = (
                '<span style="background:#F0FDF4;color:#15803D;padding:3px 10px;border-radius:20px;'
                'font-size:11px;font-weight:600;">&#10003; On track</span>'
            )

        # Milestone pills grouped by tier band
        bands_html = ""
        for band in ACTIVATION_TIER_BANDS:
            band_milestones = [m for m in ACTIVATION_MILESTONES if m["tier_days"] == band["tier_days"]]
            is_due = days >= band["tier_days"]
            pills = ""
            for m in band_milestones:
                completed = bool(row.get(m["id"], False))
                is_overdue = is_due and not completed
                pills += f'<div style="margin-bottom:5px;">{_milestone_pill(m["label"], completed, is_overdue)}</div>'

            band_color = band["color"] if is_due else "#CBD5E1"
            bands_html += f"""
            <div style="flex:1;min-width:150px;">
              <div style="font-size:10px;font-weight:700;letter-spacing:.08em;color:{band_color};
                   text-transform:uppercase;margin-bottom:8px;padding-bottom:5px;
                   border-bottom:2px solid {band_color};">{band['label']}</div>
              {pills}
            </div>"""

        border = "#FDA4AF" if overdue_count > 0 else "#E2E8F0"
        bg = "#FFF9F9" if overdue_count > 0 else "white"

        account_cards += f"""
        <div style="background:{bg};border:1px solid {border};border-radius:12px;
             padding:16px 20px;margin-bottom:10px;">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;flex-wrap:wrap;">
            <span style="font-size:14px;font-weight:700;color:#0F172A;">{row['company_name']}</span>
            {tier_badge}
            {status_badge}
            <span style="font-size:12px;color:#94A3B8;margin-left:auto;">{row['vertical']} &middot; {row['months_on_platform']}mo</span>
          </div>
          <div style="display:flex;gap:18px;flex-wrap:wrap;">{bands_html}</div>
        </div>"""

    return f"""
    <div class="container">
      <div style="margin-bottom:24px;">
        <div style="font-size:24px;font-weight:700;color:#0F172A;letter-spacing:-.02em;">Activation Tracker</div>
        <div style="font-size:14px;color:#64748B;margin-top:4px;">
          {underactivated} underactivated &middot; {on_track} on track &middot; {activation_rate}% activation rate
        </div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 340px;gap:20px;margin-bottom:28px;">

        <!-- Account list -->
        <div>
          <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.1em;
               color:#94A3B8;margin-bottom:12px;">Sorted by overdue milestone count</div>
          {account_cards}
        </div>

        <!-- TTV benchmarks -->
        <div>
          <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;overflow:hidden;position:sticky;top:80px;">
            <div style="padding:14px 16px;border-bottom:1px solid #F1F5F9;">
              <div style="font-size:13px;font-weight:700;color:#0F172A;">TTV Benchmarks</div>
              <div style="font-size:12px;color:#94A3B8;margin-top:2px;">Target vs portfolio average</div>
            </div>
            <table style="width:100%;border-collapse:collapse;">
              <thead>
                <tr style="background:#F8FAFC;">
                  <th style="padding:8px 12px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#94A3B8;text-align:left;">Milestone</th>
                  <th style="padding:8px 12px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#94A3B8;text-align:center;">Target</th>
                  <th style="padding:8px 12px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#94A3B8;text-align:center;">Avg Actual</th>
                </tr>
              </thead>
              <tbody>{bench_rows}</tbody>
            </table>
          </div>
        </div>

      </div>
    </div>"""


# ---------------------------------------------------------------------------
# Tab 4: Intervention Queue
# ---------------------------------------------------------------------------

def _intervention_card(item: dict) -> str:
    row   = item["row"]
    tier  = item["tier"]
    gaps  = item["gaps"]
    email = item["email"]

    if tier == "Red":
        c = {"border": "#FDA4AF", "bg": "#FFF1F2", "badge_bg": "#FFE4E6",
             "badge_text": "#BE123C", "label": "Urgent Save-Play", "icon": "&#x1F534;",
             "pill_bg": "#FEE2E2", "pill_text": "#991B1B"}
    else:
        c = {"border": "#FCD34D", "bg": "#FFFBEB", "badge_bg": "#FEF3C7",
             "badge_text": "#B45309", "label": "Re-Engagement", "icon": "&#x1F7E1;",
             "pill_bg": "#FEF3C7", "pill_text": "#92400E"}

    gap_pills = "".join(
        f'<span style="background:{c["pill_bg"]};color:{c["pill_text"]};padding:3px 9px;'
        f'border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap;">&#10005; {label}</span> '
        for _, label in gaps
    ) or '<span style="color:#94A3B8;font-size:12px;">No specific activation gaps flagged</span>'

    drivers_html = "".join(
        f'<div style="font-size:12px;color:#64748B;padding:2px 0 2px 10px;'
        f'border-left:2px solid #E2E8F0;margin-bottom:3px;">&#8212; {d}</div>'
        for d in row.get("signal_drivers", [])
    )

    email_escaped = (
        email.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace("\n", "<br>")
    )
    # Escape for JS data attribute
    email_js = email.replace('"', "&quot;").replace("\n", "\\n")

    arr_mo = row["contract_value_mo"]

    return f"""
    <div style="background:{c['bg']};border:1px solid {c['border']};border-radius:12px;
         padding:20px 22px;margin-bottom:14px;">
      <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:14px;flex-wrap:wrap;">
        <div style="flex:1;">
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:4px;">
            <span style="font-size:16px;font-weight:700;color:#0F172A;">{row['company_name']}</span>
            <span style="background:{c['badge_bg']};color:{c['badge_text']};padding:3px 10px;
              border-radius:20px;font-size:11px;font-weight:600;">{c['icon']} {c['label'].upper()}</span>
          </div>
          <div style="font-size:12px;color:#94A3B8;">{row['vertical']} &middot; {row['months_on_platform']}mo on platform &middot; {_fmt_dollar(arr_mo)}/mo</div>
        </div>
        <div style="min-width:160px;">
          <div style="font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;margin-bottom:6px;">Churn Risk Score</div>
          {_score_bar(row['churn_risk_score'], row['risk_tier'])}
        </div>
      </div>

      <div style="margin-bottom:12px;">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#94A3B8;margin-bottom:8px;">Activation Gaps</div>
        <div style="display:flex;flex-wrap:wrap;gap:6px;">{gap_pills}</div>
      </div>

      <div style="margin-bottom:16px;">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#94A3B8;margin-bottom:6px;">Risk Signals</div>
        {drivers_html}
      </div>

      <details style="background:white;border:1px solid #E2E8F0;border-radius:8px;">
        <summary style="display:flex;justify-content:space-between;align-items:center;
                        padding:12px 16px;cursor:pointer;list-style:none;user-select:none;">
          <span style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#94A3B8;">
            &#9654; Drafted Outreach Email
          </span>
          <button onclick="event.preventDefault();event.stopPropagation();copyEmail(this)"
            data-text="{email_js}"
            style="background:#0066FF;color:white;border:none;border-radius:6px;padding:5px 12px;
                   font-size:11px;font-weight:600;cursor:pointer;font-family:inherit;">
            Copy
          </button>
        </summary>
        <div style="padding:0 16px 16px;border-top:1px solid #F1F5F9;">
          <div style="font-size:13px;color:#334155;line-height:1.7;white-space:pre-wrap;padding-top:12px;">{email_escaped}</div>
        </div>
      </details>
    </div>"""


def _render_intervention_queue(df: pd.DataFrame, items: list) -> str:
    total_at_risk  = len(items)
    revenue_at_risk = sum(i["row"]["contract_value_mo"] for i in items)
    red_count    = sum(1 for i in items if i["tier"] == "Red")
    yellow_count = sum(1 for i in items if i["tier"] == "Yellow")

    cards_html = "".join(_intervention_card(i) for i in items)
    if not cards_html:
        cards_html = '<div style="text-align:center;color:#94A3B8;padding:48px;font-size:14px;">No accounts above the intervention threshold.</div>'

    return f"""
    <div class="container">
      <div style="margin-bottom:24px;">
        <div style="font-size:24px;font-weight:700;color:#0F172A;letter-spacing:-.02em;">Daily Intervention Queue</div>
        <div style="font-size:14px;color:#64748B;margin-top:4px;">Accounts above risk threshold &middot; Emails ready to send</div>
      </div>

      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:28px;">
        <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;padding:18px 20px;">
          <div style="font-size:11px;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;margin-bottom:6px;">At-Risk Accounts</div>
          <div style="font-size:28px;font-weight:700;color:#0F172A;">{total_at_risk}</div>
          <div style="font-size:12px;color:#94A3B8;margin-top:2px;">score &ge; {INTERVENTION_THRESHOLD}</div>
        </div>
        <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;padding:18px 20px;">
          <div style="font-size:11px;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;margin-bottom:6px;">Revenue at Risk</div>
          <div style="font-size:28px;font-weight:700;color:#F43F5E;">{_fmt_dollar(revenue_at_risk)}</div>
          <div style="font-size:12px;color:#94A3B8;margin-top:2px;">/mo combined</div>
        </div>
        <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;padding:18px 20px;">
          <div style="font-size:11px;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;margin-bottom:6px;">Urgent Save-Play</div>
          <div style="font-size:28px;font-weight:700;color:#BE123C;">{red_count}</div>
          <div style="font-size:12px;color:#94A3B8;margin-top:2px;">score &ge; {RED_CUTOFF}</div>
        </div>
        <div style="background:white;border:1px solid #E2E8F0;border-radius:12px;padding:18px 20px;">
          <div style="font-size:11px;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;margin-bottom:6px;">Re-Engagement</div>
          <div style="font-size:28px;font-weight:700;color:#B45309;">{yellow_count}</div>
          <div style="font-size:12px;color:#94A3B8;margin-top:2px;">score {INTERVENTION_THRESHOLD}&ndash;{RED_CUTOFF - 1}</div>
        </div>
      </div>

      <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.1em;color:#94A3B8;margin-bottom:12px;">
        Sorted by highest risk first &mdash; {total_at_risk} accounts
      </div>

      {cards_html}
    </div>"""


# ---------------------------------------------------------------------------
# Tab 5: NRR Model
# ---------------------------------------------------------------------------

def _render_nrr_model(df: pd.DataFrame) -> str:
    total_accounts = len(df)
    base_arr_yr    = int(df["contract_value_mo"].sum() * 12)
    retained_arr   = int(base_arr_yr * NRR_GROSS_RETENTION)
    target_arr     = int(base_arr_yr * NRR_TARGET)
    expansion_needed = target_arr - retained_arr

    churning_arr_yr  = int(df[df["risk_tier"] == "Churning"]["contract_value_mo"].sum() * 12)
    projected_arr_conservative = base_arr_yr - churning_arr_yr
    projected_nrr_conservative = round(projected_arr_conservative / base_arr_yr * 100, 1)

    gross_retention_pct = int(NRR_GROSS_RETENTION * 100)

    # Build lever cards HTML
    lever_cards = ""
    for i, lev in enumerate(NRR_LEVERS):
        num = i + 1
        lever_cards += f"""
        <div class="lever-card">
          <div class="lever-header">
            <div class="lever-title">{lev['label']}</div>
            <div class="lever-pct" id="lev{num}-pct" style="color:{lev['color']};">0%</div>
          </div>
          <div class="lever-desc">{lev['desc']}</div>
          <input type="range" id="lev{num}-slider" min="0" max="{lev['max_pct']}" value="0" step="1"
                 oninput="updateNRR()">
          <div class="lever-impact">Impact: <span id="lev{num}-impact" style="font-weight:600;color:#0066FF;">$0</span>/yr expansion</div>
        </div>"""

    # Build JS constants for levers
    lever_js_consts = "\n".join(
        f"  const LEV{i+1}_MO = {lev['mo_value']};"
        for i, lev in enumerate(NRR_LEVERS)
    )
    lever_js_calc = "\n".join(
        f"  const exp{i+1} = PORTFOLIO * (document.getElementById('lev{i+1}-slider').value / 100) * LEV{i+1}_MO * 12;"
        for i in range(len(NRR_LEVERS))
    )
    lever_js_display = "\n".join(
        f"  document.getElementById('lev{i+1}-pct').textContent = Math.round(document.getElementById('lev{i+1}-slider').value) + '%';"
        f"\n  document.getElementById('lev{i+1}-impact').textContent = fmt(exp{i+1});"
        for i in range(len(NRR_LEVERS))
    )
    lever_js_bd = "\n".join(
        f"  document.getElementById('bd-lev{i+1}').textContent = fmt(exp{i+1});"
        for i in range(len(NRR_LEVERS))
    )
    total_exp_js = " + ".join(f"exp{i+1}" for i in range(len(NRR_LEVERS)))

    bd_rows = "\n".join(
        f'<div class="breakdown-row"><span class="breakdown-label" style="color:{lev["color"]};">{lev["bd_label"]}</span><span class="breakdown-val" id="bd-lev{i+1}">$0</span></div>'
        for i, lev in enumerate(NRR_LEVERS)
    )

    return f"""
    <div class="container">
      <div style="margin-bottom:24px;">
        <div style="font-size:24px;font-weight:700;color:#0F172A;letter-spacing:-.02em;">NRR Scenario Model</div>
        <div style="font-size:14px;color:#64748B;margin-top:4px;">What would it take to cross 110% NRR? Move the sliders to find out.</div>
      </div>

      <!-- Churn trajectory banner -->
      <div style="background:#FFF1F2;border:1px solid #FDA4AF;border-radius:12px;padding:16px 20px;margin-bottom:24px;">
        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#BE123C;margin-bottom:8px;">Current Trajectory (Conservative)</div>
        <div style="display:flex;gap:32px;flex-wrap:wrap;">
          <div>
            <div style="font-size:12px;color:#94A3B8;margin-bottom:2px;">If all Churning accounts leave in 90 days</div>
            <div style="font-size:22px;font-weight:700;color:#BE123C;">&#8722;{_fmt_dollar(churning_arr_yr)}/yr</div>
          </div>
          <div>
            <div style="font-size:12px;color:#94A3B8;margin-bottom:2px;">Projected ARR (conservative)</div>
            <div style="font-size:22px;font-weight:700;color:#0F172A;">{_fmt_dollar(projected_arr_conservative)}/yr</div>
          </div>
          <div>
            <div style="font-size:12px;color:#94A3B8;margin-bottom:2px;">Projected NRR (no expansion)</div>
            <div style="font-size:22px;font-weight:700;color:#F43F5E;">{projected_nrr_conservative}%</div>
          </div>
        </div>
      </div>

      <div class="nrr-layout">

        <!-- Sliders panel -->
        <div class="sliders-panel">
          <div class="assumptions-card">
            <div class="assumptions-title">Portfolio Assumptions (fixed)</div>
            <div class="assumption-row"><span class="al">Accounts</span><span class="av">{total_accounts}</span></div>
            <div class="assumption-row"><span class="al">Total ARR</span><span class="av">{_fmt_dollar(base_arr_yr)}</span></div>
            <div class="assumption-row"><span class="al">Gross retention</span><span class="av">{gross_retention_pct}%</span></div>
            <div class="assumption-row"><span class="al">Retained ARR</span><span class="av">{_fmt_dollar(retained_arr)}</span></div>
            <div class="assumption-row"><span class="al">Target NRR</span><span class="av" style="color:#0066FF;">110%</span></div>
            <div class="assumption-row"><span class="al">Expansion needed for 110%</span><span class="av" style="color:#0066FF;">{_fmt_dollar(expansion_needed)}</span></div>
          </div>
          {lever_cards}
        </div>

        <!-- NRR meter -->
        <div>
          <div class="nrr-card">
            <div class="nrr-label">Blended NRR</div>
            <div class="arc-wrap">
              <svg viewBox="0 0 200 200">
                <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="#F1F5F9" stroke-width="16" stroke-linecap="round"/>
                <path id="arc-fill" d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="#E2E8F0"
                      stroke-width="16" stroke-linecap="round" stroke-dasharray="251.2" stroke-dashoffset="251.2"
                      style="transition:stroke-dashoffset .4s ease,stroke .4s ease;"/>
                <line x1="177" y1="86" x2="185" y2="79" stroke="#0066FF" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </div>
            <div class="nrr-number" id="nrr-display" style="color:#94A3B8;">{gross_retention_pct}<span class="nrr-pct">%</span></div>
            <div class="nrr-target-line">Target: <span>110%</span></div>
            <div class="gap-card" id="gap-card" style="background:#FFF1F2;color:#BE123C;">
              <span id="gap-text">{_fmt_dollar(expansion_needed)} expansion needed to reach 110%</span>
            </div>
            <div class="breakdown">
              <div class="breakdown-row"><span class="breakdown-label">Retained ARR</span><span class="breakdown-val">{_fmt_dollar(retained_arr)}</span></div>
              {bd_rows}
              <div class="breakdown-row total"><span class="breakdown-label">Total ARR (end of year)</span><span class="breakdown-val" id="bd-total">{_fmt_dollar(retained_arr)}</span></div>
            </div>
          </div>
        </div>

      </div>
    </div>

    <script>
    const PORTFOLIO     = {total_accounts};
    const BASE_ARR      = {base_arr_yr};
    const RETAINED_ARR  = {retained_arr};
    const TARGET_NRR    = {NRR_TARGET};
    const TARGET_ARR    = {target_arr};
    const EXPANSION_NEEDED = {expansion_needed};
    {lever_js_consts}

    function fmt(n) {{ return '$' + Math.round(n).toLocaleString(); }}

    function arcOffset(nrr) {{
      const pct = Math.max(0, Math.min(1, (nrr - 0.70) / 0.60));
      return 251.2 * (1 - pct);
    }}

    function arcColor(nrr) {{
      if (nrr >= 1.10) return '#22C55E';
      if (nrr >= 0.95) return '#F59E0B';
      return '#F43F5E';
    }}

    function updateNRR() {{
      {lever_js_calc}
      const totalExp = {total_exp_js};
      const endARR   = RETAINED_ARR + totalExp;
      const nrr      = endARR / BASE_ARR;

      {lever_js_display}
      {lever_js_bd}

      const nrrPct = Math.round(nrr * 100);
      document.getElementById('nrr-display').innerHTML = nrrPct + '<span class="nrr-pct">%</span>';
      const color = arcColor(nrr);
      document.getElementById('nrr-display').style.color = color;

      const arc = document.getElementById('arc-fill');
      arc.setAttribute('stroke-dashoffset', arcOffset(nrr).toFixed(1));
      arc.setAttribute('stroke', color);

      document.getElementById('bd-total').textContent = fmt(endARR);

      const gapCard = document.getElementById('gap-card');
      const gapText = document.getElementById('gap-text');
      const gap = TARGET_ARR - endARR;
      if (nrr >= TARGET_NRR) {{
        gapCard.style.background = '#F0FDF4';
        gapCard.style.color = '#15803D';
        gapText.textContent = '110% target reached — ' + fmt(endARR - TARGET_ARR) + ' above target';
      }} else {{
        gapCard.style.background = '#FFF1F2';
        gapCard.style.color = '#BE123C';
        gapText.textContent = fmt(gap) + ' expansion still needed to reach 110%';
      }}
    }}

    updateNRR();
    </script>"""


# ---------------------------------------------------------------------------
# Main export function
# ---------------------------------------------------------------------------

def export_dashboard(
    df: pd.DataFrame,
    intervention_items: list,
    activation_benchmarks: dict,
    expansion_pipeline: list,
    path: str,
    snapshot: dict | None = None,
) -> None:
    today = date.today().strftime("%B %d, %Y")

    tab_overview    = _render_overview(df, expansion_pipeline, snapshot)
    tab_churn       = _render_churn_risk(df)
    tab_activation  = _render_activation(df, activation_benchmarks)
    tab_queue       = _render_intervention_queue(df, intervention_items)
    tab_nrr         = _render_nrr_model(df)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{PRODUCT_NAME} &mdash; Customer Health Command Center &mdash; {today}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Inter', -apple-system, sans-serif; background: #F8FAFC; color: #0F172A; }}

  /* Top nav */
  .topnav {{
    background: white; border-bottom: 1px solid #E2E8F0;
    padding: 0 40px; display: flex; align-items: center; height: 60px;
    position: sticky; top: 0; z-index: 100;
  }}
  .logo {{ font-size: 17px; font-weight: 700; color: #0F172A; letter-spacing: -.02em; margin-right: 32px; }}
  .logo span {{ color: #0066FF; }}
  .nav-tab {{
    text-decoration: none; padding: 0 16px; height: 60px;
    display: flex; align-items: center; font-size: 13px; font-weight: 500;
    color: #64748B; border-bottom: 2px solid transparent; cursor: pointer;
    background: none; border-top: none; border-left: none; border-right: none;
    font-family: inherit; transition: color .15s;
  }}
  .nav-tab:hover {{ color: #0F172A; }}
  .nav-tab.active {{ color: #0066FF; border-bottom-color: #0066FF; }}
  .nav-date {{ margin-left: auto; font-size: 12px; color: #94A3B8; }}

  /* Tab content */
  .tab-pane {{ display: none; padding: 32px 0; }}
  .tab-pane.active {{ display: block; }}

  /* Container */
  .container {{ max-width: 1160px; margin: 0 auto; padding: 0 24px; }}

  /* NRR model specific */
  .nrr-layout {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; align-items: start; }}
  .nrr-card {{ background: white; border: 1px solid #E2E8F0; border-radius: 16px; padding: 32px; text-align: center; position: sticky; top: 80px; }}
  .nrr-label {{ font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .1em; color: #94A3B8; margin-bottom: 12px; }}
  .nrr-number {{ font-size: 72px; font-weight: 300; letter-spacing: -.04em; line-height: 1; transition: color .3s; }}
  .nrr-pct {{ font-size: 36px; font-weight: 300; }}
  .nrr-target-line {{ font-size: 13px; color: #94A3B8; margin-top: 8px; }}
  .nrr-target-line span {{ font-weight: 600; }}
  .arc-wrap {{ position: relative; width: 200px; height: 110px; margin: 20px auto 8px; overflow: hidden; }}
  .arc-wrap svg {{ width: 200px; height: 200px; position: absolute; top: 0; left: 0; }}
  .gap-card {{ margin-top: 16px; padding: 12px 16px; border-radius: 8px; font-size: 13px; font-weight: 500; }}
  .breakdown {{ margin-top: 20px; border-top: 1px solid #F1F5F9; padding-top: 16px; text-align: left; }}
  .breakdown-row {{ display: flex; justify-content: space-between; align-items: center; padding: 6px 0; font-size: 13px; }}
  .breakdown-label {{ color: #64748B; }}
  .breakdown-val {{ font-weight: 600; color: #0F172A; font-variant-numeric: tabular-nums; }}
  .breakdown-row.total {{ border-top: 1px solid #E2E8F0; margin-top: 4px; padding-top: 10px; font-weight: 600; }}
  .breakdown-row.total .breakdown-label {{ color: #0F172A; }}
  .sliders-panel {{ display: flex; flex-direction: column; gap: 16px; }}
  .assumptions-card {{ background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px; }}
  .assumptions-title {{ font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; color: #94A3B8; margin-bottom: 12px; }}
  .assumption-row {{ display: flex; justify-content: space-between; font-size: 13px; padding: 4px 0; }}
  .assumption-row .al {{ color: #64748B; }}
  .assumption-row .av {{ font-weight: 600; color: #0F172A; }}
  .lever-card {{ background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px; }}
  .lever-header {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px; }}
  .lever-title {{ font-size: 15px; font-weight: 600; color: #0F172A; }}
  .lever-pct {{ font-size: 22px; font-weight: 700; font-variant-numeric: tabular-nums; }}
  .lever-desc {{ font-size: 12px; color: #94A3B8; margin-bottom: 14px; line-height: 1.5; }}
  .lever-impact {{ font-size: 12px; color: #64748B; margin-top: 8px; }}

  input[type=range] {{
    -webkit-appearance: none; width: 100%; height: 4px;
    border-radius: 2px; background: #E2E8F0; outline: none; cursor: pointer;
  }}
  input[type=range]::-webkit-slider-thumb {{
    -webkit-appearance: none; width: 18px; height: 18px; border-radius: 50%;
    background: #0066FF; cursor: pointer; border: 2px solid white;
    box-shadow: 0 1px 4px rgba(0,0,0,.2);
  }}
  input[type=range]::-moz-range-thumb {{
    width: 18px; height: 18px; border-radius: 50%;
    background: #0066FF; cursor: pointer; border: 2px solid white;
  }}

  /* Copy toast */
  .copy-toast {{
    position: fixed; bottom: 24px; right: 24px; background: #0F172A; color: white;
    padding: 10px 18px; border-radius: 8px; font-size: 13px; font-weight: 500;
    opacity: 0; transform: translateY(8px); transition: all .2s ease; pointer-events: none;
  }}
  .copy-toast.show {{ opacity: 1; transform: translateY(0); }}
</style>
</head>
<body>

<!-- Top nav -->
<nav class="topnav">
  <div class="logo">{PRODUCT_NAME}<span>.</span></div>
  <button class="nav-tab active" data-tab="overview"   onclick="showTab('overview')">Overview</button>
  <button class="nav-tab"        data-tab="churn"      onclick="showTab('churn')">Churn Risk</button>
  <button class="nav-tab"        data-tab="activation" onclick="showTab('activation')">Activation</button>
  <button class="nav-tab"        data-tab="queue"      onclick="showTab('queue')">Intervention Queue</button>
  <button class="nav-tab"        data-tab="nrr"        onclick="showTab('nrr')">NRR Model</button>
  <div class="nav-date">{today}</div>
</nav>

<!-- Tab panes -->
<div id="pane-overview"   class="tab-pane active">{tab_overview}</div>
<div id="pane-churn"      class="tab-pane">{tab_churn}</div>
<div id="pane-activation" class="tab-pane">{tab_activation}</div>
<div id="pane-queue"      class="tab-pane">{tab_queue}</div>
<div id="pane-nrr"        class="tab-pane">{tab_nrr}</div>

<div class="copy-toast" id="toast">Copied to clipboard</div>

<script>
function showTab(id) {{
  document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(el => el.classList.remove('active'));
  document.getElementById('pane-' + id).classList.add('active');
  document.querySelector('[data-tab="' + id + '"]').classList.add('active');
}}

function setSortChurn(mode) {{
  document.getElementById('churn-view-score').style.display = mode === 'score' ? 'block' : 'none';
  document.getElementById('churn-view-arr').style.display   = mode === 'arr'   ? 'block' : 'none';
  document.getElementById('sort-score-btn').style.background = mode === 'score' ? '#0066FF' : '#F1F5F9';
  document.getElementById('sort-score-btn').style.color      = mode === 'score' ? 'white'   : '#64748B';
  document.getElementById('sort-arr-btn').style.background   = mode === 'arr'   ? '#0066FF' : '#F1F5F9';
  document.getElementById('sort-arr-btn').style.color        = mode === 'arr'   ? 'white'   : '#64748B';
}}

function copyEmail(btn) {{
  const text = btn.getAttribute('data-text').replace(/\\n/g, '\\n');
  navigator.clipboard.writeText(text).then(() => {{
    const toast = document.getElementById('toast');
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2000);
  }});
}}
</script>

</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Dashboard saved -> {path}")
