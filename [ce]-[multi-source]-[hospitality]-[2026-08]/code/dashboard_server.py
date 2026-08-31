"""
dashboard_server.py — Live operations dashboard for the Hospitality Group.

Two query modes:
  1. /api/ask   — natural language → Ollama qwen2.5 agent → tool calls →
                  structured chart data returned to browser
  2. /api/metric — direct metric query (no LLM) → chart data

The browser (dashboard.html embedded below) renders Chart.js charts
dynamically from the API response. Every cross-system metric runs SPARQL
first to resolve site IDs before touching DuckDB.

Usage:
    python dashboard_server.py
    # open http://localhost:8765
"""
# ─────────────────────────────────────────────────────
# Author   : Amit Dixit
# GitHub   : https://github.com/inbravo
# Web      : https://inbravo.github.io
# LinkedIn : https://www.linkedin.com/in/inbravo/
# ─────────────────────────────────────────────────────

import json
import logging
import sys
import traceback
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent))
import logging_config
logging_config.setup()
log = logging.getLogger("hosp.server")

import metric_layer

# ── Config ─────────────────────────────────────────────────────────────────────
PORT            = 8765
OLLAMA_BASE_URL = "http://localhost:11434/v1"
MODEL           = "qwen2.5"

app = FastAPI(title="Hospitality Dashboard API")

SITES = [
    {"id": "SITE-LDN-01", "name": "London Canary Wharf"},
    {"id": "SITE-LDN-02", "name": "London City"},
    {"id": "SITE-MAN-01", "name": "Manchester"},
]

METRIC_REGISTRY = {
    "labour_cost_per_cover": {
        "fn":          metric_layer.labour_cost_per_cover,
        "description": "Labour cost per meal served (cover). Joins WFM shifts + EPOS transactions.",
        "systems":     ["WFM", "EPOS"],
        "chart":       "bar_meal_period",
    },
    "revenue_by_category": {
        "fn":          metric_layer.revenue_by_category,
        "description": "EPOS revenue grouped by product category.",
        "systems":     ["EPOS"],
        "chart":       "bar_category",
    },
    "food_margin_by_product": {
        "fn":          metric_layer.food_margin_by_product,
        "description": "Selling price vs procurement contracted cost per product.",
        "systems":     ["EPOS", "Procurement"],
        "chart":       "hbar_product",
    },
    "revenue_per_cover": {
        "fn":          metric_layer.revenue_per_cover,
        "description": "SAP S/4HANA net revenue per cover billed by meal period (cost-centre resolved via ontology).",
        "systems":     ["SAP Sales (S/4HANA)"],
        "chart":       "bar_meal_period",
    },
    "headcount_by_contract": {
        "fn":          metric_layer.headcount_by_contract,
        "description": "SuccessFactors headcount and FTE by contract type (org-unit resolved via ontology).",
        "systems":     ["HR & Payroll (SuccessFactors)"],
        "chart":       "bar_contract",
    },
}

# ── LLM tool definitions ───────────────────────────────────────────────────────
LLM_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_labour_cost_per_cover",
            "description": "Labour cost per meal served by meal period. Joins WFM + EPOS via ontology-resolved site IDs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "epos_site_id": {"type": "string",
                                     "description": "Site ID in EPOS format, e.g. SITE-LDN-01"}
                },
                "required": ["epos_site_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_revenue_by_category",
            "description": "EPOS revenue grouped by product category for a site.",
            "parameters": {
                "type": "object",
                "properties": {
                    "epos_site_id": {"type": "string"}
                },
                "required": ["epos_site_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_food_margin_by_product",
            "description": "Gross margin per product: EPOS selling price minus procurement contracted cost.",
            "parameters": {
                "type": "object",
                "properties": {
                    "epos_site_id": {"type": "string"}
                },
                "required": ["epos_site_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_revenue_per_cover",
            "description": "SAP S/4HANA net revenue per cover billed by meal period. SAP uses cost_center_code (CC-GBR-001), resolved from EPOS site_id via the ontology.",
            "parameters": {
                "type": "object",
                "properties": {
                    "epos_site_id": {"type": "string"}
                },
                "required": ["epos_site_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_headcount_by_contract",
            "description": "SAP SuccessFactors headcount and FTE by contract type (PERMANENT, PART_TIME, ZERO_HOURS, AGENCY). SF uses org_unit_id (OU-GBR-001), resolved from EPOS site_id via the ontology.",
            "parameters": {
                "type": "object",
                "properties": {
                    "epos_site_id": {"type": "string"}
                },
                "required": ["epos_site_id"],
            },
        },
    },
]

SYSTEM_PROMPT = """You are an operations intelligence agent for a UK Hospitality Group.
Five source systems — Oracle MICROS EPOS, Infor WFM, SAP S/4HANA, SAP SuccessFactors, Coupa Procurement.
Each system uses a different site ID format for the same site. The identity resolution is automatic via OWL SPARQL.
Always pass the EPOS site_id (e.g. SITE-LDN-01) to your tools.
Sites: SITE-LDN-01 (London Canary Wharf), SITE-LDN-02 (London City), SITE-MAN-01 (Manchester).
Be concise. Lead with the headline finding, then key numbers."""


# ── Chart builders ─────────────────────────────────────────────────────────────

def build_chart(metric_name: str, rows: Any) -> dict:
    """Convert metric data into a Chart.js-compatible config dict."""
    SITE_COLORS = {
        "SITE-LDN-01": "#1E6FD9",
        "SITE-LDN-02": "#E87722",
        "SITE-MAN-01": "#2E9E5B",
    }
    DEFAULT_COLOR = "#1E6FD9"

    if metric_name in ("get_labour_cost_per_cover", "labour_cost_per_cover"):
        if not rows:
            return {}
        site_name = rows[0].get("site", "Site")
        color     = SITE_COLORS.get(rows[0].get("epos_site_id", ""), DEFAULT_COLOR)
        return {
            "type":    "bar",
            "title":   f"Labour Cost per Cover — {site_name}",
            "subtitle": f"Infor WFM shift costs ÷ EPOS cover count  [GBR_SITE_0001 ↔ SITE-LDN-01, identity resolved]",
            "labels":  [r["meal_period"].title() for r in rows],
            "datasets": [{
                "label":           "£ / cover",
                "data":            [r["labour_cost_per_cover"] for r in rows],
                "backgroundColor": color + "CC",
                "borderColor":     color,
                "borderWidth":     1,
            }],
            "yLabel":    "£ per cover",
            "threshold": {"value": 20.0, "label": "Threshold £20"},
        }

    if metric_name in ("get_revenue_by_category", "revenue_by_category"):
        if not rows:
            return {}
        site_name = rows[0].get("site", "Site")
        palette   = ["#1E6FD9", "#E87722", "#2E9E5B", "#9B59B6", "#E74C3C"]
        return {
            "type":    "bar",
            "title":   f"Revenue by Category — {site_name}",
            "subtitle": "EPOS transactions grouped by product category",
            "labels":  [r["category"].title() for r in rows],
            "datasets": [{
                "label":           "Revenue £",
                "data":            [r["revenue_gbp"] for r in rows],
                "backgroundColor": [palette[i % len(palette)] + "CC" for i in range(len(rows))],
                "borderColor":     [palette[i % len(palette)] for i in range(len(rows))],
                "borderWidth":     1,
            }],
            "yLabel": "Revenue (£)",
        }

    if metric_name in ("get_food_margin_by_product", "food_margin_by_product"):
        if not rows:
            return {}
        site_name = rows[0].get("site", "Site")
        colors    = ["#2E9E5B" if r["gross_margin_gbp"] >= 1.0 else "#E74C3C" for r in rows]
        return {
            "type":    "horizontalBar",
            "title":   f"Food Margin by Product — {site_name}",
            "subtitle": "EPOS sell price – Procurement contracted cost  [EPOS-LATTE ↔ PROD-BEV-001]",
            "labels":  [r["product_name"] for r in rows],
            "datasets": [{
                "label":           "Gross Margin £",
                "data":            [r["gross_margin_gbp"] for r in rows],
                "backgroundColor": [c + "CC" for c in colors],
                "borderColor":     colors,
                "borderWidth":     1,
            }],
            "xLabel":    "£ per unit",
            "threshold": {"value": 1.0, "label": "Min £1.00"},
        }

    if metric_name in ("get_revenue_per_cover", "revenue_per_cover"):
        if not rows:
            return {}
        site_name = rows[0].get("site", "Site")
        sap_cc    = rows[0].get("sap_cost_center", "")
        color     = SITE_COLORS.get(rows[0].get("epos_site_id", ""), DEFAULT_COLOR) if rows else DEFAULT_COLOR
        return {
            "type":    "bar",
            "title":   f"SAP Revenue per Cover — {site_name}",
            "subtitle": f"SAP S/4HANA sales invoices ÷ covers billed  [CC {sap_cc} ↔ SITE-LDN-01, identity resolved]",
            "labels":  [r["meal_period"].title() for r in rows],
            "datasets": [{
                "label":           "£ / cover",
                "data":            [r["revenue_per_cover"] for r in rows],
                "backgroundColor": color + "CC",
                "borderColor":     color,
                "borderWidth":     1,
            }],
            "yLabel":    "£ per cover",
            "threshold": {"value": 8.0, "label": "Target £8.00"},
        }

    if metric_name in ("get_headcount_by_contract", "headcount_by_contract"):
        if not rows:
            return {}
        site_name = rows[0].get("site", "Site")
        sf_org    = rows[0].get("sf_org_unit_id", "")
        palette   = {"PERMANENT": "#1E6FD9", "PART_TIME": "#2E9E5B", "ZERO_HOURS": "#E87722", "AGENCY": "#E74C3C"}
        colors    = [palette.get(r["contract_type"], DEFAULT_COLOR) for r in rows]
        return {
            "type":    "bar",
            "title":   f"Headcount by Contract — {site_name}",
            "subtitle": f"SAP SuccessFactors HR records  [OU {sf_org} ↔ SITE-LDN-01, identity resolved]",
            "labels":  [r["contract_type"].replace("_", " ").title() for r in rows],
            "datasets": [{
                "label":           "Headcount",
                "data":            [r["headcount"] for r in rows],
                "backgroundColor": [c + "CC" for c in colors],
                "borderColor":     colors,
                "borderWidth":     1,
            }],
            "yLabel": "Headcount",
        }

    return {}


def dispatch_tool(fn_name: str, args: dict) -> tuple[Any, dict]:
    """Run a metric tool and return (result, resolution)."""
    epos_id    = args.get("epos_site_id", "SITE-LDN-01")
    resolution = metric_layer.resolve_site(epos_id)

    fn_map = {
        "get_labour_cost_per_cover":  metric_layer.labour_cost_per_cover,
        "get_revenue_by_category":    metric_layer.revenue_by_category,
        "get_food_margin_by_product": metric_layer.food_margin_by_product,
        "get_revenue_per_cover":      metric_layer.revenue_per_cover,
        "get_headcount_by_contract":  metric_layer.headcount_by_contract,
    }
    fn     = fn_map.get(fn_name)
    result = fn(epos_id) if fn else {"error": f"Unknown tool: {fn_name}"}
    return result, resolution


# ── API models ─────────────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str

class MetricRequest(BaseModel):
    metric: str
    site:   str = "SITE-LDN-01"


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/api/sites")
def get_sites():
    return SITES

@app.get("/api/metrics")
def get_metrics():
    return [
        {"name": k, "description": v["description"], "systems": v["systems"]}
        for k, v in METRIC_REGISTRY.items()
    ]

@app.post("/api/metric")
def run_metric(req: MetricRequest):
    log.info("POST /api/metric  metric=%s  site=%s", req.metric, req.site)
    if req.metric not in METRIC_REGISTRY:
        log.warning("Unknown metric requested: %s", req.metric)
        raise HTTPException(400, f"Unknown metric: {req.metric}")
    try:
        resolution = metric_layer.resolve_site(req.site)
        fn         = METRIC_REGISTRY[req.metric]["fn"]
        data       = fn(req.site)
        chart      = build_chart(req.metric, data)
        log.debug("run_metric: %s  rows=%d", req.metric, len(data) if isinstance(data, list) else 1)
        return {
            "metric":     req.metric,
            "resolution": resolution,
            "data":       data,
            "chart":      chart,
        }
    except Exception as e:
        log.error("run_metric error: metric=%s site=%s  error=%s", req.metric, req.site, e)
        raise HTTPException(500, str(e))

@app.post("/api/ask")
def ask_agent(req: AskRequest):
    log.info("POST /api/ask  question=%r", req.question[:120])
    client   = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": req.question},
    ]
    steps = []

    try:
        for turn in range(10):
            log.debug("LLM turn %d — messages in context: %d", turn + 1, len(messages))
            response = client.chat.completions.create(
                model=MODEL, messages=messages,
                tools=LLM_TOOLS, tool_choice="auto",
            )
            msg = response.choices[0].message
            messages.append(msg)

            if not msg.tool_calls:
                log.info("Agent answer (turn %d): %s", turn + 1, (msg.content or "")[:200])
                return {
                    "answer": msg.content or "",
                    "steps":  steps,
                }

            for tc in msg.tool_calls:
                args   = json.loads(tc.function.arguments)
                log.info("Tool call: %s  args=%s", tc.function.name, args)
                result, resolution = dispatch_tool(tc.function.name, args)
                log.debug("Tool result: %s  rows=%s", tc.function.name,
                          len(result) if isinstance(result, list) else type(result).__name__)
                chart  = build_chart(tc.function.name, result)
                steps.append({
                    "tool":       tc.function.name,
                    "args":       args,
                    "resolution": resolution,
                    "data":       result if isinstance(result, list) else [result],
                    "chart":      chart,
                })
                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc.id,
                    "content":      json.dumps(result, default=str),
                })

        log.warning("Max turns reached. question=%s", req.question[:80])
        return {"answer": "Max turns reached.", "steps": steps}

    except Exception as e:
        log.error("ask_agent error: %s", e, exc_info=True)
        traceback.print_exc()
        raise HTTPException(500, str(e))


# ── Embedded dashboard HTML ────────────────────────────────────────────────────

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hospitality Ops Dashboard</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root {
  --bg:        #F3F6FB; --surface: #FFFFFF; --border: #E1E8F4;
  --navy:      #1C2B45; --accent:  #E8993A; --text:   #1C2B45;
  --muted:     #617292; --good:    #1E7A50; --bad:    #C23B3B;
  --header-bg: #1C2B45;
  --mono-bg:   #E2EAF6; --mono-hl: #1A4A8A; --mono-grn: #1A7A52;
  --chip-bg:   #CDD8EF;
  --shadow:    0 2px 12px rgba(0,0,0,.08);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0F1623; --surface: #182030; --border: #24334D;
    --navy: #D6E4F7; --text: #D6E4F7; --muted: #8A9FBF;
    --good: #3EAD72; --bad: #E05555; --accent: #F0A84A;
    --header-bg: #0A1120;
    --mono-bg: #0E1929; --mono-hl: #6CB8F5; --mono-grn: #5CC898;
    --chip-bg: #1A2E45;
  }
}
:root[data-theme="dark"] {
  --bg: #0F1623; --surface: #182030; --border: #24334D;
  --navy: #D6E4F7; --text: #D6E4F7; --muted: #8A9FBF;
  --good: #3EAD72; --bad: #E05555; --accent: #F0A84A;
  --header-bg: #0A1120;
  --mono-bg: #0E1929; --mono-hl: #6CB8F5; --mono-grn: #5CC898;
  --chip-bg: #1A2E45;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text);
       font-size: 14px; line-height: 1.6; -webkit-font-smoothing: antialiased; }

/* Header */
header { background: var(--header-bg); padding: 24px 40px 20px; position: relative; }
header::after { content:''; position:absolute; bottom:0; left:0; right:0; height:3px;
  background: linear-gradient(90deg, var(--accent) 0%, #D4753A 40%, transparent 100%); }
.eyebrow { font-family:'DM Mono',monospace; font-size:10.5px; letter-spacing:.12em;
           text-transform:uppercase; color:var(--accent); margin-bottom:6px; }
header h1 { font-family:'DM Serif Display',serif; font-size:24px; font-weight:400;
            color:#fff; line-height:1.2; }
header p  { font-size:12px; color:#8FAAC8; margin-top:4px; }

/* Two-panel layout */
.layout { display:grid; grid-template-columns:300px 1fr; height:calc(100vh - 80px); }

/* Sidebar */
.sidebar { background:var(--surface); border-right:1px solid var(--border);
           overflow-y:auto; display:flex; flex-direction:column; }
.sidebar-section { padding:20px 20px 12px; border-bottom:1px solid var(--border); }
.sidebar-section h3 { font-size:10.5px; font-weight:700; letter-spacing:.1em;
                      text-transform:uppercase; color:var(--muted); margin-bottom:12px; }

/* Query input */
.query-area textarea {
  width:100%; resize:none; height:80px;
  border:1px solid var(--border); border-radius:8px;
  background:var(--bg); color:var(--text);
  font-family:'Inter',sans-serif; font-size:13px; padding:10px 12px;
  line-height:1.5; transition:border-color .2s;
}
.query-area textarea:focus { outline:none; border-color:var(--accent); }
.query-area textarea::placeholder { color:var(--muted); }
.btn { display:block; width:100%; margin-top:8px;
       padding:9px 16px; border-radius:7px; border:none; cursor:pointer;
       font-family:'Inter',sans-serif; font-size:13px; font-weight:600;
       transition:opacity .15s; }
.btn:hover { opacity:.88; }
.btn-primary { background:var(--accent); color:#fff; }
.btn-secondary { background:var(--border); color:var(--muted); margin-top:6px; }

/* Direct metric controls */
select { width:100%; padding:8px 10px; margin-bottom:8px;
         border:1px solid var(--border); border-radius:7px;
         background:var(--bg); color:var(--text);
         font-family:'Inter',sans-serif; font-size:13px; cursor:pointer; }
select:focus { outline:none; border-color:var(--accent); }

/* Suggested questions */
.suggestion {
  display:block; width:100%; text-align:left; padding:8px 10px;
  margin-bottom:6px; border:1px solid var(--border); border-radius:7px;
  background:var(--bg); color:var(--text); font-size:12px; cursor:pointer;
  transition:border-color .15s, background .15s;
}
.suggestion:hover { border-color:var(--accent); background:var(--surface); }

/* Identity resolution panel */
.resolution-box { margin:0 0 16px; padding:12px 14px;
  background:var(--mono-bg); border-radius:8px;
  font-family:'DM Mono',monospace; font-size:10px;
  color:var(--mono-hl); display:none; }
.resolution-box.visible { display:block; }

.res-section-hdr { font-size:9px; letter-spacing:.09em; text-transform:uppercase;
                   font-weight:700; margin-bottom:6px; }
.res-section-hdr-data { color:var(--good); }
.res-section-hdr-id   { color:var(--muted); }

.res-item { display:flex; align-items:center; gap:8px; margin-bottom:4px; flex-wrap:wrap; }
.res-item:last-child { margin-bottom:0; }
.res-sys-label { color:var(--text); font-size:10px; font-weight:600;
                 min-width:148px; font-family:'DM Mono',monospace; }
.res-purpose { color:var(--muted); font-size:9px; font-style:italic; }

.res-row { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
.res-chip { background:var(--chip-bg); color:var(--mono-hl); padding:2px 8px;
            border-radius:4px; font-size:9.5px; }
.res-chip-data { border:1.5px solid var(--good); background:var(--chip-bg); }
.res-chip-id   { opacity:.65; }
.res-sys { color:var(--muted); font-size:9px; }
.res-arrow { color:var(--accent); }
.res-divider { border:none; border-top:1px solid var(--border); margin:8px 0; }

/* Main content */
.main { overflow-y:auto; padding:28px 32px; }
.main-placeholder { display:flex; flex-direction:column; align-items:center;
                    justify-content:center; height:100%; color:var(--muted);
                    text-align:center; }
.main-placeholder svg { opacity:.25; margin-bottom:16px; }
.main-placeholder p { font-size:13px; }

/* Answer panel */
.answer-card { background:var(--surface); border:1px solid var(--border);
               border-radius:12px; padding:20px 24px; margin-bottom:24px;
               border-left:3px solid var(--accent); }
.answer-card .answer-label { font-size:10.5px; font-weight:700; letter-spacing:.08em;
  text-transform:uppercase; color:var(--accent); margin-bottom:8px; }
.answer-card p { font-size:14px; line-height:1.65; color:var(--text); }

/* Chart card */
.chart-card { background:var(--surface); border:1px solid var(--border);
              border-radius:12px; padding:24px; margin-bottom:20px; }
.chart-title { font-size:14px; font-weight:700; color:var(--navy);
               margin-bottom:2px; }
.chart-subtitle { font-size:11px; color:var(--muted); margin-bottom:18px;
                  font-family:'DM Mono',monospace; }
.chart-wrap { position:relative; height:280px; }
.chart-wrap.hbar { height:220px; }
.chart-wrap.radar { height:300px; }

/* KPI satisfaction grid */
.sat-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; }
.sat-cell { background:var(--bg); border:1px solid var(--border); border-radius:8px;
            padding:16px; text-align:center; }
.sat-cell .sat-val { font-size:28px; font-weight:700;
                     font-variant-numeric:tabular-nums; color:var(--navy); }
.sat-cell .sat-label { font-size:11px; color:var(--muted); margin-top:4px; }

/* Step indicator */
.step-tag { display:inline-flex; align-items:center; gap:6px;
            font-family:'DM Mono',monospace; font-size:10px;
            color:var(--mono-hl); background:var(--mono-bg);
            padding:3px 10px; border-radius:20px; margin-bottom:14px; }

/* Loading */
.spinner { display:inline-block; width:16px; height:16px; border:2px solid var(--border);
           border-top-color:var(--accent); border-radius:50%; animation:spin .7s linear infinite; }
@keyframes spin { to { transform:rotate(360deg); } }
.loading-row { display:flex; align-items:center; gap:10px; color:var(--muted);
               font-size:13px; padding:20px; }

@media(max-width:768px) {
  .layout { grid-template-columns:1fr; height:auto; }
  .main { padding:20px 18px; }
}
</style>
</head>
<body>

<header>
  <div class="eyebrow">Context Engineering &mdash; Example 14</div>
  <h1>Hospitality Group — Operations Dashboard</h1>
  <p>5 source systems &middot; 4 site ID formats &middot; OWL identity resolution &middot; Live LLM agent</p>
</header>

<div class="layout">

  <!-- Sidebar -->
  <aside class="sidebar">

    <!-- Ask the agent -->
    <div class="sidebar-section">
      <h3>Ask the Agent</h3>
      <div class="query-area">
        <textarea id="questionInput" placeholder="e.g. What is the labour cost per cover at SITE-LDN-01?"></textarea>
        <button class="btn btn-primary" onclick="askAgent()">&#9658; Ask qwen2.5</button>
        <button class="btn btn-secondary" onclick="clearResults()">Clear</button>
      </div>
    </div>

    <!-- Direct metric -->
    <div class="sidebar-section">
      <h3>Direct Metric Query</h3>
      <select id="metricSelect">
        <option value="">— choose metric —</option>
      </select>
      <select id="siteSelect">
        <option value="">— choose site —</option>
      </select>
      <button class="btn btn-primary" onclick="runMetric()" style="background:#2E9E5B;">&#9654; Run Metric</button>
    </div>

    <!-- Suggestions -->
    <div class="sidebar-section">
      <h3>Suggested Questions</h3>
      <button class="suggestion" onclick="setQ(this.textContent)">What is the labour cost per cover at SITE-LDN-01?</button>
      <button class="suggestion" onclick="setQ(this.textContent)">Which site has the highest EPOS revenue?</button>
      <button class="suggestion" onclick="setQ(this.textContent)">What are the food margins at SITE-LDN-02?</button>
      <button class="suggestion" onclick="setQ(this.textContent)">What is the SAP revenue per cover at SITE-MAN-01?</button>
      <button class="suggestion" onclick="setQ(this.textContent)">What is the headcount breakdown at SITE-LDN-02?</button>
      <button class="suggestion" onclick="setQ(this.textContent)">Give me a full operational summary for SITE-MAN-01.</button>
    </div>

  </aside>

  <!-- Main panel -->
  <main class="main" id="mainPanel">
    <div class="main-placeholder" id="placeholder">
      <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
        <rect x="8" y="8" width="20" height="48" rx="3" fill="currentColor"/>
        <rect x="34" y="20" width="22" height="36" rx="3" fill="currentColor"/>
        <rect x="8" y="54" width="48" height="2" rx="1" fill="currentColor"/>
      </svg>
      <p>Ask the agent a question or run a metric directly.<br>Charts will render here from live query results.</p>
    </div>
    <div id="results" style="display:none;"></div>
  </main>

</div>

<script>
const API = '';  // same origin

// Load selects on startup
async function init() {
  const [sites, metrics] = await Promise.all([
    fetch(API + '/api/sites').then(r => r.json()),
    fetch(API + '/api/metrics').then(r => r.json()),
  ]);
  const ss = document.getElementById('siteSelect');
  sites.forEach(s => {
    const o = document.createElement('option');
    o.value = s.id; o.textContent = s.name;
    ss.appendChild(o);
  });
  const ms = document.getElementById('metricSelect');
  metrics.forEach(m => {
    const o = document.createElement('option');
    o.value = m.name;
    o.textContent = m.name.replace(/_/g,' ') + '  [' + m.systems.join(', ') + ']';
    ms.appendChild(o);
  });
}

function setQ(text) {
  document.getElementById('questionInput').value = text;
}

function showLoading(msg) {
  document.getElementById('placeholder').style.display = 'none';
  const r = document.getElementById('results');
  r.style.display = 'block';
  r.innerHTML = `<div class="loading-row"><span class="spinner"></span>${msg}</div>`;
}

function clearResults() {
  document.getElementById('results').style.display = 'none';
  document.getElementById('results').innerHTML = '';
  document.getElementById('placeholder').style.display = 'flex';
}

// ── Ask agent ─────────────────────────────────────────────────────────────────
async function askAgent() {
  const q = document.getElementById('questionInput').value.trim();
  if (!q) {
    const ta = document.getElementById('questionInput');
    ta.style.borderColor = 'var(--bad)';
    setTimeout(() => ta.style.borderColor = '', 1200);
    return;
  }
  showLoading('Sending to qwen2.5 agent…');

  const resp = await fetch(API + '/api/ask', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({question: q}),
  });
  if (!resp.ok) {
    const err = await resp.text();
    document.getElementById('results').innerHTML =
      `<div class="answer-card"><div class="answer-label">Error</div><p>${err}</p></div>`;
    return;
  }
  const data = await resp.json();
  renderAgentResult(data);
}

function renderAgentResult(data) {
  const r = document.getElementById('results');
  let html = '';

  if (data.answer) {
    html += `<div class="answer-card">
      <div class="answer-label">&#9654; Agent Answer</div>
      <p>${escHtml(data.answer)}</p>
    </div>`;
  }

  (data.steps || []).forEach((step, i) => {
    html += renderStep(step, i + 1);
  });

  r.innerHTML = html;
  (data.steps || []).forEach((step, i) => {
    if (step.chart && Object.keys(step.chart).length) {
      drawChart(`chart-${i}`, step.chart);
    }
  });
}

// ── Source-system map — what each tool actually queries vs. identity-only ────
const TOOL_SOURCES = {
  get_labour_cost_per_cover: {
    data: [
      { sys: 'EPOS — Oracle MICROS',  key: 'epos_site_id',    purpose: 'cover count by meal period' },
      { sys: 'Infor WFM',             key: 'infor_site_code', purpose: 'shift labour cost (£)' },
    ],
    idOnly: [
      { sys: 'SAP S/4HANA',          key: 'sap_cost_center' },
      { sys: 'SAP SuccessFactors',    key: 'sf_org_unit_id'  },
    ],
  },
  get_revenue_by_category: {
    data: [
      { sys: 'EPOS — Oracle MICROS',  key: 'epos_site_id', purpose: 'revenue by product category' },
    ],
    idOnly: [
      { sys: 'Infor WFM',            key: 'infor_site_code' },
      { sys: 'SAP S/4HANA',          key: 'sap_cost_center' },
      { sys: 'SAP SuccessFactors',   key: 'sf_org_unit_id'  },
    ],
  },
  get_food_margin_by_product: {
    data: [
      { sys: 'EPOS — Oracle MICROS',  key: 'epos_site_id', purpose: 'selling price per item' },
      { sys: 'Coupa Procurement',     key: null,           purpose: 'contracted cost (national catalogue)' },
    ],
    idOnly: [
      { sys: 'Infor WFM',            key: 'infor_site_code' },
      { sys: 'SAP S/4HANA',          key: 'sap_cost_center' },
      { sys: 'SAP SuccessFactors',   key: 'sf_org_unit_id'  },
    ],
  },
  get_revenue_per_cover: {
    data: [
      { sys: 'SAP S/4HANA',          key: 'sap_cost_center', purpose: 'client invoices / net revenue per cover' },
    ],
    idOnly: [
      { sys: 'EPOS — Oracle MICROS', key: 'epos_site_id'    },
      { sys: 'Infor WFM',            key: 'infor_site_code' },
      { sys: 'SAP SuccessFactors',   key: 'sf_org_unit_id'  },
    ],
  },
  get_headcount_by_contract: {
    data: [
      { sys: 'SAP SuccessFactors',   key: 'sf_org_unit_id', purpose: 'headcount & FTE by contract type' },
    ],
    idOnly: [
      { sys: 'EPOS — Oracle MICROS', key: 'epos_site_id'    },
      { sys: 'Infor WFM',            key: 'infor_site_code' },
      { sys: 'SAP S/4HANA',          key: 'sap_cost_center' },
    ],
  },
};

function renderResolution(res, toolOrMetric) {
  const src = TOOL_SOURCES[toolOrMetric] || TOOL_SOURCES['get_' + toolOrMetric];
  const idMap = {
    epos_site_id:    res.epos_site_id    || '—',
    infor_site_code: res.infor_site_code || '—',
    sap_cost_center: res.sap_cost_center || '—',
    sf_org_unit_id:  res.sf_org_unit_id  || '—',
  };

  if (!src) {
    return `<div class="resolution-box visible">
      <div class="res-row">
        <span class="res-sys">EPOS</span><span class="res-chip">${idMap.epos_site_id}</span>
        <span class="res-arrow">→</span>
        <span class="res-sys">Infor WFM</span><span class="res-chip">${idMap.infor_site_code}</span>
        <span class="res-arrow">·</span>
        <span class="res-sys">SAP</span><span class="res-chip">${idMap.sap_cost_center}</span>
        <span class="res-arrow">·</span>
        <span class="res-sys">SF</span><span class="res-chip">${idMap.sf_org_unit_id}</span>
      </div></div>`;
  }

  const dataRows = src.data.map(d => `
    <div class="res-item">
      <span class="res-sys-label">${d.sys}</span>
      <span class="res-chip res-chip-data">${d.key ? idMap[d.key] : 'no site_id'}</span>
      <span class="res-purpose">${d.purpose}</span>
    </div>`).join('');

  const idOnlyChips = src.idOnly.map(d =>
    `<span class="res-sys">${d.sys}</span><span class="res-chip res-chip-id">${idMap[d.key]}</span>`
  ).join('<span class="res-arrow"> · </span>');

  return `<div class="resolution-box visible">
    <div class="res-section-hdr res-section-hdr-data">&#9654; Queried for data</div>
    ${dataRows}
    <hr class="res-divider">
    <div class="res-section-hdr res-section-hdr-id">&#9632; Identity resolved via SPARQL &mdash; not queried for this metric</div>
    <div class="res-row">${idOnlyChips}</div>
  </div>`;
}

function renderStep(step, n) {
  const res   = step.resolution || {};
  const chart = step.chart || {};
  const hasChart = chart.type;

  let chartHtml = '';
  if (hasChart) {
    const wrapClass = chart.type === 'horizontalBar' ? 'hbar' : '';
    chartHtml = `<div class="chart-wrap ${wrapClass}"><canvas id="chart-${n-1}"></canvas></div>`;
  }

  return `<div class="chart-card">
    <div class="step-tag">Tool ${n} &mdash; ${step.tool}</div>
    ${renderResolution(res, step.tool)}
    <div class="chart-title">${chart.title || step.tool}</div>
    <div class="chart-subtitle">${chart.subtitle || ''}</div>
    ${chartHtml}
  </div>`;
}

// ── Direct metric ─────────────────────────────────────────────────────────────
async function runMetric() {
  const metric = document.getElementById('metricSelect').value;
  const site   = document.getElementById('siteSelect').value;
  if (!metric || !site) { alert('Select a metric and a site.'); return; }

  showLoading('Running metric…');
  const resp = await fetch(API + '/api/metric', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({metric, site}),
  });
  if (!resp.ok) {
    document.getElementById('results').innerHTML =
      `<div class="answer-card"><div class="answer-label">Error</div><p>${await resp.text()}</p></div>`;
    return;
  }
  const data = await resp.json();
  renderDirectResult(data);
}

function renderDirectResult(data) {
  const chart = data.chart || {};
  const res   = data.resolution || {};
  const hasChart = chart.type;

  const wrapClass = chart.type === 'horizontalBar' ? 'hbar' :
                    chart.type === 'radar' ? 'radar' : '';

  let chartHtml = '';
  if (hasChart) {
    chartHtml = `<div class="chart-wrap ${wrapClass}"><canvas id="direct-chart"></canvas></div>`;
  }

  const r = document.getElementById('results');
  r.innerHTML = `<div class="chart-card">
    ${renderResolution(res, 'get_' + data.metric)}
    <div class="chart-title">${chart.title || data.metric}</div>
    <div class="chart-subtitle">${chart.subtitle || ''}</div>
    ${chartHtml}
  </div>`;

  if (hasChart && chart.type !== 'radar') {
    drawChart('direct-chart', chart);
  }
}

// ── Chart.js renderer ─────────────────────────────────────────────────────────
function drawChart(canvasId, cfg) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  const isHBar = cfg.type === 'horizontalBar';
  const type   = isHBar ? 'bar' : cfg.type;

  const plugins = [];
  const annotations = {};

  if (cfg.threshold) {
    annotations.thresholdLine = {
      type: 'line',
      ...(isHBar
        ? {xMin: cfg.threshold.value, xMax: cfg.threshold.value}
        : {yMin: cfg.threshold.value, yMax: cfg.threshold.value}),
      borderColor: '#E74C3C',
      borderWidth: 1.5,
      borderDash: [6, 4],
      label: {
        display: true,
        content: cfg.threshold.label,
        position: 'end',
        color: '#E74C3C',
        font: {size: 10},
        backgroundColor: 'rgba(231,76,60,.1)',
      },
    };
  }

  new Chart(ctx, {
    type,
    data: {
      labels:   cfg.labels,
      datasets: cfg.datasets,
    },
    options: {
      indexAxis: isHBar ? 'y' : 'x',
      responsive:          true,
      maintainAspectRatio: false,
      plugins: {
        legend:  {display: cfg.datasets?.length > 1,
                  labels: {font: {size: 11}, color: getComputedStyle(document.body).getPropertyValue('--text').trim() || '#1C2B45'}},
        tooltip: {callbacks: {
          label: ctx => {
            const v = ctx.parsed[isHBar ? 'x' : 'y'];
            const lbl = cfg.yLabel || cfg.xLabel || '';
            if (lbl.includes('%')) return `${v.toFixed(1)}%`;
            if (lbl.includes('£'))  return `£${v.toFixed(2)}`;
            return v;
          }
        }},
      },
      scales: {
        x: {
          grid:   {color: '#E1E8F420'},
          ticks:  {font: {size: 11}, color: '#617292'},
          title:  {display: !!cfg.xLabel, text: cfg.xLabel, font: {size: 11}, color: '#617292'},
        },
        y: {
          grid:   {color: '#E1E8F420'},
          ticks:  {font: {size: 11}, color: '#617292'},
          title:  {display: !!cfg.yLabel, text: cfg.yLabel, font: {size: 11}, color: '#617292'},
          beginAtZero: true,
        },
      },
    },
  });
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
          .replace(/\n/g,'<br>');
}

// Kick off
init();

// Enter to submit
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('questionInput').addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); askAgent(); }
  });
});
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    return HTMLResponse(content=DASHBOARD_HTML)


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Validate prerequisites
    import duckdb
    from pathlib import Path
    db_path  = Path(__file__).parent / "hospitality.duckdb"
    ttl_path = Path(__file__).parent.parent / "ontology" / "hospitality_ontology.ttl"
    if not db_path.exists():
        print("ERROR: hospitality.duckdb not found — run bootstrap_hospitality.py first.")
        sys.exit(1)
    if not ttl_path.exists():
        print("ERROR: ontology TTL not found — run generate_ontology.py first.")
        sys.exit(1)

    log.info("Starting Hospitality Dashboard — port=%d  model=%s  db=%s  ttl=%s",
             PORT, MODEL, db_path, ttl_path)
    print(f"Starting Hospitality Dashboard on http://localhost:{PORT}")
    print("  LLM backend : Ollama qwen2.5")
    print("  Data        : 5 source systems, identity resolved via OWL SPARQL")
    print()
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")
