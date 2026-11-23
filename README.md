# cloud-cost-mgmt

[![dbt build](https://github.com/KrisanaP/cloud-cost-mgmt/actions/workflows/dbt.yml/badge.svg)](https://github.com/KrisanaP/cloud-cost-mgmt/actions/workflows/dbt.yml)
[![dashboard](https://github.com/KrisanaP/cloud-cost-mgmt/actions/workflows/dashboard.yml/badge.svg)](https://github.com/KrisanaP/cloud-cost-mgmt/actions/workflows/dashboard.yml)
![dbt tests](https://img.shields.io/badge/dbt%20tests-78-blue)
![pytest](https://img.shields.io/badge/pytest-8-blue)

**How much does each project really spend on AWS, when resources are shared and tags are late or wrong?**

A mini cloud cost management tool (in the spirit of Datadog CCM) built on **dbt + DuckDB** over a simulated
AWS Cost and Usage Report (CUR 2.0). Every dollar on the bill ends up on a project, and a test proves the
allocated total equals the bill to the cent, every month.

[ภาษาไทย](README.th.md) · [Data dictionary](docs/data-dictionary.md) · [Lineage](docs/lineage.md) · [Tests](docs/testing.md) · [Roadmap](docs/ROADMAP.md) · [Design decisions](docs/decisions/) · [Articles](docs/articles/)

## The problem

| Pain | What usually happens | What this project does |
| --- | --- | --- |
| Savings Plans and RIs are paid in a monthly fee line | The buying account looks expensive, the teams using them look free | **Effective (amortized) cost** moves commitment cost onto the usage lines that consumed it |
| Tags are not retroactive | A resource tagged in September is "unowned" for July and August forever | **SCD2 ownership overrides** with valid-from / valid-to; fix one seed row and history is recomputed |
| Shared resources (EKS cluster, network, support, tax) | Dumped into "shared" or split by gut feeling | **Versioned allocation rules**: even, fixed %, proportional to direct cost, or usage driver (vCPU-hours), with step-down |
| Rounding | Splitting $10 three ways gives $9.99 | **Largest remainder** allocation, so totals match exactly |
| AWS rewrites the current month several times a day | Appending duplicates cost | **Incremental delete+insert** by billing period, tested with a simulated restatement |

## Architecture

```mermaid
flowchart TB
    CUR[("<b>AWS CUR 2.0</b> (simulated)<br/>data/cur2_sample.parquet<br/>Jul–Sep 2026 · 7 accounts · 28k line items")]

    subgraph DBT["dbt-duckdb  ·  warehouse.duckdb"]
        direction TB
        STG["<b>staging</b><br/>stg_cur__line_items · stg_cur__resource_tags"]
        EFF["<b>effective cost</b> · amortize SP / RI fees onto usage<br/>int_cost__effective → fct_cost_line_item (incremental)"]
        ATT["<b>attribution</b> · override › tag › account default<br/>int_cost__attributed → fct_cost_attributed"]
        ALC["<b>shared-cost allocation</b> · step-down, largest remainder<br/>int_alloc__pools / direct_basis / shares → fct_cost_allocated"]
        MART["<b>marts</b><br/>mart_project_cost_monthly / daily<br/>mart_attribution_coverage · mart_allocation_audit"]
        STG --> EFF --> ATT --> ALC --> MART

        SEED[/"<b>seeds</b><br/>projects · tag_project_map<br/>account_default_project"/] --> ATT
        OWN[/"<b>resource_ownership</b><br/>SCD2 valid_from / valid_to"/] --> ATT
        OWN -.-> SNAP[("snap_resource_ownership<br/>who changed it, when")]
        RULES[/"<b>allocation_rules</b> + targets<br/>versioned"/] --> ALC
        USE[/"<b>usage_drivers</b><br/>EKS vCPU-hours"/] --> ALC
        MART -.- TEST{{"<b>78 dbt tests</b><br/>allocated total = bill"}}
    end

    CUR --> STG

    subgraph OUT["Consumers · no API layer"]
        direction LR
        EVI["<b>Evidence dashboard</b><br/>overview · project detail · coverage<br/>(via export_marts.py → Parquet)"]
        ST1["<b>Streamlit · rules editor</b><br/>edits allocation_rules seed<br/>reruns dbt to preview impact"]
        ST2["<b>Streamlit · audit trail</b><br/>any dollar back to bill lines"]
    end

    MART --> EVI
    MART --> ST1
    MART --> ST2

    subgraph CI["GitHub Actions"]
        direction LR
        W1["<b>dbt.yml</b><br/>dbt build + restatement test"]
        W2["<b>dashboard.yml</b><br/>dbt build · pytest · dbt docs · Evidence"]
    end
    EVI --> W2
    W2 --> PAGES["<b>GitHub Pages</b><br/>dashboard + /dbt-docs/"]

    classDef src fill:#eef2ff,stroke:#6366f1,color:#1e1b4b
    classDef core fill:#ecfdf5,stroke:#059669,color:#064e3b
    classDef seed fill:#fffbeb,stroke:#d97706,color:#78350f
    classDef app fill:#fdf2f8,stroke:#db2777,color:#500724
    classDef ci fill:#f1f5f9,stroke:#475569,color:#0f172a
    class CUR src
    class STG,EFF,ATT,ALC,MART,SNAP,TEST core
    class SEED,OWN,RULES,USE seed
    class EVI,ST1,ST2 app
    class W1,W2,PAGES ci
    style DBT fill:#fafafa,stroke:#a3a3a3
    style OUT fill:#fafafa,stroke:#a3a3a3
    style CI fill:#fafafa,stroke:#a3a3a3
```

PNG version: [docs/img/architecture.png](docs/img/architecture.png) · source: [docs/architecture.mmd](docs/architecture.mmd) · model-level lineage: [dbt docs](https://krisanap.github.io/cloud-cost-mgmt/dbt-docs/)

No API layer: dbt writes report tables, the dashboard and Streamlit read them directly.

## What the tests guarantee

Full list with what each test catches: [docs/testing.md](docs/testing.md).

- Raw file = staging = fact = daily mart, per billing period, for unblended, net and effective cost
- Every Savings Plan / RI fee = cost moved to usage + unused part
- Attribution never adds or drops a row or a cent; ownership date ranges never overlap
- After allocation, each bill line sums back to its original cost, and **the monthly allocated total equals the bill**
- Fixed percentages sum to 100, no rule allocates back into a shared pool, no line matches two rules at the same step
- Unit tests cover mid-month ownership moves, late tags, and each allocation method
- A restatement run rewrites September and checks nothing is duplicated

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cd dbt && dbt build --profiles-dir . && cd ..       # models + data/unit tests
bash scripts/simulate_restatement.sh                 # AWS rewrites a month; totals must not double
pytest -q tests                                      # Streamlit rule validation + page smoke tests
streamlit run streamlit_app/Home.py                  # rules editor + audit trail

python3 scripts/export_marts.py                      # dashboard data (Parquet)
cd dashboard && npm install && npm run sources && npm run dev
```

## Screenshots

| Audit: where did this project's money come from? | Allocation rules editor |
| --- | --- |
| ![audit](docs/img/streamlit_audit.png) | ![rules](docs/img/streamlit_rules.png) |

## Data

`data/cur2_sample.*` is **simulated**, not a real bill, generated by `scripts/gen_cur2.py`
(1 Jul – 30 Sep 2026, 7 accounts, 50+ AWS services, approximate prices). It deliberately contains a few
real-world problems to find. Usage drivers for the shared EKS cluster are simulated by
`scripts/gen_usage_drivers.py`; in production they would come from CloudWatch Container Insights or OpenCost.

A second, **real** dataset lives in `data/focus/`: 100k rows of the FinOps Foundation
[FOCUS 1.0 Sample Data](https://github.com/FinOps-Open-Cost-and-Usage-Spec/FOCUS-Sample-Data)
(anonymized AWS, Azure and OCI billing, Sep 2024, CC BY 4.0, © FinOps Foundation). It runs through
`stg_focus__charges` → `fct_focus_cost_daily` / `mart_focus_tag_coverage`, is reconciled to the raw file
by `assert_focus_totals_match_raw`, and has its own dashboard page (`dashboard/pages/focus.md`).
Its tags are randomized and it covers one month, so it is used for multi-cloud reporting and tag coverage,
not for SCD2 attribution or allocation. See `data/focus/README.md` for caveats.

## Stack

dbt-core 1.12 · dbt-duckdb · DuckDB · Evidence · Streamlit · GitHub Actions
