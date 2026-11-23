# Data dictionary

The tables people query, one section per table. Everything is in USD, dates are UTC, and every cost column
here is **effective (amortized) cost** unless the name says otherwise
(see [decision 0001](decisions/0001-effective-cost.md)).

Row counts are from the sample data (Jul–Sep 2026). Model-level lineage: [lineage.md](lineage.md).
What the tests guarantee about these tables: [testing.md](testing.md).

| Table | Grain (1 row =) | Rows | Read by |
| --- | --- | ---: | --- |
| [`mart_project_cost_monthly`](#mart_project_cost_monthly) | month × project | 33 | Evidence overview, Streamlit |
| [`mart_project_cost_daily`](#mart_project_cost_daily) | day × project × direct/shared | 1,932 | Evidence trend charts |
| [`mart_attribution_coverage`](#mart_attribution_coverage) | month × account × service × resource, unattributed only | 121 | Evidence coverage page |
| [`mart_allocation_audit`](#mart_allocation_audit) | project × bill line | 80,370 | Streamlit audit page |
| [`fct_cost_allocated`](#fct_cost_allocated) | bill line × project, after sharing | 80,370 | source of every mart |
| [`fct_cost_attributed`](#fct_cost_attributed) | bill line, with owner | 28,381 | allocation, audit |
| [`fct_cost_line_item`](#fct_cost_line_item) | bill line | 28,381 | everything (incremental) |
| [`fct_cost_daily`](#fct_cost_daily) | day × account × service × resource × cost class | 26,164 | ad-hoc |
| `fct_project_cost_monthly` | month × project × cost class × attribution source | 67 | before-sharing view |
| `fct_project_cost_allocated_monthly` | month × project × cost source (`direct` or rule id) | 194 | "where did shared cost come from" |

---

## Shared vocabulary

**`cost_class`**: what kind of money a bill line is. Derived from `line_item_type` in `int_cost__effective`.

| Value | From `line_item_type` | Meaning |
| --- | --- | --- |
| `direct` | Usage, SavingsPlanCoveredUsage, DiscountedUsage | Someone used something. SP/RI lines carry their amortized cost |
| `commitment_offset` | SavingsPlanNegation | Cancels the on-demand price of SP-covered usage. Effective cost = 0 |
| `commitment_unused` | SavingsPlanRecurringFee, RIFee | The part of a commitment nobody used |
| `tax` | Tax | |
| `support` | Fee with product `AWSSupport*` | |
| `credit` | Credit, Refund | Negative amounts |
| `fee` | other Fee | |

**`attribution_source`**: how a line got its owner, checked in this order (first hit wins):

| Value | Meaning |
| --- | --- |
| `override` | A row in seed `resource_ownership` covers this resource on this date (SCD2, `[valid_from, valid_to)`) |
| `tag` | The `user_service` tag maps to a project in seed `tag_project_map` (keys/values lower-cased and trimmed) |
| `account_default` | The account has a default project in seed `account_default_project` |
| `unattributed` | None of the above |

**`allocation_status`** (in `fct_cost_allocated`):

| Value | Meaning |
| --- | --- |
| `direct` | Not a shared line. One row, `allocated_cost = effective cost`, `share_pct = 1` |
| `allocated` | A shared line split by a rule. One row per receiving project |
| `no_basis` | A shared line matched a rule but had nothing to split by that day (e.g. no usage driver). Stays with its original owner |

**`cost_type`** (in marts): `shared` when `allocation_status = 'allocated'`, otherwise `direct`.

---

## mart_project_cost_monthly

Monthly cost per project after sharing. The overview page reads this.
Unique on `(billing_period, project_id)`.

| Column | Type | Description |
| --- | --- | --- |
| `billing_period` | date | First day of the month |
| `project_id` | varchar | Project key, see seed `projects` |
| `project_name` | varchar | |
| `owner_team` | varchar | |
| `direct_cost` | double | Cost the project owns directly (rows with `cost_type = direct`) |
| `shared_cost` | double | Cost received from allocation rules |
| `total_cost` | double | `direct_cost + shared_cost` |
| `prev_total_cost` | double | `total_cost` of the previous month, null for the first month |
| `mom_change` | double | `total_cost - prev_total_cost` |
| `mom_change_pct` | double | `total_cost / prev_total_cost - 1` (0.12 = +12%) |

```sql
-- Top projects last month
select project_id, total_cost, mom_change_pct
from mart_project_cost_monthly
where billing_period = (select max(billing_period) from mart_project_cost_monthly)
order by total_cost desc;
```

## mart_project_cost_daily

Daily cost per project, split into direct and shared, for trend charts.
Monthly lines (support, tax, fees) land on the 1st of the month, as AWS records them.

| Column | Type | Description |
| --- | --- | --- |
| `usage_date` | date | |
| `billing_period` | date | |
| `project_id` | varchar | |
| `project_name` | varchar | |
| `cost_type` | varchar | `direct` or `shared` |
| `cost` | double | |

## mart_attribution_coverage

Cost that still has no owner after sharing, grouped so the biggest tagging gaps come first.
Use `unattributed_cost / total_cost_in_group` for coverage %.

| Column | Type | Description |
| --- | --- | --- |
| `billing_period` | date | |
| `account_name` | varchar | |
| `product_code` | varchar | AWS service, e.g. `AmazonEC2` |
| `resource_key` | varchar | `resource_id`, or `(no resource)` |
| `line_item_count` | bigint | Unattributed lines in the group |
| `unattributed_cost` | double | |
| `total_cost_in_group` | double | All cost for the same month × account × service, owned or not |

```sql
-- Where to fix tags first
select account_name, product_code, resource_key, sum(unattributed_cost) as cost
from mart_attribution_coverage
group by all order by cost desc limit 10;
```

## mart_allocation_audit

Explains every dollar a project received: which bill line, whether it was direct or shared,
which rule and version split it, at what share, and how the line got its original owner.

| Column | Type | Description |
| --- | --- | --- |
| `billing_period`, `usage_date` | date | |
| `project_id`, `project_name` | varchar | Receiving project |
| `cost_type` | varchar | `direct` / `shared` |
| `allocated_cost` | double | Amount this project got from this line |
| `share_pct` | double | Fraction of the line, 0–1 |
| `rule_id`, `rule_version`, `rule_name` | varchar, int, varchar | Rule that split the line (null for direct) |
| `method` | varchar | `even` / `fixed_pct` / `proportional_direct` / `usage_driver` |
| `driver_metric` | varchar | For `usage_driver`, e.g. `vcpu_hours` |
| `step` | int | Step-down order of the rule |
| `line_item_id` | varchar | The CUR bill line |
| `line_effective_cost` | double | Full effective cost of that line before splitting |
| `original_project_id` | varchar | Owner before sharing (a shared pool or `unattributed`) |
| `attribution_source` | varchar | How the original owner was found |
| `override_reason` | varchar | Reason from `resource_ownership` when the source is `override` |
| `tag_project_id` | varchar | What the tag alone would have said (to see overrides beating tags) |
| `account_name`, `product_code`, `resource_id`, `line_item_type`, `cost_class` | varchar | From the bill line |

```sql
-- Where did storefront's shared cost come from in August?
select rule_name, method, sum(allocated_cost) as cost
from mart_allocation_audit
where project_id = 'storefront' and billing_period = '2026-08-01' and cost_type = 'shared'
group by all order by cost desc;
```

## fct_cost_allocated

The core output. One row per bill line per receiving project. Summing `allocated_cost` by line gives
back the line's effective cost, and summing by month gives the bill. Unique on `(line_item_id, project_id)`.

| Column | Type | Description |
| --- | --- | --- |
| `line_item_id` | varchar | |
| `project_id`, `project_name`, `owner_team` | varchar | Receiving project |
| `allocated_cost` | double | Rounded to 6 decimals for split lines; largest remainder keeps the sum exact |
| `share_pct` | double | 0–1 |
| `is_shared` | boolean | Whether the original owner is a shared pool |
| `allocation_status` | varchar | `direct` / `allocated` / `no_basis` |
| `rule_id`, `rule_version`, `step`, `method` | | Null for direct lines |
| `original_project_id` | varchar | Owner from attribution, before sharing |
| `attribution_source` | varchar | |
| `line_effective_cost` | double | |
| `billing_period`, `usage_date`, `account_id`, `account_name`, `product_code`, `resource_id`, `line_item_type`, `cost_class` | | From the bill line |

## fct_cost_attributed

`fct_cost_line_item` plus the owner. Rebuilt in full every run, so fixing an ownership row recomputes
every past month. Unique on `line_item_id`.

All columns of `fct_cost_line_item`, plus:

| Column | Type | Description |
| --- | --- | --- |
| `project_id` | varchar | Owner (never null; `unattributed` when nothing matched) |
| `attribution_source` | varchar | `override` / `tag` / `account_default` / `unattributed` |
| `tag_project_id` | varchar | Project from the tag alone |
| `override_reason` | varchar | |
| `project_name`, `owner_team`, `cost_center` | varchar | From seed `projects` |
| `is_shared` | boolean | Owner is a shared pool (`eks-platform`, `shared-infra`) to be split later |

## fct_cost_line_item

One row per CUR line item, typed and renamed, with effective cost.
**Incremental, delete+insert by `billing_period`**: when AWS restates a month, that month is replaced,
other months stay.

| Column | Type | Description |
| --- | --- | --- |
| `line_item_id` | varchar | `identity_line_item_id`. Unique |
| `billing_period` | date | `bill_billing_period_start_date` |
| `usage_date` | date | Date of `usage_start_at` |
| `usage_start_at`, `usage_end_at` | timestamp | UTC |
| `bill_type`, `invoice_id`, `payer_account_id` | varchar | |
| `account_id`, `account_name` | varchar | Usage account |
| `line_item_type` | varchar | Usage, SavingsPlanCoveredUsage, … (10 values) |
| `cost_class` | varchar | See vocabulary |
| `product_code`, `service_code`, `usage_type`, `operation` | varchar | |
| `region`, `availability_zone` | varchar | |
| `resource_id`, `instance_type`, `pricing_term` | varchar | |
| `usage_amount` | double | |
| `currency_code` | varchar | Always `USD` (tested) |
| `unblended_cost` | double | What the bill line says |
| `net_unblended_cost` | double | After discounts |
| `effective_cost` | double | Amortized. **Use this for project cost** |
| `public_on_demand_cost` | double | List price, for savings reporting |
| `savings_plan_arn`, `reservation_arn` | varchar | Commitment that covered the line |
| `resource_tags_json` | varchar | Raw tags as JSON |
| `cost_category_business_unit`, `cost_category_environment` | varchar | AWS Cost Categories |
| `loaded_at` | timestamptz | When this month was loaded |

## fct_cost_daily

Daily rollup without ownership: day × account × service × resource × cost class.
Columns: `usage_date`, `billing_period`, `account_id`, `account_name`, `product_code`,
`resource_key` (`resource_id` or a placeholder), `resource_id`, `cost_class`, `line_item_count`,
`usage_amount`, `unblended_cost`, `net_unblended_cost`, `effective_cost`.

---

## Seeds (inputs people edit)

| Seed | 1 row = | Key columns |
| --- | --- | --- |
| `projects` | project | `project_id`, `project_name`, `owner_team`, `cost_center`, `is_shared` |
| `tag_project_map` | tag value | `tag_key`, `tag_value` → `project_id` |
| `account_default_project` | account × date range | `account_id`, `project_id`, `valid_from`, `valid_to` |
| `resource_ownership` | resource × date range (SCD2) | `resource_id`, `project_id`, `valid_from`, `valid_to`, `reason`, `source`, `changed_at` |
| `allocation_rules` | rule version | `rule_id`, `rule_version`, `step`, `pool_*` filters, `method`, `driver_metric`, `valid_from`, `valid_to` |
| `allocation_rule_targets` | rule version × target project | `rule_id`, `rule_version`, `project_id`, `pct` (fixed_pct only) |
| `usage_drivers` | day × metric × project | `usage_date`, `driver_metric`, `project_id`, `quantity` |

All date ranges are half-open `[valid_from, valid_to)`; a null `valid_to` means "still valid".
The snapshot `snap_resource_ownership` records every change to `resource_ownership` with `dbt_valid_from`,
so you can tell **when** an ownership fix was made, not only which dates it covers.
