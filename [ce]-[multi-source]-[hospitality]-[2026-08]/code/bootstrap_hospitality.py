"""
bootstrap_hospitality.py — Seed DuckDB with five source systems from a
fictional UK Hospitality Group (B&I catering sector).

Modelled on the real Compass Group data landscape (as shared by AWS):

  System               Vendor            Site ID format       Identity problem
  ───────────────────  ────────────────  ───────────────────  ─────────────────
  EPOS                 Oracle MICROS     SITE-LDN-01          Hyphen + prefix
  WFM                  Infor WFM         GBR_SITE_0001        Country+underscore
  Procurement          3rd-party (Coupa) (no site_id)         National catalogue
  SAP Sales/Orders     SAP S/4HANA       CC-GBR-001           Cost-centre code
  HR & Payroll         SuccessFactors    OU-GBR-001           Org-unit code

  Product ID mismatch (Procurement):
    EPOS item code  : EPOS-LATTE
    Coupa SKU       : PROD-BEV-001

  No system shares a key with another. This is what the ontology resolves.

Run order:
    python bootstrap_hospitality.py     — seed hospitality.duckdb (once)
    python generate_ontology.py         — introspect schemas, build OWL TTL
    python metric_layer.py              — list available cross-system metrics
    python agent_hospitality_ollama.py  — ask cross-system questions
    python dashboard_server.py          — live FastAPI dashboard on :8765

Scale note (real Compass Group):
    Procurement catalogue : ~300,000 products / ~20,000 suppliers per market
    EPOS providers        : up to 40 per market
    This PoC uses a representative subset to keep the demo fast.
"""
# ─────────────────────────────────────────────────────
# Author   : Amit Dixit
# GitHub   : https://github.com/inbravo
# Web      : https://inbravo.github.io
# LinkedIn : https://www.linkedin.com/in/inbravo/
# ─────────────────────────────────────────────────────

import logging
import os
import random
import duckdb
from datetime import date, timedelta

import logging_config
logging_config.setup()
log = logging.getLogger("hosp.bootstrap")

DB_FILE = "hospitality.duckdb"
random.seed(42)

# ── Sites — the common anchor, encoded differently per system ────────────────
#
# In a real Compass deployment, EPOS alone can have up to 40 providers per
# market, each with its own site_id convention. Here we show one provider
# (Oracle MICROS) alongside Infor WFM, SAP, and SuccessFactors formats.
#
SITES = [
    # canonical_id   epos_site_id   infor_site_code  sap_cost_center  sf_org_unit    city
    ("gbr-lnd-01", "SITE-LDN-01", "GBR_SITE_0001",  "CC-GBR-001",   "OU-GBR-001", "London Canary Wharf"),
    ("gbr-lnd-02", "SITE-LDN-02", "GBR_SITE_0002",  "CC-GBR-002",   "OU-GBR-002", "London City"),
    ("gbr-man-01", "SITE-MAN-01", "GBR_SITE_0101",  "CC-GBR-101",   "OU-GBR-101", "Manchester"),
]

# ── EPOS item catalogue (Oracle MICROS format) ────────────────────────────────
EPOS_ITEMS = [
    # epos_item_id    category        item_name                      unit_price_gbp
    ("EPOS-LATTE",   "HOT DRINKS",   "Latte",                       3.20),
    ("EPOS-AMERI",   "HOT DRINKS",   "Americano",                   2.80),
    ("EPOS-TEA",     "HOT DRINKS",   "English Breakfast Tea",       2.40),
    ("EPOS-CCURRY",  "MAINS",        "Chicken Curry & Rice",        6.80),
    ("EPOS-PASTA",   "MAINS",        "Pasta Bolognese",             6.20),
    ("EPOS-VTAG",    "MAINS",        "Vegetable Tagine",            5.90),
    ("EPOS-BLTSD",   "SANDWICHES",   "BLT Sandwich",                4.50),
    ("EPOS-CKWRP",   "SANDWICHES",   "Chicken Tikka Wrap",          4.80),
    ("EPOS-WATER",   "COLD DRINKS",  "Still Water 500ml",           1.50),
    ("EPOS-OJ",      "COLD DRINKS",  "Fresh Orange Juice 330ml",    2.10),
]

# ── WFM roles (Infor WFM — B&I catering grade structure) ─────────────────────
WFM_ROLES = [
    # role                   hourly_rate_gbp
    ("CATERING_MANAGER",     19.50),
    ("HEAD_CHEF",            17.00),
    ("CHEF_DE_PARTIE",       14.50),
    ("COMMIS_CHEF",          12.50),
    ("BARISTA",              12.00),
    ("HOSPITALITY_ASSISTANT", 11.50),
    ("KITCHEN_PORTER",       11.00),
]
MEAL_PERIODS = ["BREAKFAST", "LUNCH", "AFTERNOON"]

# ── SAP clients per site ─────────────────────────────────────────────────────
SAP_CLIENTS = {
    "CC-GBR-001": [("CLIENT-LDN-001", "Alpha Financial Services"),
                   ("CLIENT-LDN-002", "Vertex Technology Campus")],
    "CC-GBR-002": [("CLIENT-LDN-003", "Sterling Banking Group"),
                   ("CLIENT-LDN-004", "Blue Capital Partners")],
    "CC-GBR-101": [("CLIENT-MAN-001", "Northern Rail Group"),
                   ("CLIENT-MAN-002", "Bridgewater NHS Trust")],
}

# ── SuccessFactors role templates ─────────────────────────────────────────────
SF_ROLE_TEMPLATES = [
    # job_title                  department         contract_type   fte   annual_salary
    ("Catering Manager",        "Management",       "PERMANENT",    1.0,  42000),
    ("Deputy Catering Manager", "Management",       "PERMANENT",    1.0,  32000),
    ("Head Chef",               "Back of House",    "PERMANENT",    1.0,  34000),
    ("Chef de Partie",          "Back of House",    "PERMANENT",    1.0,  28000),
    ("Chef de Partie",          "Back of House",    "PART_TIME",    0.5,  14000),
    ("Commis Chef",             "Back of House",    "PERMANENT",    1.0,  24000),
    ("Commis Chef",             "Back of House",    "AGENCY",       1.0,  0),
    ("Barista",                 "Front of House",   "PERMANENT",    1.0,  23500),
    ("Barista",                 "Front of House",   "PART_TIME",    0.5,  11750),
    ("Hospitality Assistant",   "Front of House",   "PERMANENT",    1.0,  22000),
    ("Hospitality Assistant",   "Front of House",   "PART_TIME",    0.5,  11000),
    ("Hospitality Assistant",   "Front of House",   "ZERO_HOURS",   0.0,  0),
    ("Kitchen Porter",          "Back of House",    "PERMANENT",    1.0,  21500),
    ("Kitchen Porter",          "Back of House",    "AGENCY",       1.0,  0),
]


def main() -> None:
    log.info("Bootstrap starting — target DB: %s", DB_FILE)
    if os.path.exists(DB_FILE):
        log.debug("Removing existing DB: %s", DB_FILE)
        os.remove(DB_FILE)

    db = duckdb.connect(DB_FILE)
    start = date(2026, 8, 1)

    log.info("Creating table: epos_transactions (Oracle MICROS)")
    # ── 1. EPOS Transactions (Oracle MICROS — site_id = "SITE-LDN-01") ──────
    db.execute("""
        CREATE TABLE epos_transactions (
            txn_id          VARCHAR PRIMARY KEY,
            site_id         VARCHAR NOT NULL,
            epos_item_id    VARCHAR NOT NULL,
            item_name       VARCHAR NOT NULL,
            category        VARCHAR NOT NULL,
            quantity        INTEGER NOT NULL,
            unit_price_gbp  DECIMAL(8,2) NOT NULL,
            total_gbp       DECIMAL(8,2) NOT NULL,
            meal_period     VARCHAR NOT NULL,
            txn_date        DATE NOT NULL
        )
    """)

    txn_rows = []
    for day_offset in range(30):
        txn_date = start + timedelta(days=day_offset)
        for _, epos_id, _, _, _, _ in SITES:
            for period in MEAL_PERIODS:
                n = random.randint(6, 14)
                for i in range(n):
                    item = random.choice(EPOS_ITEMS)
                    qty  = random.randint(1, 3)
                    tid  = f"TXN-{txn_date.strftime('%Y%m%d')}-{epos_id[-6:]}-{period[:3]}-{i:02d}"
                    txn_rows.append((
                        tid, epos_id, item[0], item[2], item[1],
                        qty, item[3], round(item[3] * qty, 2), period, txn_date
                    ))
    db.executemany("INSERT INTO epos_transactions VALUES (?,?,?,?,?,?,?,?,?,?)", txn_rows)
    log.debug("epos_transactions: %d rows inserted", len(txn_rows))

    log.info("Creating table: wfm_shifts (Infor WFM)")
    # ── 2. WFM Shifts (Infor WFM — site_id = "GBR_SITE_0001") ──────────────
    db.execute("""
        CREATE TABLE wfm_shifts (
            shift_id         VARCHAR PRIMARY KEY,
            site_id          VARCHAR NOT NULL,
            wfm_employee_id  VARCHAR NOT NULL,
            role             VARCHAR NOT NULL,
            shift_date       DATE NOT NULL,
            hours_worked     DECIMAL(4,2) NOT NULL,
            labour_cost_gbp  DECIMAL(8,2) NOT NULL,
            worker_type      VARCHAR NOT NULL
        )
    """)

    shift_rows = []
    emp_counter = 1
    role_rate   = {r[0]: r[1] for r in WFM_ROLES}
    for day_offset in range(30):
        shift_date = start + timedelta(days=day_offset)
        for _, _, infor_id, _, _, _ in SITES:
            for j in range(random.randint(4, 8)):
                role_entry  = random.choice(WFM_ROLES)
                role        = role_entry[0]
                hourly_rate = role_entry[1]
                hours       = round(random.uniform(6.0, 9.5), 2)
                labour_cost = round(hours * hourly_rate * 1.138, 2)  # 13.8% employer NI + pension
                worker_type = ("AGENCY" if role in ("COMMIS_CHEF", "KITCHEN_PORTER")
                               and random.random() < 0.25
                               else "PERMANENT" if random.random() < 0.65
                               else "PART_TIME")
                shift_rows.append((
                    f"SHIFT-{shift_date.strftime('%Y%m%d')}-{infor_id}-{j:02d}",
                    infor_id,
                    f"EMP-WFM-{emp_counter:04d}",
                    role, shift_date, hours, labour_cost, worker_type
                ))
                emp_counter += 1
    db.executemany("INSERT INTO wfm_shifts VALUES (?,?,?,?,?,?,?,?)", shift_rows)
    log.debug("wfm_shifts: %d rows inserted", len(shift_rows))

    log.info("Creating table: procurement_products (Coupa)")
    # ── 3. Procurement Products (Coupa — national catalogue, no site_id) ────
    #
    # Real scale: ~300,000 products, ~20,000 suppliers per market.
    # This PoC shows the representative B&I catering SKUs that bridge to EPOS.
    #
    db.execute("""
        CREATE TABLE procurement_products (
            proc_product_id      VARCHAR PRIMARY KEY,
            epos_item_id         VARCHAR,
            product_name         VARCHAR NOT NULL,
            category             VARCHAR NOT NULL,
            contracted_price_gbp DECIMAL(8,2) NOT NULL,
            supplier_id          VARCHAR NOT NULL,
            supplier_name        VARCHAR NOT NULL,
            supplier_tier        VARCHAR NOT NULL,
            is_approved          BOOLEAN NOT NULL
        )
    """)
    db.executemany("INSERT INTO procurement_products VALUES (?,?,?,?,?,?,?,?,?)", [
        ("PROD-BEV-001",  "EPOS-LATTE",  "Fresh Ground Coffee — Latte (whole bean + milk)",    "HOT DRINKS",  2.10, "SUP-00001", "Costa Coffee UK",              "TIER_1", True),
        ("PROD-BEV-002",  "EPOS-AMERI",  "Fresh Ground Coffee — Americano (whole bean)",       "HOT DRINKS",  1.85, "SUP-00001", "Costa Coffee UK",              "TIER_1", True),
        ("PROD-BEV-003",  "EPOS-TEA",    "Tetley English Breakfast Tea — box 100",             "HOT DRINKS",  0.35, "SUP-00002", "Brakes Food Service",          "TIER_1", True),
        ("PROD-MAIN-001", "EPOS-CCURRY", "Chicken Curry & Basmati Rice — portion",             "MAINS",       3.80, "SUP-00002", "Brakes Food Service",          "TIER_1", True),
        ("PROD-MAIN-002", "EPOS-PASTA",  "Pasta Bolognese — hot counter portion",              "MAINS",       3.50, "SUP-00002", "Brakes Food Service",          "TIER_1", True),
        ("PROD-MAIN-003", "EPOS-VTAG",   "Vegetable Tagine — hot counter portion",             "MAINS",       3.20, "SUP-00002", "Brakes Food Service",          "TIER_1", True),
        ("PROD-SAND-001", "EPOS-BLTSD",  "BLT Sandwich — chilled, pre-packed",                "SANDWICHES",  2.80, "SUP-00002", "Brakes Food Service",          "TIER_1", True),
        ("PROD-SAND-002", "EPOS-CKWRP",  "Chicken Tikka Wrap — chilled, pre-packed",          "SANDWICHES",  2.90, "SUP-00002", "Brakes Food Service",          "TIER_1", True),
        ("PROD-BEV-004",  "EPOS-WATER",  "Coca-Cola Still Water — 500ml",                     "COLD DRINKS", 0.45, "SUP-00003", "Coca-Cola European Partners",  "TIER_1", True),
        ("PROD-BEV-005",  "EPOS-OJ",     "Tropicana Orange Juice — 330ml",                    "COLD DRINKS", 0.85, "SUP-00003", "Coca-Cola European Partners",  "TIER_1", True),
    ])
    log.debug("procurement_products: 10 rows inserted (national catalogue subset)")

    log.info("Creating table: sap_sales (SAP S/4HANA)")
    # ── 4. SAP Sales / Invoicing (SAP S/4HANA — cost_center = "CC-GBR-001") ─
    #
    # SAP generates client invoices — one per client per meal period per day.
    # The SAP cost_center_code is the site identifier in the ERP — entirely
    # different from the EPOS site_id or WFM site_code.
    #
    db.execute("""
        CREATE TABLE sap_sales (
            invoice_id           VARCHAR PRIMARY KEY,
            cost_center_code     VARCHAR NOT NULL,
            client_code          VARCHAR NOT NULL,
            client_name          VARCHAR NOT NULL,
            meal_period          VARCHAR NOT NULL,
            covers_billed        INTEGER NOT NULL,
            net_amount_gbp       DECIMAL(10,2) NOT NULL,
            vat_gbp              DECIMAL(10,2) NOT NULL,
            invoice_date         DATE NOT NULL
        )
    """)

    inv_rows    = []
    inv_counter = 1
    for day_offset in range(30):
        inv_date = start + timedelta(days=day_offset)
        for _, _, _, sap_cc, _, _ in SITES:
            clients = SAP_CLIENTS[sap_cc]
            for client_code, client_name in clients:
                for period in MEAL_PERIODS:
                    covers     = random.randint(18, 120)
                    avg_spend  = random.uniform(7.80, 14.50)
                    net_amount = round(covers * avg_spend, 2)
                    vat        = round(net_amount * 0.20, 2)
                    inv_rows.append((
                        f"INV-{inv_date.strftime('%Y%m%d')}-{sap_cc[-3:]}-{client_code[-3:]}-{period[:3]}-{inv_counter:04d}",
                        sap_cc,
                        client_code,
                        client_name,
                        period,
                        covers,
                        net_amount,
                        vat,
                        inv_date,
                    ))
                    inv_counter += 1
    db.executemany("INSERT INTO sap_sales VALUES (?,?,?,?,?,?,?,?,?)", inv_rows)
    log.debug("sap_sales: %d rows inserted", len(inv_rows))

    log.info("Creating table: hr_employees (SAP SuccessFactors)")
    # ── 5. HR & Payroll (SuccessFactors — org_unit_id = "OU-GBR-001") ────────
    #
    # SuccessFactors stores the employee master record.
    # Crucially: wfm_employee_id links back to WFM (format EMP-WFM-XXXX) but
    # SF uses its own employee_id (format SF-EMP-XXXXX) — another ID mismatch.
    #
    db.execute("""
        CREATE TABLE hr_employees (
            employee_id        VARCHAR PRIMARY KEY,
            org_unit_id        VARCHAR NOT NULL,
            job_title          VARCHAR NOT NULL,
            department         VARCHAR NOT NULL,
            contract_type      VARCHAR NOT NULL,
            fte                DECIMAL(3,2) NOT NULL,
            annual_salary_gbp  DECIMAL(10,2),
            wfm_employee_id    VARCHAR,
            start_date         DATE NOT NULL
        )
    """)

    hr_rows     = []
    sf_counter  = 1
    wfm_hr_link = 1
    hire_base   = date(2022, 1, 1)
    for _, _, _, _, sf_org, _ in SITES:
        for template in SF_ROLE_TEMPLATES:
            job_title, dept, contract_type, fte, salary = template
            n_per_site = (2 if "Manager" in job_title
                          else 3 if "Chef de Partie" in job_title or "Barista" in job_title
                          else 4 if "Hospitality Assistant" in job_title
                          else 2)
            for _ in range(n_per_site):
                salary_val = salary + random.randint(-1500, 1500) if salary > 0 else None
                start_dt   = hire_base + timedelta(days=random.randint(0, 1200))
                hr_rows.append((
                    f"SF-EMP-{sf_counter:05d}",
                    sf_org,
                    job_title,
                    dept,
                    contract_type,
                    fte,
                    round(salary_val, 2) if salary_val else None,
                    f"EMP-WFM-{wfm_hr_link:04d}",
                    start_dt,
                ))
                sf_counter  += 1
                wfm_hr_link += 1

    db.executemany("INSERT INTO hr_employees VALUES (?,?,?,?,?,?,?,?,?)", hr_rows)
    log.debug("hr_employees: %d rows inserted", len(hr_rows))
    db.close()

    # ── Summary ───────────────────────────────────────────────────────────────
    db2 = duckdb.connect(DB_FILE, read_only=True)
    counts = {t: db2.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("epos_transactions","wfm_shifts","procurement_products",
                        "sap_sales","hr_employees")}
    db2.close()
    log.info(
        "Bootstrap complete — epos=%d  wfm=%d  proc=%d  sap=%d  hr=%d  db=%s",
        counts["epos_transactions"], counts["wfm_shifts"],
        counts["procurement_products"], counts["sap_sales"],
        counts["hr_employees"], DB_FILE,
    )

    print(f"Created : {DB_FILE}")
    print()
    print(f"{'Source system':<22} {'Vendor / System':<30} {'Site ID format':<22} {'Rows':>6}")
    print("─" * 86)
    print(f"{'EPOS':<22} {'Oracle MICROS':<30} {'SITE-LDN-01':<22} {counts['epos_transactions']:>6}")
    print(f"{'WFM':<22} {'Infor WFM':<30} {'GBR_SITE_0001':<22} {counts['wfm_shifts']:>6}")
    print(f"{'Procurement':<22} {'Coupa (3rd-party)':<30} {'(no site_id)':<22} {counts['procurement_products']:>6}")
    print(f"{'SAP Sales':<22} {'SAP S/4HANA':<30} {'CC-GBR-001':<22} {counts['sap_sales']:>6}")
    print(f"{'HR & Payroll':<22} {'SAP SuccessFactors':<30} {'OU-GBR-001':<22} {counts['hr_employees']:>6}")
    print()
    print("No system shares a key with another. The ontology resolves this.")
    print("Run generate_ontology.py next.")


if __name__ == "__main__":
    main()
