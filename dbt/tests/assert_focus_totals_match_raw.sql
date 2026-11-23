-- กระทบยอด FOCUS: ต่อ provider ยอดในไฟล์ดิบ = staging = fct_focus_cost_daily
-- ตรวจจำนวนแถว, billed, effective, list ยอมให้ต่างไม่เกิน $0.01
-- และ mart_focus_tag_coverage ต้องรวมได้เท่ายอด Usage ของ staging
-- test ผ่าน = query นี้คืน 0 แถว

{% set tolerance = 0.01 %}

with raw as (
    select
        ProviderName                                   as provider_name,
        count(*)                                       as n_rows,
        sum(cast(BilledCost as double))                as billed,
        sum(cast(EffectiveCost as double))             as effective,
        sum(cast(ListCost as double))                  as list
    from {{ source('focus', 'focus_raw') }}
    group by 1
),

stg as (
    select provider_name, count(*) as n_rows, sum(billed_cost) as billed,
           sum(effective_cost) as effective, sum(list_cost) as list,
           sum(billed_cost) filter (where charge_category = 'Usage') as usage_billed
    from {{ ref('stg_focus__charges') }}
    group by 1
),

fct as (
    select provider_name, sum(charge_count) as n_rows, sum(billed_cost) as billed,
           sum(effective_cost) as effective, sum(list_cost) as list
    from {{ ref('fct_focus_cost_daily') }}
    group by 1
),

cov as (
    select provider_name, sum(usage_billed_cost) as usage_billed
    from {{ ref('mart_focus_tag_coverage') }}
    group by 1
)

select raw.*, stg.billed as stg_billed, fct.billed as fct_billed, fct.n_rows as fct_rows
from raw
left join stg using (provider_name)
left join fct using (provider_name)
left join cov using (provider_name)
where stg.n_rows is distinct from raw.n_rows
   or fct.n_rows is distinct from raw.n_rows
   or abs(coalesce(stg.billed, 1e18)    - raw.billed)    > {{ tolerance }}
   or abs(coalesce(fct.billed, 1e18)    - raw.billed)    > {{ tolerance }}
   or abs(coalesce(fct.effective, 1e18) - coalesce(raw.effective, 0)) > {{ tolerance }}
   or abs(coalesce(fct.list, 1e18)      - coalesce(raw.list, 0))      > {{ tolerance }}
   or abs(coalesce(cov.usage_billed, 0) - coalesce(stg.usage_billed, 0)) > {{ tolerance }}
