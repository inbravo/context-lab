"""
metric_layer.py — Cross-system metric execution using the ontology as the
identity resolution layer.

Modelled on the real Compass Group data landscape (AWS-shared):

  Source system    Vendor             Site ID in DB       Resolved via
  ───────────────  ─────────────────  ──────────────────  ──────────────────
  EPOS             Oracle MICROS      SITE-LDN-01         (caller always passes this)
  WFM              Infor WFM          GBR_SITE_0001       hosp:inforSiteCode
  Procurement      Coupa (3rd-party)  (no site_id)        product bridge only
  SAP Sales        SAP S/4HANA        CC-GBR-001          hosp:sapCostCenter
  HR & Payroll     SuccessFactors     OU-GBR-001          hosp:sfOrgUnitId

One SPARQL call resolves ALL system IDs from a single EPOS site_id.
DuckDB then queries each system using its own ID format — no JOIN would
otherwise work across these vendor systems.

This is what AWS COA's Virtual Knowledge Graph (Ontop / SPARQL endpoint on
Amazon Neptune) does at scale. Here the SPARQL is explicit Python.

Available metrics:
  labour_cost_per_cover    — Infor WFM + Oracle MICROS EPOS
  revenue_by_category      — EPOS only
  food_margin_by_product   — EPOS + Coupa Procurement (product ID bridge)
  revenue_per_cover        — SAP S/4HANA Sales (cost-centre → EPOS bridge)
  headcount_by_contract    — SAP SuccessFactors HR (org-unit → EPOS bridge)

Usage:
    python metric_layer.py
    python metric_layer.py labour_cost_per_cover SITE-LDN-01
    python metric_layer.py revenue_per_cover SITE-MAN-01
    python metric_layer.py headcount_by_contract SITE-LDN-02
"""
# ─────────────────────────────────────────────────────
# Author   : Amit Dixit
# GitHub   : https://github.com/inbravo
# Web      : https://inbravo.github.io
# LinkedIn : https://www.linkedin.com/in/inbravo/
# ─────────────────────────────────────────────────────

import sys
import logging
import duckdb
from pathlib import Path
from rdflib import Graph, Namespace

import logging_config
logging_config.setup()
log = logging.getLogger("hosp.metric")

DB_FILE  = Path(__file__).parent / "hospitality.duckdb"
TTL_FILE = Path(__file__).parent.parent / "ontology" / "hospitality_ontology.ttl"

HOSP = Namespace("http://hospitality.example.org/ontology#")

_graph: Graph | None = None


def _ontology() -> Graph:
    global _graph
    if _graph is None:
        if not TTL_FILE.exists():
            raise FileNotFoundError(
                f"Ontology not found at {TTL_FILE} — run generate_ontology.py first."
            )
        log.debug("Loading ontology from %s", TTL_FILE)
        _graph = Graph()
        _graph.parse(str(TTL_FILE), format="turtle")
        log.info("Ontology loaded — %d triples from %s", len(_graph), TTL_FILE.name)
    return _graph


# ── Identity resolver ─────────────────────────────────────────────────────────

def resolve_site(epos_site_id: str) -> dict:
    """
    Given an EPOS (Oracle MICROS) site_id, return all four source-system IDs.

    One SPARQL call resolves: Infor WFM code, SAP cost centre, SF org unit.
    This is what COA's VKG does for every cross-system query at Compass scale.
    """
    q = """
    PREFIX hosp: <http://hospitality.example.org/ontology#>
    SELECT ?epos_id ?infor_code ?sap_cc ?sf_org ?site_name WHERE {
        ?site hosp:eposSiteId    ?epos_id ;
              hosp:inforSiteCode ?infor_code ;
              hosp:sapCostCenter ?sap_cc ;
              hosp:sfOrgUnitId   ?sf_org ;
              hosp:siteName      ?site_name .
        FILTER(?epos_id = "%s")
    }
    """ % epos_site_id
    log.debug("resolve_site: epos_site_id=%s", epos_site_id)
    rows = list(_ontology().query(q))
    if not rows:
        log.warning("resolve_site: no ontology match for epos_site_id=%s", epos_site_id)
        raise ValueError(
            f"Site '{epos_site_id}' not found in ontology. "
            "Valid EPOS site IDs: SITE-LDN-01, SITE-LDN-02, SITE-MAN-01"
        )
    row = rows[0]
    result = {
        "epos_site_id":    str(row.epos_id),
        "infor_site_code": str(row.infor_code),
        "sap_cost_center": str(row.sap_cc),
        "sf_org_unit_id":  str(row.sf_org),
        "site_name":       str(row.site_name),
    }
    log.info(
        "resolve_site: %s → infor=%s  sap=%s  sf=%s  (%s)",
        result["epos_site_id"], result["infor_site_code"],
        result["sap_cost_center"], result["sf_org_unit_id"], result["site_name"],
    )
    return result


def resolve_product(epos_item_id: str) -> dict | None:
    """Given an EPOS item code, return the Coupa procurement details."""
    q = """
    PREFIX hosp: <http://hospitality.example.org/ontology#>
    SELECT ?epos_id ?proc_id ?name ?contracted_price WHERE {
        ?prod hosp:eposItemId         ?epos_id ;
              hosp:procProductId      ?proc_id ;
              hosp:productName        ?name ;
              hosp:contractedPriceGBP ?contracted_price .
        FILTER(?epos_id = "%s")
    }
    """ % epos_item_id
    log.debug("resolve_product: epos_item_id=%s", epos_item_id)
    rows = list(_ontology().query(q))
    if not rows:
        log.debug("resolve_product: no bridge for epos_item_id=%s", epos_item_id)
        return None
    row = rows[0]
    log.debug("resolve_product: %s → proc_id=%s", epos_item_id, row.proc_id)
    return {
        "epos_item_id":     str(row.epos_id),
        "proc_product_id":  str(row.proc_id),
        "product_name":     str(row.name),
        "contracted_price": float(str(row.contracted_price)),
    }


# ── Metrics ───────────────────────────────────────────────────────────────────

def labour_cost_per_cover(epos_site_id: str) -> list[dict]:
    """
    Labour cost per cover by meal period.
    Joins Infor WFM shift costs (infor_site_code) with EPOS transaction
    counts (epos_site_id) — two different site ID formats, resolved via SPARQL.
    """
    log.info("metric=labour_cost_per_cover  site=%s", epos_site_id)
    site = resolve_site(epos_site_id)
    db   = duckdb.connect(str(DB_FILE), read_only=True)

    total_labour = db.execute(
        "SELECT SUM(labour_cost_gbp) FROM wfm_shifts WHERE site_id = ?",
        [site["infor_site_code"]]
    ).fetchone()[0] or 0.0
    log.debug("WFM labour total: infor_site_code=%s  total_labour_gbp=%.2f", site["infor_site_code"], total_labour)

    covers_by_period = db.execute("""
        SELECT meal_period, COUNT(*) AS covers, SUM(total_gbp) AS epos_revenue
        FROM epos_transactions WHERE site_id = ?
        GROUP BY meal_period ORDER BY meal_period
    """, [site["epos_site_id"]]).fetchall()
    log.debug("EPOS covers by period: epos_site_id=%s  periods=%d", site["epos_site_id"], len(covers_by_period))
    db.close()

    return [
        {
            "site":                  site["site_name"],
            "epos_site_id":          site["epos_site_id"],
            "infor_site_code":       site["infor_site_code"],
            "meal_period":           period,
            "covers":                covers,
            "epos_revenue_gbp":      round(float(rev), 2),
            "total_labour_gbp":      round(float(total_labour), 2),
            "labour_cost_per_cover": round(float(total_labour) / covers, 2) if covers else 0.0,
        }
        for period, covers, rev in covers_by_period
    ]


def revenue_by_category(epos_site_id: str) -> list[dict]:
    """EPOS revenue grouped by product category (Oracle MICROS)."""
    log.info("metric=revenue_by_category  site=%s", epos_site_id)
    site = resolve_site(epos_site_id)
    db   = duckdb.connect(str(DB_FILE), read_only=True)
    rows = db.execute("""
        SELECT category, COUNT(*) AS transactions, SUM(total_gbp) AS revenue
        FROM epos_transactions WHERE site_id = ?
        GROUP BY category ORDER BY revenue DESC
    """, [site["epos_site_id"]]).fetchall()
    log.debug("EPOS category rows: %d", len(rows))
    db.close()
    return [
        {"site": site["site_name"], "category": r[0],
         "transactions": r[1], "revenue_gbp": round(float(r[2]), 2)}
        for r in rows
    ]


def food_margin_by_product(epos_site_id: str) -> list[dict]:
    """
    EPOS selling price vs Coupa contracted cost.
    Product identity bridge (EPOS-LATTE ↔ PROD-BEV-001) resolved via SPARQL.
    """
    log.info("metric=food_margin_by_product  site=%s", epos_site_id)
    site = resolve_site(epos_site_id)
    db   = duckdb.connect(str(DB_FILE), read_only=True)
    rows = db.execute("""
        SELECT epos_item_id, item_name, AVG(unit_price_gbp) AS avg_sell, COUNT(*) AS units
        FROM epos_transactions WHERE site_id = ?
        GROUP BY epos_item_id, item_name
    """, [site["epos_site_id"]]).fetchall()
    log.debug("EPOS products for margin: %d distinct items", len(rows))
    db.close()

    results = []
    for epos_item_id, item_name, avg_sell, units in rows:
        prod = resolve_product(epos_item_id)
        if prod:
            margin = round(float(avg_sell) - prod["contracted_price"], 2)
            results.append({
                "site":             site["site_name"],
                "epos_item_id":     epos_item_id,
                "proc_product_id":  prod["proc_product_id"],
                "product_name":     item_name,
                "avg_sell_price":   round(float(avg_sell), 2),
                "contracted_cost":  prod["contracted_price"],
                "gross_margin_gbp": margin,
                "units_sold":       int(units),
            })
    results.sort(key=lambda r: r["gross_margin_gbp"], reverse=True)
    log.debug("food_margin_by_product: %d products bridged to Coupa", len(results))
    return results


def revenue_per_cover(epos_site_id: str) -> list[dict]:
    """
    SAP-invoiced net revenue per cover billed, by meal period.
    SAP uses cost_center_code (CC-GBR-001) — resolved from EPOS site_id via SPARQL.
    This cross-system query would silently return 0 rows without the ontology.
    """
    log.info("metric=revenue_per_cover  site=%s", epos_site_id)
    site = resolve_site(epos_site_id)
    log.debug("SAP query: cost_center_code=%s", site["sap_cost_center"])
    db   = duckdb.connect(str(DB_FILE), read_only=True)
    rows = db.execute("""
        SELECT meal_period,
               COUNT(DISTINCT client_code)      AS clients,
               SUM(covers_billed)               AS covers,
               ROUND(SUM(net_amount_gbp), 2)    AS net_revenue,
               ROUND(SUM(net_amount_gbp)
                     / NULLIF(SUM(covers_billed), 0), 2) AS revenue_per_cover
        FROM sap_sales WHERE cost_center_code = ?
        GROUP BY meal_period ORDER BY meal_period
    """, [site["sap_cost_center"]]).fetchall()
    log.debug("SAP revenue_per_cover rows: %d", len(rows))
    db.close()
    return [
        {
            "site":             site["site_name"],
            "sap_cost_center":  site["sap_cost_center"],
            "meal_period":      r[0],
            "clients":          int(r[1]),
            "covers_billed":    int(r[2]),
            "net_revenue_gbp":  float(r[3]),
            "revenue_per_cover": float(r[4]) if r[4] else 0.0,
        }
        for r in rows
    ]


def headcount_by_contract(epos_site_id: str) -> list[dict]:
    """
    SuccessFactors headcount breakdown by contract type.
    SF uses org_unit_id (OU-GBR-001) — resolved from EPOS site_id via SPARQL.
    Returns FTE count and headcount per contract type.
    """
    log.info("metric=headcount_by_contract  site=%s", epos_site_id)
    site = resolve_site(epos_site_id)
    log.debug("SF query: org_unit_id=%s", site["sf_org_unit_id"])
    db   = duckdb.connect(str(DB_FILE), read_only=True)
    rows = db.execute("""
        SELECT contract_type,
               COUNT(*)              AS headcount,
               ROUND(SUM(fte), 2)   AS total_fte,
               ROUND(AVG(annual_salary_gbp), 0) AS avg_salary
        FROM hr_employees WHERE org_unit_id = ?
        GROUP BY contract_type ORDER BY headcount DESC
    """, [site["sf_org_unit_id"]]).fetchall()
    log.debug("SF headcount_by_contract rows: %d contract types", len(rows))
    db.close()
    return [
        {
            "site":           site["site_name"],
            "sf_org_unit_id": site["sf_org_unit_id"],
            "contract_type":  r[0],
            "headcount":      int(r[1]),
            "total_fte":      float(r[2]),
            "avg_salary_gbp": float(r[3]) if r[3] else 0.0,
        }
        for r in rows
    ]


# ── Registry ──────────────────────────────────────────────────────────────────

METRIC_REGISTRY = {
    "labour_cost_per_cover": {
        "fn":          labour_cost_per_cover,
        "description": "Labour cost per cover by meal period. Joins Infor WFM (GBR_SITE_0001) with EPOS (SITE-LDN-01) via ontology SPARQL.",
        "systems":     ["WFM (Infor)", "EPOS (Oracle MICROS)"],
        "arg":         "EPOS site_id  e.g. SITE-LDN-01",
        "chart":       "bar_meal_period",
    },
    "revenue_by_category": {
        "fn":          revenue_by_category,
        "description": "Oracle MICROS EPOS revenue grouped by product category.",
        "systems":     ["EPOS (Oracle MICROS)"],
        "arg":         "EPOS site_id  e.g. SITE-LDN-01",
        "chart":       "bar_category",
    },
    "food_margin_by_product": {
        "fn":          food_margin_by_product,
        "description": "EPOS selling price vs Coupa contracted cost. Product bridge (EPOS-LATTE ↔ PROD-BEV-001) resolved via SPARQL.",
        "systems":     ["EPOS (Oracle MICROS)", "Procurement (Coupa)"],
        "arg":         "EPOS site_id  e.g. SITE-LDN-01",
        "chart":       "hbar_product",
    },
    "revenue_per_cover": {
        "fn":          revenue_per_cover,
        "description": "SAP-invoiced net revenue per cover billed by meal period. SAP uses CC-GBR-001 cost-centre code — resolved from EPOS site_id via SPARQL.",
        "systems":     ["SAP Sales (S/4HANA)"],
        "arg":         "EPOS site_id  e.g. SITE-LDN-01",
        "chart":       "bar_meal_period",
    },
    "headcount_by_contract": {
        "fn":          headcount_by_contract,
        "description": "SuccessFactors headcount and FTE by contract type. SF uses OU-GBR-001 org-unit code — resolved from EPOS site_id via SPARQL.",
        "systems":     ["HR & Payroll (SuccessFactors)"],
        "arg":         "EPOS site_id  e.g. SITE-LDN-01",
        "chart":       "bar_contract",
    },
}


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        print("Available cross-system metrics (ontology-resolved joins):\n")
        for name, meta in METRIC_REGISTRY.items():
            print(f"  {name}")
            print(f"    {meta['description']}")
            print(f"    Systems : {', '.join(meta['systems'])}")
            print(f"    Arg     : {meta['arg']}")
            print()
        sys.exit(0)

    metric_name = args[0]
    site_arg    = args[1] if len(args) > 1 else "SITE-LDN-01"

    if metric_name not in METRIC_REGISTRY:
        print(f"Unknown metric '{metric_name}'. Run with no args to list.")
        sys.exit(1)

    meta = METRIC_REGISTRY[metric_name]
    site = resolve_site(site_arg)

    print(f"\nMetric  : {metric_name}")
    print(f"Site    : {site_arg}")
    print(f"  EPOS (Oracle MICROS) : {site['epos_site_id']}")
    print(f"  WFM  (Infor)         : {site['infor_site_code']}")
    print(f"  SAP  (S/4HANA)       : {site['sap_cost_center']}")
    print(f"  SF   (SuccessFactors): {site['sf_org_unit_id']}")
    print(f"Systems : {', '.join(meta['systems'])}")
    print("─" * 60)

    rows = meta["fn"](site_arg)
    if isinstance(rows, dict):
        for k, v in rows.items():
            print(f"  {k}: {v}")
    else:
        for row in rows:
            print(f"  {row}")
