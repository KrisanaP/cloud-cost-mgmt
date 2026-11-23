# Lineage and table relationships

Two views of the dbt project: which model is built from which (lineage), and how the main tables join (ERD).
The interactive version of the lineage is in [dbt docs](https://krisanap.github.io/cloud-cost-mgmt/dbt-docs/)
(click the graph icon). For the big picture see [architecture](../README.md#architecture);
for columns see [data-dictionary.md](data-dictionary.md).

## Model lineage

Every `ref()` / `source()` in `dbt/models`, drawn left to right. Seeds are the orange shapes; they are the
only inputs people edit by hand (or through the Streamlit rules page). The `projects` seed is left out to keep
the graph readable: `fct_cost_attributed`, `int_alloc__direct_basis`, `int_alloc__shares` and `fct_cost_allocated`
all join it.

```mermaid
flowchart LR
    RAW[("source: cur.cur2_raw<br/>data/cur2_sample.parquet")]

    subgraph staging
        STG[stg_cur__line_items]
        TAGS[stg_cur__resource_tags]
    end

    subgraph intermediate
        EFF[int_cost__effective]
        LIT[int_cost__line_item_tags]
        ATT[int_cost__attributed]
        POOL[int_alloc__pools]
        DB[int_alloc__direct_basis]
        SH[int_alloc__shares]
    end

    subgraph marts
        FLI["fct_cost_line_item<br/>(incremental)"]
        FD[fct_cost_daily]
        FA[fct_cost_attributed]
        FPM[fct_project_cost_monthly]
        FAL[fct_cost_allocated]
        FPAM[fct_project_cost_allocated_monthly]
        MM[mart_project_cost_monthly]
        MD[mart_project_cost_daily]
        MC[mart_attribution_coverage]
        MA[mart_allocation_audit]
    end

    TPM[/tag_project_map/]
    ADP[/account_default_project/]
    RO[/resource_ownership/]
    AR[/allocation_rules/]
    ART[/allocation_rule_targets/]
    UD[/usage_drivers/]

    RAW --> STG --> TAGS
    STG --> EFF --> FLI
    FLI --> FD
    FLI --> LIT
    FLI --> ATT
    LIT --> ATT
    TPM --> ATT
    ADP --> ATT
    RO --> ATT
    RO -.-> SNAP[("snap_resource_ownership")]
    ATT --> FA
    FA --> FPM

    FA --> POOL
    AR --> POOL
    FA --> DB
    POOL --> DB
    POOL --> SH
    DB --> SH
    ART --> SH
    UD --> SH

    FA --> FAL
    POOL --> FAL
    SH --> FAL

    FAL --> FPAM
    FAL --> MM
    FAL --> MD
    FAL --> MC
    FAL --> MA
    FA --> MA
    AR --> MA

    classDef seed fill:#fffbeb,stroke:#d97706,color:#78350f
    classDef mart fill:#fdf2f8,stroke:#db2777,color:#500724
    class TPM,ADP,RO,AR,ART,UD seed
    class MM,MD,MC,MA mart
```

### What each step does

| Step | Model | In one line |
| --- | --- | --- |
| Clean | `stg_cur__line_items` | Cast types, rename CUR 2.0 columns, 1 row = 1 line item |
| | `stg_cur__resource_tags` | Explode the tag JSON into rows, lower-case and trim keys/values |
| Effective cost | `int_cost__effective` | Amortized cost per line + `cost_class` |
| | `fct_cost_line_item` | Same, stored incrementally by billing period (restatement-safe) |
| Attribution | `int_cost__line_item_tags` | Tags for every month already in the fact table |
| | `int_cost__attributed` | Pick the owner: override › tag › account default › unattributed |
| | `fct_cost_attributed` | Adds project details, rebuilt in full so ownership fixes reach past months |
| Allocation | `int_alloc__pools` | Lines owned by a shared pool that match a rule (lowest step wins) |
| | `int_alloc__direct_basis` | Each project's direct cost per day, the basis for `proportional_direct` |
| | `int_alloc__shares` | Split each pool line by the rule's method, then largest remainder to the 6th decimal |
| | `fct_cost_allocated` | Direct lines (1 row) + split lines (1 row per receiver) |
| Report | `mart_*` | Shapes for the dashboard and the audit page |

### Step-down

Rules run in `step` order. Step 1 splits shared infrastructure (EKS, network, unused commitments).
Step 2 splits support, tax and credits **in proportion to direct cost plus what each project received in
step 1**, so a project that uses a lot of shared infrastructure also carries its fair part of support and tax.
A project that receives a share can never be a pool, so money never loops back (tested).

## Table relationships (ERD)

Keys that join the main tables. All `*_id` keys are varchar.

```mermaid
erDiagram
    fct_cost_line_item ||--|| fct_cost_attributed : "line_item_id"
    fct_cost_attributed ||--|{ fct_cost_allocated : "line_item_id (1 to many after split)"
    fct_cost_allocated ||--|| mart_allocation_audit : "line_item_id + project_id"
    projects ||--o{ fct_cost_attributed : "project_id (owner)"
    projects ||--o{ fct_cost_allocated : "project_id (receiver)"
    projects ||--o{ resource_ownership : "project_id"
    projects ||--o{ tag_project_map : "project_id"
    projects ||--o{ account_default_project : "project_id"
    allocation_rules ||--o{ allocation_rule_targets : "rule_id + rule_version"
    allocation_rules ||--o{ fct_cost_allocated : "rule_id + rule_version"
    projects ||--o{ usage_drivers : "project_id"

    fct_cost_line_item {
        varchar line_item_id PK
        date billing_period
        date usage_date
        varchar account_id
        varchar resource_id
        varchar cost_class
        double effective_cost
    }
    fct_cost_attributed {
        varchar line_item_id PK
        varchar project_id FK
        varchar attribution_source
    }
    fct_cost_allocated {
        varchar line_item_id PK
        varchar project_id PK
        double allocated_cost
        varchar allocation_status
        varchar rule_id FK
        int rule_version FK
    }
    mart_allocation_audit {
        varchar line_item_id
        varchar project_id
        varchar cost_type
        varchar rule_name
    }
    projects {
        varchar project_id PK
        boolean is_shared
        varchar owner_team
    }
    resource_ownership {
        varchar resource_id PK
        date valid_from PK
        date valid_to
        varchar project_id FK
    }
    tag_project_map {
        varchar tag_key PK
        varchar tag_value PK
        varchar project_id FK
    }
    account_default_project {
        varchar account_id PK
        date valid_from PK
        varchar project_id FK
    }
    allocation_rules {
        varchar rule_id PK
        int rule_version PK
        int step
        varchar method
        date valid_from
        date valid_to
    }
    allocation_rule_targets {
        varchar rule_id FK
        int rule_version FK
        varchar project_id FK
        double pct
    }
    usage_drivers {
        date usage_date
        varchar driver_metric
        varchar project_id FK
        double quantity
    }
```

Date-ranged joins (`resource_ownership`, `account_default_project`, `allocation_rules`) match when
`valid_from <= usage_date < coalesce(valid_to, '9999-12-31')`. Tests make sure ranges for the same key never overlap,
so each line finds at most one row.
