"""
generate_report.py — Generate a self-contained HTML operations dashboard
from all five source systems, resolved via the OWL ontology.

Every section of the report crosses at least one system boundary.
The ontology resolves EPOS site_id → Infor WFM / SAP S/4HANA / SuccessFactors IDs
before any DuckDB query runs — the same pattern as AWS COA VKG.

Charts (embedded as base64 PNG via matplotlib):
  1. KPI summary cards   — all 3 sites: revenue, labour cost/cover, SAP rev/cover, flexible %
  2. Revenue by category — grouped bar, all sites  [EPOS]
  3. Labour cost/cover   — grouped bar by meal period, all sites  [Infor WFM + EPOS]
  4. SAP revenue/cover   — grouped bar by meal period, all sites  [SAP S/4HANA]
  5. Headcount by contract type — grouped bar, all sites  [SAP SuccessFactors]
  6. Food margin         — horizontal bar by product  [EPOS + Coupa]

Output: ../reports/hospitality_report.html (single self-contained file)

Usage:
    python generate_report.py
"""
# ─────────────────────────────────────────────────────
# Author   : Amit Dixit
# GitHub   : https://github.com/inbravo
# Web      : https://inbravo.github.io
# LinkedIn : https://www.linkedin.com/in/inbravo/
# ─────────────────────────────────────────────────────

import base64
import io
import logging
import sys
from datetime import datetime
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

import logging_config
logging_config.setup()
log = logging.getLogger("hosp.report")

import metric_layer

DB_FILE     = Path(__file__).parent / "hospitality.duckdb"
REPORT_DIR  = Path(__file__).parent.parent / "reports"
REPORT_FILE = REPORT_DIR / "hospitality_report.html"

SITES = [
    ("SITE-LDN-01", "London\nCanary Wharf"),
    ("SITE-LDN-02", "London\nCity"),
    ("SITE-MAN-01", "Manchester"),
]
SITE_LABELS = ["London Canary Wharf", "London City", "Manchester"]

# ── Palette ────────────────────────────────────────────────────────────────────
NAVY    = "#0D1B2A"
C1      = "#1E6FD9"   # blue
C2      = "#E87722"   # orange
C3      = "#2E9E5B"   # green
C4      = "#9B59B6"   # purple
C5      = "#E74C3C"   # red
GRID    = "#E5E9F0"
BG      = "#F7F9FC"
TEXT    = "#1A1A2E"

SITE_COLORS = [C1, C2, C3]
CONTRACT_COLORS = {
    "PERMANENT":  C3,
    "PART_TIME":  C1,
    "ZERO_HOURS": C2,
    "AGENCY":     C5,
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.facecolor": BG,
    "figure.facecolor": "white",
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.labelcolor": TEXT,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "axes.titlecolor": NAVY,
})


# ── Chart helpers ─────────────────────────────────────────────────────────────

def fig_to_b64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def chart_revenue_by_category() -> str:
    all_cats: set = set()
    site_data: dict = {}
    for epos_id, label in SITES:
        rows = metric_layer.revenue_by_category(epos_id)
        d = {r["category"]: r["revenue_gbp"] for r in rows}
        site_data[label.replace("\n", " ")] = d
        all_cats.update(d.keys())

    cats    = sorted(all_cats)
    x       = np.arange(len(cats))
    width   = 0.25
    offsets = [(-1) * width, 0, width]

    fig, ax = plt.subplots(figsize=(9, 4.2))
    for i, label in enumerate(SITE_LABELS):
        vals = [site_data[label].get(c, 0) for c in cats]
        bars = ax.bar(x + offsets[i], vals, width, label=label,
                      color=SITE_COLORS[i], edgecolor="white", linewidth=0.5)
        for bar in bars:
            h = bar.get_height()
            if h > 30:
                ax.text(bar.get_x() + bar.get_width() / 2, h + 4,
                        f"£{h:.0f}", ha="center", va="bottom",
                        fontsize=6.5, color=NAVY, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([c.title() for c in cats], fontsize=9)
    ax.set_ylabel("Revenue (£)", fontsize=9)
    ax.set_title("Revenue by Category — All Sites  [Oracle MICROS EPOS]", pad=10)
    ax.legend(fontsize=8, framealpha=0.7)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"£{v:,.0f}"))
    fig.tight_layout()
    return fig_to_b64(fig)


def chart_labour_cost_per_cover() -> str:
    all_periods: set = set()
    site_data: dict  = {}
    for epos_id, label in SITES:
        rows = metric_layer.labour_cost_per_cover(epos_id)
        d = {r["meal_period"]: r["labour_cost_per_cover"] for r in rows}
        site_data[label.replace("\n", " ")] = d
        all_periods.update(d.keys())

    periods = sorted(all_periods)
    x       = np.arange(len(periods))
    width   = 0.25
    offsets = [(-1) * width, 0, width]

    fig, ax = plt.subplots(figsize=(8, 4))
    for i, label in enumerate(SITE_LABELS):
        vals = [site_data[label].get(p, 0) for p in periods]
        ax.bar(x + offsets[i], vals, width, label=label,
               color=SITE_COLORS[i], edgecolor="white", linewidth=0.5)

    ax.axhline(20.0, color=C5, linewidth=1.2, linestyle="--",
               label="Threshold £20.00", zorder=5)
    ax.set_xticks(x)
    ax.set_xticklabels([p.title() for p in periods], fontsize=9)
    ax.set_ylabel("£ per cover", fontsize=9)
    ax.set_title("Labour Cost per Cover by Meal Period  [Infor WFM + EPOS · identity resolved]", pad=10)
    ax.legend(fontsize=8, framealpha=0.7)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"£{v:.2f}"))
    fig.tight_layout()
    return fig_to_b64(fig)


def chart_sap_revenue_per_cover() -> str:
    all_periods: set = set()
    site_data: dict  = {}
    for epos_id, label in SITES:
        rows = metric_layer.revenue_per_cover(epos_id)
        d = {r["meal_period"]: r["revenue_per_cover"] for r in rows}
        site_data[label.replace("\n", " ")] = d
        all_periods.update(d.keys())

    periods = sorted(all_periods)
    x       = np.arange(len(periods))
    width   = 0.25
    offsets = [(-1) * width, 0, width]

    fig, ax = plt.subplots(figsize=(8, 4))
    for i, label in enumerate(SITE_LABELS):
        vals = [site_data[label].get(p, 0) for p in periods]
        bars = ax.bar(x + offsets[i], vals, width, label=label,
                      color=SITE_COLORS[i], edgecolor="white", linewidth=0.5)
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, h + 0.15,
                        f"£{h:.2f}", ha="center", va="bottom",
                        fontsize=6.5, color=NAVY, fontweight="bold")

    ax.axhline(8.0, color=C5, linewidth=1.2, linestyle="--",
               label="Threshold £8.00", zorder=5)
    ax.set_xticks(x)
    ax.set_xticklabels([p.title() for p in periods], fontsize=9)
    ax.set_ylabel("£ per cover", fontsize=9)
    ax.set_title("SAP Revenue per Cover by Meal Period  [SAP S/4HANA · identity resolved]", pad=10)
    ax.legend(fontsize=8, framealpha=0.7)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"£{v:.2f}"))
    fig.tight_layout()
    return fig_to_b64(fig)


def chart_headcount_by_contract() -> str:
    contract_types = ["PERMANENT", "PART_TIME", "ZERO_HOURS", "AGENCY"]
    site_data: dict = {}
    for epos_id, label in SITES:
        rows = metric_layer.headcount_by_contract(epos_id)
        d = {r["contract_type"]: r["headcount"] for r in rows}
        site_data[label.replace("\n", " ")] = d

    x       = np.arange(len(SITE_LABELS))
    width   = 0.18
    n       = len(contract_types)
    offsets = [(i - (n - 1) / 2) * width for i in range(n)]

    fig, ax = plt.subplots(figsize=(9, 4.2))
    for i, ct in enumerate(contract_types):
        vals = [site_data[label].get(ct, 0) for label in SITE_LABELS]
        color = CONTRACT_COLORS.get(ct, C4)
        bars = ax.bar(x + offsets[i], vals, width, label=ct.replace("_", " ").title(),
                      color=color, edgecolor="white", linewidth=0.5)
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, h + 0.1,
                        str(int(h)), ha="center", va="bottom",
                        fontsize=7, color=NAVY, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(SITE_LABELS, fontsize=9)
    ax.set_ylabel("Headcount", fontsize=9)
    ax.set_title("Headcount by Contract Type  [SAP SuccessFactors · identity resolved]", pad=10)
    ax.legend(fontsize=8, framealpha=0.7)
    fig.tight_layout()
    return fig_to_b64(fig)


def chart_food_margin() -> str:
    rows = metric_layer.food_margin_by_product("SITE-LDN-01")
    products = [r["product_name"] for r in rows]
    margins  = [r["gross_margin_gbp"] for r in rows]

    y  = np.arange(len(products))
    fig, ax = plt.subplots(figsize=(9, max(3.5, len(products) * 0.7 + 1)))

    colors = [C3 if m >= 0.5 else C5 for m in margins]
    bars = ax.barh(y, margins, color=colors, edgecolor="white", height=0.55)
    for bar, m in zip(bars, margins):
        w = bar.get_width()
        ax.text(w + 0.02, bar.get_y() + bar.get_height() / 2,
                f"£{m:.2f}", va="center", fontsize=9, fontweight="bold",
                color=NAVY)

    ax.axvline(1.0, color=C5, linewidth=1.2, linestyle="--",
               label="Min margin £1.00", zorder=5)
    ax.set_yticks(y)
    ax.set_yticklabels(products, fontsize=9)
    ax.set_xlabel("Gross Margin per Unit (£)", fontsize=9)
    ax.set_title("Food Margin by Product — London Canary Wharf  [EPOS + Coupa · identity resolved]", pad=10)
    ax.legend(fontsize=8, framealpha=0.7)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"£{v:.2f}"))
    fig.tight_layout()
    return fig_to_b64(fig)


# ── KPI data ──────────────────────────────────────────────────────────────────

def build_kpi_table() -> list[dict]:
    rows = []
    for epos_id, raw_label in SITES:
        label = raw_label.replace("\n", " ")
        site  = metric_layer.resolve_site(epos_id)

        rev_rows  = metric_layer.revenue_by_category(epos_id)
        total_rev = sum(r["revenue_gbp"] for r in rev_rows)

        lc_rows = metric_layer.labour_cost_per_cover(epos_id)
        if lc_rows:
            total_labour_gbp = lc_rows[0]["total_labour_gbp"]
            total_covers     = sum(r["covers"] for r in lc_rows)
            avg_lc = round(total_labour_gbp / total_covers, 2) if total_covers else 0.0
        else:
            avg_lc = 0.0

        sap_rows = metric_layer.revenue_per_cover(epos_id)
        avg_sap_rev = (sum(r["revenue_per_cover"] for r in sap_rows) / len(sap_rows)
                       if sap_rows else 0.0)

        hc_rows = metric_layer.headcount_by_contract(epos_id)
        total_hc  = sum(r["headcount"] for r in hc_rows)
        flex_hc   = sum(r["headcount"] for r in hc_rows
                        if r["contract_type"] in ("ZERO_HOURS", "AGENCY"))
        flex_pct  = round(flex_hc / total_hc * 100, 1) if total_hc else 0.0

        rows.append({
            "site":           label,
            "epos_id":        site["epos_site_id"],
            "infor_id":       site["infor_site_code"],
            "sap_cc":         site["sap_cost_center"],
            "sf_ou":          site["sf_org_unit_id"],
            "revenue":        total_rev,
            "lc_per_cover":   avg_lc,
            "sap_rev_cover":  round(avg_sap_rev, 2),
            "flex_pct":       flex_pct,
        })
    return rows


def flag(value, threshold, direction="above") -> str:
    bad = value > threshold if direction == "above" else value < threshold
    return "kpi-bad" if bad else "kpi-good"


# ── HTML ───────────────────────────────────────────────────────────────────────

CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

:root {
  --bg:        #F3F6FB;
  --surface:   #FFFFFF;
  --border:    #E1E8F4;
  --navy:      #1C2B45;
  --accent:    #E8993A;
  --accent-dim:#F5C887;
  --text:      #1C2B45;
  --muted:     #617292;
  --good:      #1E7A50;
  --good-bg:   #EAF6F0;
  --bad:       #C23B3B;
  --bad-bg:    #FDEAEA;
  --mono-bg:   #0E1929;
  --mono-text: #A8BFDA;
  --mono-hl:   #6CB8F5;
  --mono-grn:  #5CC898;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg:        #0F1623;
    --surface:   #182030;
    --border:    #24334D;
    --navy:      #D6E4F7;
    --text:      #D6E4F7;
    --muted:     #8A9FBF;
    --good:      #3EAD72;
    --good-bg:   #0E2E1E;
    --bad:       #E05555;
    --bad-bg:    #2E0E0E;
    --accent:    #F0A84A;
    --accent-dim:#8A5A1A;
  }
}
:root[data-theme="dark"] {
  --bg:        #0F1623;
  --surface:   #182030;
  --border:    #24334D;
  --navy:      #D6E4F7;
  --text:      #D6E4F7;
  --muted:     #8A9FBF;
  --good:      #3EAD72;
  --good-bg:   #0E2E1E;
  --bad:       #E05555;
  --bad-bg:    #2E0E0E;
  --accent:    #F0A84A;
  --accent-dim:#8A5A1A;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }

body {
  font-family: 'Inter', system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  font-size: 14px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

header {
  background: var(--mono-bg);
  color: #E2EBF7;
  padding: 36px 48px 32px;
  position: relative;
  overflow: hidden;
}
header::after {
  content: '';
  position: absolute; bottom: 0; left: 0; right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--accent) 0%, #D4753A 40%, transparent 100%);
}
.header-eyebrow {
  font-family: 'DM Mono', monospace;
  font-size: 11px; letter-spacing: .12em; text-transform: uppercase;
  color: var(--accent); margin-bottom: 10px;
}
header h1 {
  font-family: 'DM Serif Display', Georgia, serif;
  font-size: 28px; font-weight: 400; line-height: 1.2;
  color: #FFFFFF; margin-bottom: 8px;
  text-wrap: balance;
}
header p { font-size: 13px; color: #8FAAC8; max-width: 640px; }

.badges { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 20px; }
.badge {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 11px; font-weight: 600; letter-spacing: .03em;
  padding: 4px 11px; border-radius: 20px; border: 1px solid;
}
.badge-sys  { color: var(--accent); border-color: #4A3010; background: #1E1408; }
.badge-ont  { color: #5CC898;       border-color: #0E3020; background: #0A1E12; }
.badge-db   { color: #6CB8F5;       border-color: #0A2540; background: #091520; }
.header-meta {
  margin-top: 14px; font-family: 'DM Mono', monospace;
  font-size: 10.5px; color: #5A7090; letter-spacing: .04em;
}

main { max-width: 1160px; margin: 0 auto; padding: 36px 32px 72px; }

.section-head {
  display: flex; align-items: baseline; gap: 12px;
  margin: 40px 0 16px;
}
.section-head h2 {
  font-family: 'Inter', sans-serif;
  font-size: 12px; font-weight: 700; letter-spacing: .1em;
  text-transform: uppercase; color: var(--muted);
}
.section-head .sys-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.sys-tag {
  font-family: 'DM Mono', monospace;
  font-size: 10px; padding: 2px 8px; border-radius: 4px;
  background: var(--border); color: var(--muted);
  border: 1px solid var(--border);
}

.kpi-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 20px; }
.kpi-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 22px 24px;
  position: relative;
  overflow: hidden;
}
.kpi-card::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: var(--accent);
}
.kpi-site {
  font-family: 'DM Serif Display', Georgia, serif;
  font-size: 17px; font-weight: 400; color: var(--text);
  margin-bottom: 18px; line-height: 1.3;
  text-wrap: balance;
}
.kpi-rows { display: flex; flex-direction: column; gap: 10px; }
.kpi-row  { display: flex; justify-content: space-between; align-items: baseline; }
.kpi-label {
  font-size: 11px; color: var(--muted); font-weight: 500;
  letter-spacing: .02em;
}
.kpi-value {
  font-size: 18px; font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--text);
}
.kpi-good { color: var(--good); }
.kpi-bad  { color: var(--bad);  }

.id-strip {
  margin-top: 18px; padding: 10px 13px;
  background: var(--bg); border: 1px solid var(--border);
  border-radius: 7px;
  font-family: 'DM Mono', monospace;
  font-size: 10px; color: var(--muted); line-height: 2;
}
.id-strip .sys-name { color: var(--muted); font-size: 9.5px; }
.id-strip code {
  background: var(--mono-bg); color: var(--mono-hl);
  padding: 1px 6px; border-radius: 3px; font-size: 10px;
}
.id-arrow { color: var(--accent); margin: 0 3px; }

.chart-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 28px 28px 20px;
  margin-bottom: 20px;
  overflow-x: auto;
}
.chart-card img { width: 100%; height: auto; display: block; max-width: 100%; }

.proof-box {
  background: var(--mono-bg);
  border: 1px solid #1E3050;
  border-radius: 12px;
  padding: 28px 32px;
  margin-top: 40px;
  overflow-x: auto;
}
.proof-box-header {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 20px;
}
.proof-box-header h4 {
  font-family: 'DM Mono', monospace;
  font-size: 11px; font-weight: 500;
  letter-spacing: .1em; text-transform: uppercase;
  color: var(--mono-hl);
}
.proof-dot {
  width: 8px; height: 8px; border-radius: 50%;
  display: inline-block; margin-right: 3px;
}
.proof-box pre {
  font-family: 'DM Mono', monospace;
  font-size: 11.5px; line-height: 1.85;
  color: var(--mono-text); white-space: pre-wrap; word-break: break-word;
}
.proof-kw   { color: #C792EA; }
.proof-prop { color: var(--mono-hl); }
.proof-val  { color: #C3E88D; }
.proof-result {
  margin-top: 18px; padding: 12px 16px;
  background: #091520; border-left: 3px solid var(--mono-grn);
  border-radius: 0 6px 6px 0;
  font-family: 'DM Mono', monospace; font-size: 11px;
  color: var(--mono-grn); line-height: 1.9;
}
.proof-note {
  margin-top: 14px; font-size: 11.5px; color: #5A7090;
  font-family: 'Inter', sans-serif; line-height: 1.6;
}

footer {
  text-align: center; padding: 28px 24px 20px;
  border-top: 1px solid var(--border);
  font-size: 11px; color: var(--muted);
  margin-top: 56px; letter-spacing: .03em;
}
footer a { color: var(--accent); text-decoration: none; }

@media (max-width: 760px) {
  .kpi-grid { grid-template-columns: 1fr; }
  header { padding: 28px 24px 24px; }
  main { padding: 24px 18px 56px; }
}
"""


def kpi_card(kpi: dict) -> str:
    lc_class  = flag(kpi["lc_per_cover"],  20.0, "above")
    sap_class = flag(kpi["sap_rev_cover"],   8.0, "below")
    fl_class  = flag(kpi["flex_pct"],       30.0, "above")

    return f"""
<div class="kpi-card">
  <div class="kpi-site">{kpi['site']}</div>
  <div class="kpi-rows">
    <div class="kpi-row">
      <span class="kpi-label">Total Revenue (EPOS)</span>
      <span class="kpi-value">£{kpi['revenue']:,.0f}</span>
    </div>
    <div class="kpi-row">
      <span class="kpi-label">Labour Cost / Cover</span>
      <span class="kpi-value {lc_class}">£{kpi['lc_per_cover']:.2f}</span>
    </div>
    <div class="kpi-row">
      <span class="kpi-label">SAP Revenue / Cover</span>
      <span class="kpi-value {sap_class}">£{kpi['sap_rev_cover']:.2f}</span>
    </div>
    <div class="kpi-row">
      <span class="kpi-label">Flexible Contracts %</span>
      <span class="kpi-value {fl_class}">{kpi['flex_pct']:.1f}%</span>
    </div>
  </div>
  <div class="id-strip">
    <span class="sys-name">EPOS</span> <code>{kpi['epos_id']}</code>
    <span class="id-arrow">&#8594;</span>
    <span class="sys-name">Infor WFM</span> <code>{kpi['infor_id']}</code>
    &nbsp;&middot;&nbsp;
    <span class="sys-name">SAP CC</span> <code>{kpi['sap_cc']}</code>
    &nbsp;&middot;&nbsp;
    <span class="sys-name">SF OU</span> <code>{kpi['sf_ou']}</code>
  </div>
</div>"""


def build_html(kpis, charts: dict) -> str:
    now      = datetime.now().strftime("%d %b %Y %H:%M")
    kpi_html = "\n".join(kpi_card(k) for k in kpis)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hospitality Ops Dashboard</title>
<style>{CSS}</style>
</head>
<body>

<header>
  <div class="header-eyebrow">Context Engineering &mdash; Example 14</div>
  <h1>Hospitality Group<br>Operations Dashboard</h1>
  <p>Five source systems. Four different site ID formats. One OWL ontology that resolves them all before any query runs.</p>
  <div class="badges">
    <span class="badge badge-sys">Oracle MICROS EPOS</span>
    <span class="badge badge-sys">Infor WFM</span>
    <span class="badge badge-sys">SAP S/4HANA</span>
    <span class="badge badge-sys">SAP SuccessFactors</span>
    <span class="badge badge-sys">Coupa</span>
    <span class="badge badge-ont">OWL Identity Resolution</span>
    <span class="badge badge-db">rdflib &bull; DuckDB &bull; qwen2.5</span>
  </div>
  <div class="header-meta">Generated {now} &nbsp;&middot;&nbsp; August 2026 (30 days) &nbsp;&middot;&nbsp; 3 sites &nbsp;&middot;&nbsp; 5 source systems</div>
</header>

<main>

<div class="section-head">
  <h2>Site KPIs</h2>
  <div class="sys-tags">
    <span class="sys-tag">EPOS &rarr; Oracle MICROS</span>
    <span class="sys-tag">WFM &rarr; Infor</span>
    <span class="sys-tag">Sales &rarr; SAP S/4HANA</span>
    <span class="sys-tag">HR &rarr; SuccessFactors</span>
  </div>
</div>
<div class="kpi-grid">
{kpi_html}
</div>

<div class="section-head">
  <h2>Revenue by Category</h2>
  <div class="sys-tags"><span class="sys-tag">Oracle MICROS EPOS &rarr; epos_transactions</span></div>
</div>
<div class="chart-card">
  <img src="data:image/png;base64,{charts['revenue']}" alt="Revenue by category">
</div>

<div class="section-head">
  <h2>Labour Cost per Cover</h2>
  <div class="sys-tags">
    <span class="sys-tag">Infor WFM &rarr; GBR_SITE_0001</span>
    <span class="sys-tag">Oracle MICROS EPOS &rarr; SITE-LDN-01</span>
    <span class="sys-tag">&#8594; identity resolved via hosp:inforSiteCode</span>
  </div>
</div>
<div class="chart-card">
  <img src="data:image/png;base64,{charts['labour']}" alt="Labour cost per cover">
</div>

<div class="section-head">
  <h2>SAP Revenue per Cover</h2>
  <div class="sys-tags">
    <span class="sys-tag">SAP S/4HANA &rarr; CC-GBR-001</span>
    <span class="sys-tag">&#8594; identity resolved via hosp:sapCostCenter</span>
  </div>
</div>
<div class="chart-card">
  <img src="data:image/png;base64,{charts['sap_revenue']}" alt="SAP revenue per cover">
</div>

<div class="section-head">
  <h2>Headcount by Contract Type</h2>
  <div class="sys-tags">
    <span class="sys-tag">SAP SuccessFactors &rarr; OU-GBR-001</span>
    <span class="sys-tag">&#8594; identity resolved via hosp:sfOrgUnitId</span>
  </div>
</div>
<div class="chart-card">
  <img src="data:image/png;base64,{charts['headcount']}" alt="Headcount by contract type">
</div>

<div class="section-head">
  <h2>Food Margin by Product</h2>
  <div class="sys-tags">
    <span class="sys-tag">EPOS item_id: EPOS-LATTE</span>
    <span class="sys-tag">Coupa SKU: PROD-BEV-001</span>
    <span class="sys-tag">&#8594; identity resolved via hosp:eposItemId / hosp:procProductId</span>
  </div>
</div>
<div class="chart-card">
  <img src="data:image/png;base64,{charts['margin']}" alt="Food margin by product">
</div>

<div class="proof-box">
  <div class="proof-box-header">
    <span class="proof-dot" style="background:#E05555;"></span>
    <span class="proof-dot" style="background:#E8993A;"></span>
    <span class="proof-dot" style="background:#5CC898;"></span>
    <h4>Ontology Identity Resolution &mdash; SPARQL query that powers every cross-system metric</h4>
  </div>
  <pre><span class="proof-kw">PREFIX</span> hosp: &lt;http://hospitality.example.org/ontology#&gt;
<span class="proof-kw">SELECT</span> <span class="proof-prop">?epos_id ?infor_code ?sap_cc ?sf_org ?site_name</span> <span class="proof-kw">WHERE</span> &#123;
    ?site <span class="proof-prop">hosp:eposSiteId</span>    <span class="proof-prop">?epos_id</span>    ;
          <span class="proof-prop">hosp:inforSiteCode</span> <span class="proof-prop">?infor_code</span> ;
          <span class="proof-prop">hosp:sapCostCenter</span> <span class="proof-prop">?sap_cc</span>     ;
          <span class="proof-prop">hosp:sfOrgUnitId</span>   <span class="proof-prop">?sf_org</span>     ;
          <span class="proof-prop">hosp:siteName</span>      <span class="proof-prop">?site_name</span> .
    <span class="proof-kw">FILTER</span>(?epos_id = <span class="proof-val">"SITE-LDN-01"</span>)
&#125;</pre>
  <div class="proof-result">
    &#10140;&nbsp; epos_id=<span style="color:#F5C887">"SITE-LDN-01"</span>
    &nbsp;&middot;&nbsp; infor_code=<span style="color:#F5C887">"GBR_SITE_0001"</span>
    &nbsp;&middot;&nbsp; sap_cc=<span style="color:#F5C887">"CC-GBR-001"</span>
    &nbsp;&middot;&nbsp; sf_org=<span style="color:#F5C887">"OU-GBR-001"</span>
    &nbsp;&middot;&nbsp; site_name=<span style="color:#F5C887">"London Canary Wharf"</span>
  </div>
  <p class="proof-note">
    Without this resolution, Infor WFM / SAP S/4HANA / SuccessFactors queries return 0 rows &mdash;
    their site_id formats don&rsquo;t match EPOS. The ontology is the only key that connects all five systems.
    In production, AWS COA runs the equivalent query against its Virtual Knowledge Graph (Ontop) over Amazon Neptune.
  </p>
</div>

</main>

<footer>
  <a href="https://github.com/inbravo/my-hello-worlds" target="_blank">github.com/inbravo/my-hello-worlds</a>
  &nbsp;&middot;&nbsp; Stack: rdflib &middot; DuckDB &middot; matplotlib &middot; Ollama qwen2.5
  &nbsp;&middot;&nbsp; Amit Dixit
</footer>

</body>
</html>"""


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    log.info("generate_report starting — db=%s", DB_FILE)
    if not DB_FILE.exists():
        log.error("DB not found: %s — run bootstrap_hospitality.py first", DB_FILE)
        print("ERROR: hospitality.duckdb not found — run bootstrap_hospitality.py first.")
        sys.exit(1)
    ttl = Path(__file__).parent.parent / "ontology" / "hospitality_ontology.ttl"
    if not ttl.exists():
        log.error("Ontology not found: %s — run generate_ontology.py first", ttl)
        print("ERROR: ontology not found — run generate_ontology.py first.")
        sys.exit(1)

    print("Building KPI data from all 5 systems...")
    log.info("Building KPI table for %d sites", len(SITES))
    kpis = build_kpi_table()
    for k in kpis:
        log.debug(
            "KPI: site=%s  revenue=£%.0f  lc_per_cover=£%.2f  sap_rev_cover=£%.2f  flex=%.1f%%",
            k["site"], k["revenue"], k["lc_per_cover"], k["sap_rev_cover"], k["flex_pct"],
        )
        print(f"  {k['site']}: revenue=£{k['revenue']:,.0f}  lc/cover=£{k['lc_per_cover']:.2f}"
              f"  SAP rev/cover=£{k['sap_rev_cover']:.2f}  flexible={k['flex_pct']:.1f}%")

    print("Rendering charts...")
    log.info("Rendering 5 charts")
    charts = {
        "revenue":     chart_revenue_by_category(),
        "labour":      chart_labour_cost_per_cover(),
        "sap_revenue": chart_sap_revenue_per_cover(),
        "headcount":   chart_headcount_by_contract(),
        "margin":      chart_food_margin(),
    }
    log.debug("Charts rendered: %s", list(charts.keys()))
    print(f"  {len(charts)} charts rendered")

    html = build_html(kpis, charts)

    REPORT_DIR.mkdir(exist_ok=True)
    REPORT_FILE.write_text(html, encoding="utf-8")

    size_kb = REPORT_FILE.stat().st_size // 1024
    log.info("Report written: %s  (%d KB)", REPORT_FILE, size_kb)
    print(f"\nReport written : {REPORT_FILE}  ({size_kb} KB)")
    print("Open in a browser to view the dashboard.")


if __name__ == "__main__":
    main()
