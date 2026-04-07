# CastNet Database Context for cast-llm

This document provides the connection details, schema definitions, and query patterns needed to connect the cast-llm analysis pipeline directly to CastNet's live databases, replacing the static JSON file approach used in the Hartree POC.

---

## Network & Server Overview

All databases run on or are accessible from the CastNet server (Windows 11 Pro). The cast-llm project runs on the same server.

| Database | Engine | Host | Port | Database Name | Auth |
|----------|--------|------|------|---------------|------|
| CastNet operational data | MongoDB | localhost | 27017 | `castnet` | No auth (local) |
| OEE + ProLink data | PostgreSQL 16 | localhost | 5432 | `castnet_oee` | User: `castnet`, Password: from `.env` |
| Spectrometer (OXSAS) | SQL Server Express | 192.168.54.18 | 1433 | `ANALYSES` | User: `CastNet`, Password: `CastNet400!` |

MongoDB and PostgreSQL run as Docker containers (via Docker Desktop). The OXSAS SQL Server is a separate machine on the factory network. All are reachable from the Windows host at the addresses above.

---

## 1. MongoDB — Shift Reports and Operational Data

### Connection

```python
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["castnet"]
```

No authentication is required for the local MongoDB instance.

### Collection: `reports`

This is the primary data source the Hartree POC used (exported as JSON). Each document is one shift report written by an operator.

**Key fields:**

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | Unique identifier |
| `report` | String | Free-text shift narrative (the main content for LLM analysis) |
| `die` | String | Die name, e.g. "KM RDM Carrier", "Tesla Battery Knuckle" |
| `equipment` | String | Machine name, e.g. "DCM 1", "DCM 3" |
| `department` | String | e.g. "Casting" |
| `shift` | String | e.g. "Days", "Nights" |
| `cavity` | String | Cavity identifier |
| `name` | String | Operator name |
| `date_iso` | Date | Shift date as ISO date |
| `createdAt` | Date | When the report was submitted |

**Example query — replaces loading from JSON file:**

```python
from datetime import datetime

# Equivalent to the Hartree POC's JSON load + filter
reports = list(db["reports"].find(
    {
        "report": {"$regex": "porosity", "$options": "i"},
        "die": {"$regex": "KM RDM Carrier", "$options": "i"},
        "date_iso": {
            "$gte": datetime(2024, 1, 1),
            "$lte": datetime(2025, 12, 31)
        }
    },
    {
        "_id": 0,
        "report": 1,
        "die": 1,
        "equipment": 1,
        "shift": 1,
        "department": 1,
        "cavity": 1,
        "name": 1,
        "date_iso": 1
    }
).sort("date_iso", -1))
```

### Other useful MongoDB collections

| Collection | What it contains | Useful for |
|------------|-----------------|------------|
| `dies` | Die definitions with customer, metal, targets, cycle times | Cross-referencing die names to customers and production targets |
| `die-master` | Tooling configurations (bolster + cavity combos) | Understanding which tooling setup was in use |
| `equipment` | Machine registry (DCM 1 through DCM 16) | Machine metadata |
| `daily-value` | Daily packed/scrap counts per machine per shift | Production output numbers with OEE fields |
| `statusevents` | Machine status events (running, stopped, etc.) from Brainboxes I/O | Uptime/downtime event log |
| `maintenance-requests` | Maintenance work requests | Correlating maintenance actions with production issues |
| `quality-alerts` | Quality alerts raised during production | Quality events and responses |

**Example — get daily value data for a machine and date range:**

```python
daily_values = list(db["daily-value"].find(
    {
        "equipment": "DCM 3",
        "date": {
            "$gte": datetime(2025, 1, 1),
            "$lte": datetime(2025, 3, 31)
        }
    }
))
```

---

## 2. PostgreSQL — OEE and ProLink SPC Data

### Connection

```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="castnet_oee",
    user="castnet",
    password="<from .env file — POSTGRES_PASSWORD>"
)
```

Install with: `pip install psycopg2-binary`

The PostgreSQL database contains two schemas: `public` (OEE data from Odyssey ERP) and `prolink` (SPC process parameter data from Pro-Link software on each DCM).

### Schema: `public` — OEE Data (from Odyssey ERP)

This is production history synced from the Odyssey Progress OpenEdge ERP. It contains one record per machine per shift per day with pre-computed OEE metrics.

#### Table: `dim_machines` (14 rows — one per DCM)

| Column | Type | Description |
|--------|------|-------------|
| `machine_id` | SERIAL PK | Internal ID |
| `machine_name` | VARCHAR | Display name, e.g. "DCM1" |
| `operation_code` | VARCHAR | Odyssey code, e.g. "0402D01" |

**Machine mapping note:** Odyssey code `0402D13` maps to DCM11 (not DCM13). Codes `0402D11` and `0402D14` do not exist.

#### Table: `dim_shifts` (2 rows)

| shift_id | shift_code | shift_name |
|----------|-----------|------------|
| 1 | 1 | Day |
| 2 | 3 | Night |

Day shift = 06:00–18:00. Night shift = 18:00–06:00.

#### Table: `fact_oee_transactions` (main fact table)

One row per machine per shift per day. Key columns:

| Column | Type | Description |
|--------|------|-------------|
| `transaction_id` | SERIAL PK | |
| `machine_id` | INT FK | → dim_machines |
| `shift_id` | INT FK | → dim_shifts |
| `transaction_date` | DATE | Production date |
| `production_qty` | INT | Parts produced (Transcode 33) |
| `scrap_qty` | INT | Parts scrapped (Transcode 34) |
| `available_hours` | FLOAT | Total shift hours worked (Transcode 33) |
| `downtime_hours` | FLOAT | Downtime hours (Transcode 04) |
| `production_hours` | FLOAT | Net running time (available_hours − downtime_hours) |
| `routing_rate` | FLOAT | Standard time per part (hours) |
| `cavities` | INT | Number of impressions (typically 1) |
| `tool` | VARCHAR | Odyssey tool code (maps to bolster) |
| `config` | VARCHAR | Odyssey config code (maps to cavity) |
| `availability` | FLOAT | **Computed column** — production_hours / available_hours |
| `performance` | FLOAT | **Computed column** — can exceed 1.0 (legitimate) |
| `quality` | FLOAT | **Computed column** — good_parts / production_qty |
| `oee` | FLOAT | **Computed column** — availability × performance × quality |

Availability, performance, quality, and OEE are `GENERATED ALWAYS AS STORED` columns — they are computed automatically from the raw metrics and exactly match the existing Crystal Reports formulas.

#### Pre-built views

| View | Description | Use case |
|------|-------------|----------|
| `vw_oee_report` | Shift-level data with machine/shift names joined | Per-shift analysis |
| `vw_oee_daily` | Daily totals (both shifts combined) | Daily summaries |
| `vw_oee_daily_by_machine` | Daily totals per machine | Machine comparison |
| `vw_oee_monthly` | Monthly aggregation | Trend analysis |

**Example query — OEE summary for a machine over a date range:**

```sql
SELECT
    m.machine_name,
    t.transaction_date,
    s.shift_name,
    t.production_qty,
    t.scrap_qty,
    ROUND((t.availability * 100)::numeric, 1) AS availability_pct,
    ROUND((t.performance * 100)::numeric, 1) AS performance_pct,
    ROUND((t.quality * 100)::numeric, 1) AS quality_pct,
    ROUND((t.oee * 100)::numeric, 1) AS oee_pct,
    ROUND(t.downtime_hours::numeric, 2) AS downtime_hrs
FROM fact_oee_transactions t
JOIN dim_machines m ON t.machine_id = m.machine_id
JOIN dim_shifts s ON t.shift_id = s.shift_id
WHERE m.machine_name = 'DCM3'
  AND t.transaction_date BETWEEN '2025-01-01' AND '2025-03-31'
ORDER BY t.transaction_date, s.shift_code;
```

**OEE aggregation rule:** When rolling up across multiple shifts (daily, weekly, monthly totals), always **sum the raw columns first, then compute ratios**. Never average the pre-computed percentages — that gives equal weight to every shift regardless of production volume.

```sql
-- Correct monthly OEE for a machine
SELECT
    m.machine_name,
    DATE_TRUNC('month', t.transaction_date) AS month,
    SUM(t.production_qty) AS total_production,
    SUM(t.scrap_qty) AS total_scrap,
    ROUND((SUM(t.production_hours) / NULLIF(SUM(t.available_hours), 0) * 100)::numeric, 1) AS availability_pct,
    ROUND((SUM(t.time_to_produce_parts) / NULLIF(SUM(t.production_hours), 0) * 100)::numeric, 1) AS performance_pct,
    ROUND(((SUM(t.production_qty) - SUM(t.scrap_qty))::float / NULLIF(SUM(t.production_qty), 0) * 100)::numeric, 1) AS quality_pct
FROM fact_oee_transactions t
JOIN dim_machines m ON t.machine_id = m.machine_id
WHERE m.machine_name = 'DCM3'
GROUP BY m.machine_name, DATE_TRUNC('month', t.transaction_date)
ORDER BY month;
```

---

### Schema: `prolink` — SPC Process Parameter Data

Shot-by-shot process parameters captured from Pro-Link software running on each DCM PC. Data is polled from CSV files on the DCM PCs every 30 seconds and ingested into PostgreSQL.

#### Table: `prolink.machines` (14 rows)

| Column | Type | Description |
|--------|------|-------------|
| `machine_id` | SERIAL PK | Internal ID |
| `machine_code` | VARCHAR | Pro-Link machine code, e.g. "DA0021" |
| `display_name` | VARCHAR | e.g. "DCM1" |
| `oee_machine_id` | INT | FK to `dim_machines` for OEE correlation |
| `mongo_equipment_id` | VARCHAR(24) | MongoDB ObjectId from equipment collection |

#### Table: `prolink.spc_parameters` (~88 rows)

Catalogue of known SPC parameters.

| Column | Type | Description |
|--------|------|-------------|
| `param_id` | SERIAL PK | |
| `param_name` | VARCHAR | e.g. "AISV", "CYCLE_TIME", "FIP" |
| `category` | VARCHAR | e.g. "Velocity", "Pressure", "Temperature" |
| `unit` | VARCHAR | e.g. "mm/s", "bar", "seconds" |
| `is_critical` | BOOLEAN | Flagged for dashboard display |

**Key parameters for die casting analysis:**

| Parameter | Description | Category |
|-----------|-------------|----------|
| AISV | Average Intensification Shot Velocity | Velocity |
| ASSV | Average Slow Shot Velocity | Velocity |
| AFSV | Average Fast Shot Velocity | Velocity |
| FIP | Final Intensifier Pressure | Pressure |
| EOSP | End of Shot Pressure | Pressure |
| CYCLE_TIME | Total cycle time | Timing |
| FT | Fill Time | Timing |
| B_L | Biscuit Length | Position |
| TB1Ton–TB4Ton | Tie Bar Temperatures | Temperature |

#### Table: `prolink.spc_shots` (one row per shot)

| Column | Type | Description |
|--------|------|-------------|
| `shot_id` | BIGSERIAL PK | |
| `machine_id` | INT FK | → prolink.machines |
| `shot_counter` | INT | Incrementing counter from Pro-Link |
| `shot_timestamp` | TIMESTAMPTZ | When the shot occurred |
| `part_name` | VARCHAR | Extracted from .plv file path, e.g. "RDU350_CASE_Cav19_gen6_1100t" |

#### Table: `prolink.spc_values` (one row per parameter per shot — EAV design)

| Column | Type | Description |
|--------|------|-------------|
| `value_id` | BIGSERIAL PK | |
| `shot_id` | BIGINT FK | → prolink.spc_shots |
| `param_id` | INT FK | → prolink.spc_parameters |
| `lsl` | FLOAT | Lower spec limit (NULL if undefined) |
| `process_value` | FLOAT | Actual measured value |
| `usl` | FLOAT | Upper spec limit (NULL if undefined) |
| `is_in_spec` | BOOLEAN | **Computed column** — true if within LSL/USL |

#### Table: `prolink.activity_events` (machine events)

| Column | Type | Description |
|--------|------|-------------|
| `event_id` | BIGSERIAL PK | |
| `machine_id` | INT FK | → prolink.machines |
| `event_timestamp` | TIMESTAMPTZ | |
| `log_type` | VARCHAR | "Shot", "MachMode", "Proc", "ValueChg", "CmdSent" |
| `msg_number` | INT | 0 = info, negative = alarm |
| `message` | TEXT | Human-readable description |
| `user_id` | VARCHAR | Operator logged in |

#### Materialised view: `prolink.mv_spc_hourly_stats`

Pre-aggregated hourly statistics per machine per parameter. Refreshed every 15 minutes by an Agenda scheduled job.

| Column | Type | Description |
|--------|------|-------------|
| `machine_id` | INT | |
| `part_name` | VARCHAR | |
| `param_name` | VARCHAR | |
| `hour` | TIMESTAMPTZ | Truncated to hour |
| `shot_count` | INT | Shots in that hour |
| `avg_value` | FLOAT | Mean process value |
| `min_value` | FLOAT | |
| `max_value` | FLOAT | |
| `stddev_value` | FLOAT | Standard deviation |
| `lsl` | FLOAT | |
| `usl` | FLOAT | |
| `out_of_spec_count` | INT | Shots outside spec |

**Example query — SPC parameter trend for a machine:**

```sql
SELECT
    s.shot_timestamp,
    p.param_name,
    v.process_value,
    v.lsl,
    v.usl,
    v.is_in_spec
FROM prolink.spc_shots s
JOIN prolink.spc_values v ON v.shot_id = s.shot_id
JOIN prolink.spc_parameters p ON p.param_id = v.param_id
JOIN prolink.machines m ON s.machine_id = m.machine_id
WHERE m.display_name = 'DCM3'
  AND p.param_name = 'CYCLE_TIME'
  AND s.shot_timestamp BETWEEN '2025-10-01' AND '2025-10-31'
ORDER BY s.shot_timestamp;
```

**Example query — hourly SPC summary (uses materialised view for performance):**

```sql
SELECT
    m.display_name,
    h.part_name,
    h.param_name,
    h.hour,
    h.shot_count,
    ROUND(h.avg_value::numeric, 3) AS avg_val,
    ROUND(h.stddev_value::numeric, 3) AS stddev_val,
    h.out_of_spec_count
FROM prolink.mv_spc_hourly_stats h
JOIN prolink.machines m ON h.machine_id = m.machine_id
WHERE m.display_name = 'DCM3'
  AND h.param_name = 'AFSV'
  AND h.hour BETWEEN '2025-10-15 00:00:00' AND '2025-10-16 00:00:00'
ORDER BY h.hour;
```

**Example query — process alarms for a machine:**

```sql
SELECT
    m.display_name,
    a.event_timestamp,
    a.message,
    a.msg_number,
    a.user_id
FROM prolink.activity_events a
JOIN prolink.machines m ON a.machine_id = m.machine_id
WHERE m.display_name = 'DCM3'
  AND a.log_type = 'Proc'
  AND a.event_timestamp BETWEEN '2025-10-01' AND '2025-10-31'
ORDER BY a.event_timestamp DESC;
```

---

## 3. SQL Server — OXSAS Spectrometer Data

### Connection

```python
import pymssql

conn = pymssql.connect(
    server="192.168.54.18",
    port=1433,
    user="CastNet",
    password="CastNet400!",
    database="ANALYSES"
)
```

Install with: `pip install pymssql`

This is a **read-only** connection. The CastNet user cannot modify data.

**Important:** Always use the `ANALYSES` database, not `OXSAS_DB` (which is configuration only).

### Schema Overview

The OXSAS database uses an EAV (entity-attribute-value) pattern for both metadata and elemental concentrations.

#### Table: `Analyses` (main — 37,690+ rows)

| Column | Type | Description |
|--------|------|-------------|
| `ID` | INT PK | Analysis identifier |
| `AnaDateTime` | DATETIME | When the analysis was performed |

#### Table: `Attributes` (metadata — key-value pairs)

| Column | Type | Description |
|--------|------|-------------|
| `LinkAnalyses` | INT FK | → Analyses.ID |
| `LinkName` | INT FK | → AttributeName.ID |
| `Value` | NVARCHAR | The attribute value |

**AttributeName lookup (critical):**

| LinkName ID | Meaning | Example values |
|-------------|---------|----------------|
| 4 | Signature | "DCM9 - TESLA - MON D" |
| 5 | Machine (Furnace No) | "DCM9", "DCM15" |
| 6 | Part Number | "TESLA", "GETRAGB85 14" |
| 7 | Shift Number | "MON D", "SUN N" |
| 8 | Operator | "LG", "IK" |
| 9 | Grade | "A356.0 DAILY CHECK", "EN46000 DAILY CHECK" |

#### Table: `Elements` (elemental concentrations — 1M+ rows)

| Column | Type | Description |
|--------|------|-------------|
| `LinkAnalyses` | INT FK | → Analyses.ID |
| `LinkName` | INT FK | → DisplayName.ID |
| `Value` | NVARCHAR | Concentration as string — must CAST to FLOAT |

#### Table: `DisplayName` (element name lookup — 66 rows)

Maps LinkName IDs to element symbols. Key elements for aluminium die casting:

| ID | Name | ID | Name | ID | Name |
|----|------|----|------|----|------|
| 21 | Si | 10 | Fe | 9 | Cu |
| 15 | Mn | 14 | Mg | 26 | Zn |
| 24 | Ti | 8 | Cr | 17 | Ni |
| 23 | Sr | 2 | SF | | |

**Data quality notes:**
- Element concentrations are stored as NVARCHAR strings — always `CAST(Value AS FLOAT)`
- Near-zero values like `9.9999999747524292e-07` mean "not detected" — treat as 0
- Element names are case-sensitive: use `'Si'` not `'SI'`

**Example query — recent spectrometer analyses with key elements:**

```sql
WITH AnalysisMetadata AS (
    SELECT
        a.ID,
        a.AnaDateTime,
        MAX(CASE WHEN attr.LinkName = 5 THEN attr.Value END) AS Machine,
        MAX(CASE WHEN attr.LinkName = 6 THEN attr.Value END) AS Part,
        MAX(CASE WHEN attr.LinkName = 7 THEN attr.Value END) AS Shift,
        MAX(CASE WHEN attr.LinkName = 9 THEN attr.Value END) AS Grade
    FROM (
        SELECT TOP 100 ID, AnaDateTime
        FROM Analyses
        WHERE AnaDateTime >= '2025-01-01'
        ORDER BY AnaDateTime DESC
    ) a
    LEFT JOIN Attributes attr ON a.ID = attr.LinkAnalyses
    GROUP BY a.ID, a.AnaDateTime
),
ElementData AS (
    SELECT
        e.LinkAnalyses,
        MAX(CASE WHEN dn.Name = 'Si' THEN CAST(e.Value AS FLOAT) END) AS Si,
        MAX(CASE WHEN dn.Name = 'Fe' THEN CAST(e.Value AS FLOAT) END) AS Fe,
        MAX(CASE WHEN dn.Name = 'Cu' THEN CAST(e.Value AS FLOAT) END) AS Cu,
        MAX(CASE WHEN dn.Name = 'Mg' THEN CAST(e.Value AS FLOAT) END) AS Mg,
        MAX(CASE WHEN dn.Name = 'Mn' THEN CAST(e.Value AS FLOAT) END) AS Mn,
        MAX(CASE WHEN dn.Name = 'Zn' THEN CAST(e.Value AS FLOAT) END) AS Zn,
        MAX(CASE WHEN dn.Name = 'Ti' THEN CAST(e.Value AS FLOAT) END) AS Ti,
        MAX(CASE WHEN dn.Name = 'Sr' THEN CAST(e.Value AS FLOAT) END) AS Sr
    FROM Elements e
    INNER JOIN DisplayName dn ON e.LinkName = dn.ID
    WHERE e.LinkAnalyses IN (
        SELECT TOP 100 ID FROM Analyses
        WHERE AnaDateTime >= '2025-01-01'
        ORDER BY AnaDateTime DESC
    )
    GROUP BY e.LinkAnalyses
)
SELECT
    am.AnaDateTime,
    am.Machine,
    am.Part,
    am.Shift,
    am.Grade,
    ed.Si, ed.Fe, ed.Cu, ed.Mg, ed.Mn, ed.Zn, ed.Ti, ed.Sr
FROM AnalysisMetadata am
LEFT JOIN ElementData ed ON am.ID = ed.LinkAnalyses
ORDER BY am.AnaDateTime DESC;
```

**Example query — analyses for a specific machine and date range:**

```sql
SELECT
    a.ID,
    a.AnaDateTime,
    attr.Value AS Machine
FROM Analyses a
INNER JOIN Attributes attr ON a.ID = attr.LinkAnalyses
WHERE attr.LinkName = 5
  AND attr.Value = 'DCM3'
  AND a.AnaDateTime BETWEEN '2025-10-01' AND '2025-10-31'
ORDER BY a.AnaDateTime DESC;
```

---

## 4. Cross-Referencing Between Data Sources

### Machine Identity Mapping

The same physical machine has different identifiers in each system:

| Physical Machine | MongoDB `equipment` | PostgreSQL OEE `dim_machines` | PostgreSQL ProLink `prolink.machines` | OXSAS `Attributes` (LinkName=5) | Odyssey Operation Code |
|-----------------|---------------------|-------------------------------|---------------------------------------|--------------------------------|----------------------|
| DCM 1 | "DCM 1" | "DCM1" (machine_id=1) | "DA0021" (display_name="DCM1") | "DCM1" | 0402D01 |
| DCM 3 | "DCM 3" | "DCM3" (machine_id=3) | "DA0023" (display_name="DCM3") | "DCM3" | 0402D03 |

Note the spacing difference: MongoDB uses "DCM 1" (with space), while PostgreSQL and OXSAS use "DCM1" (no space). When correlating data across systems, normalise the machine name by stripping spaces.

The `prolink.machines` table has explicit cross-reference columns:
- `oee_machine_id` → links to `dim_machines.machine_id`
- `mongo_equipment_id` → links to MongoDB `equipment._id`

### Shift Identity Mapping

| System | Day Shift | Night Shift |
|--------|-----------|-------------|
| MongoDB shift reports | "Days" | "Nights" |
| PostgreSQL OEE | shift_code=1, "Day" | shift_code=3, "Night" |
| OXSAS | "MON D", "TUE D", etc. | "MON N", "TUE N", etc. |

Day = 06:00–18:00. Night = 18:00–06:00 (into next calendar day).

### Correlating Shift Reports with OEE Data

To combine a shift report's narrative with the corresponding OEE metrics:

```python
# 1. Get shift report from MongoDB
report = db["reports"].find_one({
    "equipment": "DCM 3",
    "shift": "Days",
    "date_iso": {"$gte": datetime(2025, 10, 15), "$lt": datetime(2025, 10, 16)}
})

# 2. Get matching OEE from PostgreSQL
cursor = pg_conn.cursor()
cursor.execute("""
    SELECT
        t.production_qty, t.scrap_qty,
        ROUND((t.availability * 100)::numeric, 1) AS availability_pct,
        ROUND((t.performance * 100)::numeric, 1) AS performance_pct,
        ROUND((t.quality * 100)::numeric, 1) AS quality_pct,
        ROUND((t.oee * 100)::numeric, 1) AS oee_pct,
        ROUND(t.downtime_hours::numeric, 2) AS downtime_hrs
    FROM fact_oee_transactions t
    JOIN dim_machines m ON t.machine_id = m.machine_id
    JOIN dim_shifts s ON t.shift_id = s.shift_id
    WHERE m.machine_name = 'DCM3'
      AND s.shift_code = 1
      AND t.transaction_date = '2025-10-15'
""")
oee_row = cursor.fetchone()
```

### Correlating Shift Reports with SPC Data

To get SPC summaries for the same shift window:

```sql
-- SPC summary for DCM3, day shift (06:00-18:00), 15 Oct 2025
SELECT
    p.param_name,
    COUNT(*) AS shot_count,
    ROUND(AVG(v.process_value)::numeric, 3) AS avg_value,
    ROUND(STDDEV(v.process_value)::numeric, 3) AS stddev_value,
    COUNT(*) FILTER (WHERE NOT v.is_in_spec) AS out_of_spec_count
FROM prolink.spc_shots s
JOIN prolink.spc_values v ON v.shot_id = s.shot_id
JOIN prolink.spc_parameters p ON p.param_id = v.param_id
JOIN prolink.machines m ON s.machine_id = m.machine_id
WHERE m.display_name = 'DCM3'
  AND s.shot_timestamp >= '2025-10-15 06:00:00'
  AND s.shot_timestamp < '2025-10-15 18:00:00'
  AND p.param_name IN ('CYCLE_TIME', 'AFSV', 'FIP', 'B_L')
GROUP BY p.param_name
ORDER BY p.param_name;
```

---

## 5. Python Dependencies

Add these to your `pyproject.toml` or `requirements.txt`:

```
pymongo>=4.6
psycopg2-binary>=2.9
pymssql>=2.2
```

---

## 6. Migrating from Static JSON to Live Queries

The Hartree POC loads shift reports from a static JSON export:

```python
# OLD (Hartree POC)
with open("data/castnet.reports.json") as f:
    castnet_reports = json.load(f)
filtered_reports = filter_reports_by_config(castnet_reports, filters)
```

Replace with a direct MongoDB query:

```python
# NEW (live data)
from pymongo import MongoClient
from datetime import datetime

client = MongoClient("mongodb://localhost:27017")
db = client["castnet"]

# Build MongoDB query from the same filter config
filters = {
    "report": ["porosity"],
    "die": ["KM RDM Carrier"],
    "date_iso": [2024, 2025]
}

query = {}
if "report" in filters:
    query["report"] = {"$regex": "|".join(filters["report"]), "$options": "i"}
if "die" in filters:
    query["die"] = {"$regex": "|".join(filters["die"]), "$options": "i"}
if "date_iso" in filters:
    years = filters["date_iso"]
    query["date_iso"] = {
        "$gte": datetime(min(years), 1, 1),
        "$lte": datetime(max(years), 12, 31)
    }

reports = list(db["reports"].find(query, {"_id": 0}).sort("date_iso", -1))
print(f"Number of filtered reports: {len(reports)}")
```

The rest of the pipeline (system prompt, context, sending to LLM) stays the same — the LLM still receives JSON, it just comes from a live query instead of a file.

---

## 7. Data Volume Reference

| Data Source | Approximate Volume | Growth Rate |
|-------------|-------------------|-------------|
| MongoDB shift reports | ~20 years of data | ~2-4 per day |
| PostgreSQL OEE (fact_oee_transactions) | ~141,806 records (2024 onwards), data from 2009 | ~28 rows/day (14 machines × 2 shifts) |
| PostgreSQL ProLink SPC shots | Growing — ~15,000 shots/day | ~5.5M rows/year |
| PostgreSQL ProLink SPC values (EAV) | Growing — ~900K rows/day | ~331M rows/year |
| PostgreSQL ProLink activity events | Growing — ~700 events/hour | ~6.1M rows/year |
| OXSAS spectrometer analyses | 37,690+ analyses | ~10-20 per day |

---

## 8. Important Technical Notes

### MongoDB `withDB` Pattern
CastNet's Node.js backend uses a `withDB` wrapper that opens and closes connections per request. For the Python pipeline, use a persistent `MongoClient` connection — PyMongo handles connection pooling automatically.

### PostgreSQL Connection Pooling
For repeated queries in the pipeline, keep the connection open for the duration of the analysis run. Don't open/close per query.

### OXSAS Performance
The Elements table has 1M+ rows. Always use the CTE pattern shown above (filter to relevant Analyses IDs first via `TOP N`, then join Elements only for those IDs). Never do an unfiltered scan of the Elements table.

### OEE Performance Can Exceed 100%
This is correct and expected in die casting — it means operators ran faster than the standard routing rate. Do not cap or flag this as an error.

### Date/Time Zones
- MongoDB stores dates in UTC
- PostgreSQL uses TIMESTAMPTZ (timezone-aware)
- OXSAS SQL Server stores local UK time (no timezone info)
- CastNet operates on UK time (GMT/BST)

### Read-Only Access
The OXSAS connection is read-only. MongoDB and PostgreSQL are read-write but the LLM pipeline should only read — never insert, update, or delete production data.
