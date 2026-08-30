"""
metric_layer.py — The Boring Semantic Layer (BSL) translation engine.

Reads a metric YAML file from ../metrics/ and translates it into a
SQL query that Ibis executes against the configured backend.

The agent calls query_metric(name, filters) and gets back rows.
It never writes SQL.  The formula lives in the YAML, not in the agent.

How it works:
    1. Load the metric YAML  (governed definition, reviewed by humans)
    2. Build SQL from the YAML spec  (BSL translation step)
    3. Execute via ibis.Backend.sql()  (backend-agnostic execution)

Swapping backends:
    DuckDB   → ibis.duckdb.connect('delivery.duckdb')   [default]
    Postgres → ibis.postgres.connect(host=..., database=...)
    BigQuery → ibis.bigquery.connect(project=...)

Zero changes to the YAML or the agent are needed to swap backends.
Only the connect() call at the bottom of this file changes.

Usage (standalone):
    python metric_layer.py              # lists available metrics
    python metric_layer.py edd          # runs EDD metric, all rows
    python metric_layer.py edd order_id=48213
    python metric_layer.py order_count customer_id=C002
"""
# ─────────────────────────────────────────────────────
# Author   : Amit Dixit
# GitHub   : https://github.com/inbravo
# Web      : https://inbravo.github.io
# LinkedIn : https://www.linkedin.com/in/inbravo/
# ─────────────────────────────────────────────────────

import sys
import yaml
import ibis
from pathlib import Path
from typing import Any

METRICS_DIR = Path(__file__).parent.parent / "metrics"
DB_FILE     = Path(__file__).parent / "delivery.duckdb"


# ── Metric registry ────────────────────────────────────────────────────────

def _load_metric(name: str) -> dict:
    """Load and parse a metric YAML file by metric name."""
    path = METRICS_DIR / f"{name}.yaml"
    if not path.exists():
        available = [p.stem for p in METRICS_DIR.glob("*.yaml")]
        raise ValueError(
            f"Metric '{name}' not found.  Available: {available}"
        )
    with open(path) as f:
        return yaml.safe_load(f)


def list_metrics() -> list[dict]:
    """Return summary metadata for all available governed metrics."""
    results = []
    for path in sorted(METRICS_DIR.glob("*.yaml")):
        with open(path) as f:
            m = yaml.safe_load(f)
        results.append({
            "metric":      m["metric"],
            "label":       m["label"],
            "description": m.get("description", "").strip(),
            "owner":       m.get("owner", ""),
            "version":     m.get("version", ""),
            "approved_by": m.get("approved_by", ""),
            "dimensions":  [d["name"] for d in m.get("dimensions", [])],
        })
    return results


# ── BSL translation: YAML → SQL ────────────────────────────────────────────

def _build_sql(
    metric:  dict,
    filters: dict[str, Any] | None = None,
) -> str:
    """
    Translate a metric YAML definition into a SQL SELECT statement.

    This is the BSL step — what Boring Semantic Layer does when it reads
    the YAML and produces an executable SQL string for the backend.

    The agent never sees this function.  It calls query_metric() and
    receives rows.  The SQL is derived entirely from the YAML contract.

    Handles three metric shapes:
      1. Select + derived columns  (e.g. EDD — date arithmetic)
      2. Aggregation               (e.g. order_count — COUNT with GROUP BY)
      3. Plain select              (fallback)
    """
    cfg       = metric["computation"]
    base_tbl  = cfg["base_table"]
    agg_cfg   = cfg.get("aggregation")
    derived   = cfg.get("derived_columns", {})
    select    = cfg.get("select", [])

    # ── SELECT clause ──────────────────────────────────────────────────────
    if agg_cfg:
        # Aggregation metric — group by all non-aggregated select columns
        fn      = agg_cfg["function"].upper()
        col     = agg_cfg["column"]
        alias   = agg_cfg.get("alias", f"{fn.lower()}_{col}")
        groups  = [c for c in select if c != col]
        group_cols = ", ".join(groups)
        select_clause = f"{group_cols}, {fn}({col}) AS {alias}"
    else:
        # Select + optional derived columns
        parts = list(select)
        for alias, expr in derived.items():
            # Rewrite arithmetic: "a + b + c" → "CAST(a AS INTEGER) + ..."
            # For date + integers → explicit INTERVAL DAY casting for portability
            terms = [t.strip() for t in expr.split("+")]
            if terms:
                # First term is the date column; rest are integer day offsets
                date_col = terms[0]
                int_cols = terms[1:]
                if int_cols:
                    day_parts = " + ".join(
                        f"CAST({c} AS INTEGER)" for c in int_cols
                    )
                    parts.append(
                        f"({date_col} + INTERVAL (({day_parts}) || ' days')) AS {alias}"
                    )
                else:
                    parts.append(f"{terms[0]} AS {alias}")
        select_clause = ", ".join(parts)

    # ── WHERE clause ───────────────────────────────────────────────────────
    where_parts: list[str] = []

    # Governance filters from the YAML (always enforced)
    for f in cfg.get("filters", []):
        where_parts.append(f)

    # Caller-supplied dimension filters (agent-supplied, validated against dimensions)
    allowed_dims = {d["name"] for d in metric.get("dimensions", [])}
    if filters:
        for col_name, value in filters.items():
            if col_name not in allowed_dims:
                raise ValueError(
                    f"'{col_name}' is not a valid dimension for metric '{metric['metric']}'. "
                    f"Valid dimensions: {sorted(allowed_dims)}"
                )
            if isinstance(value, str):
                where_parts.append(f"{col_name} = '{value}'")
            else:
                where_parts.append(f"{col_name} = {value}")

    where_clause = (
        "WHERE " + "\n  AND ".join(where_parts) if where_parts else ""
    )

    # ── GROUP BY clause (aggregation only) ────────────────────────────────
    group_by_clause = ""
    if agg_cfg and groups:
        group_by_clause = f"GROUP BY {', '.join(groups)}"

    # ── Assemble ───────────────────────────────────────────────────────────
    sql = (
        f"SELECT {select_clause}\n"
        f"FROM   {base_tbl}\n"
        f"{where_clause}\n"
        f"{group_by_clause}"
    ).strip()

    return sql


# ── Public API (what the agent calls) ─────────────────────────────────────

def query_metric(
    name:    str,
    filters: dict[str, Any] | None = None,
    conn:    ibis.BaseBackend | None = None,
) -> list[dict]:
    """
    Execute a governed metric by name and return rows as a list of dicts.

    Parameters
    ----------
    name    : metric identifier — must match a file in ../metrics/
    filters : optional dict of dimension → value  (agent-supplied)
    conn    : Ibis backend connection (defaults to local DuckDB)

    Returns
    -------
    list of row dicts — the agent receives these, not raw SQL results.
    """
    if conn is None:
        conn = ibis.duckdb.connect(str(DB_FILE))

    metric = _load_metric(name)
    sql    = _build_sql(metric, filters)
    return conn.sql(sql).execute().to_dict(orient="records")


def get_metric_sql(
    name:    str,
    filters: dict[str, Any] | None = None,
) -> str:
    """Return the SQL that would be generated for a metric — for audit / transparency."""
    metric = _load_metric(name)
    return _build_sql(metric, filters)


# ── CLI for standalone testing ─────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        metrics = list_metrics()
        print("Available governed metrics:")
        for m in metrics:
            print(f"\n  {m['metric']} — {m['label']}")
            print(f"    {m['description'][:90]}...")
            print(f"    owner={m['owner']}  version={m['version']}  "
                  f"approved_by={m['approved_by']}")
            print(f"    dimensions: {m['dimensions']}")
        sys.exit(0)

    metric_name = args[0]
    filters = {}
    for arg in args[1:]:
        if "=" in arg:
            k, v = arg.split("=", 1)
            filters[k.strip()] = v.strip()

    # Show the generated SQL first (transparency / audit)
    sql = get_metric_sql(metric_name, filters or None)
    print(f"\nMetric   : {metric_name}")
    print(f"Filters  : {filters or 'none'}")
    print(f"\nGenerated SQL (from YAML contract):\n{'─'*50}")
    print(sql)
    print('─' * 50)

    rows = query_metric(metric_name, filters or None)
    print(f"\nResult ({len(rows)} row(s)):")
    for row in rows:
        print(f"  {row}")
