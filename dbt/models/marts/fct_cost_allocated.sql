-- 1 แถว = line item × project  (ตารางที่หน้าตรวจย้อนกลับใช้)
--
-- บรรทัดที่ไม่ใช่ shared: 1 แถว เจ้าของเดิม allocated_cost = effective_cost, share_pct = 1
-- บรรทัด shared ที่หารได้: แตกเป็นหลายแถวตาม int_alloc__shares
-- บรรทัด shared ที่หาฐานหารไม่ได้ (เช่น ไม่มี driver วันนั้น): คงไว้ที่เจ้าของเดิม allocation_status = no_basis
--   ห้ามหาย ยอดรวมต้องเท่าบิลเสมอ

with lines as (
    select * from {{ ref('fct_cost_attributed') }}
),

pools as (
    select * from {{ ref('int_alloc__pools') }}
),

shares as (
    select * from {{ ref('int_alloc__shares') }}
),

allocated as (
    select
        l.line_item_id,
        s.project_id,
        s.allocated_cost,
        s.share                 as share_pct,
        p.rule_id,
        p.rule_version,
        p.step,
        p.method,
        true                    as is_shared,
        'allocated'             as allocation_status
    from lines l
    join pools p using (line_item_id)
    join shares s using (line_item_id)
),

not_allocated as (
    select
        l.line_item_id,
        l.project_id,
        l.effective_cost        as allocated_cost,
        1.0                     as share_pct,
        p.rule_id,
        p.rule_version,
        p.step,
        p.method,
        p.line_item_id is not null as is_shared,
        case when p.line_item_id is null then 'direct' else 'no_basis' end as allocation_status
    from lines l
    left join pools p using (line_item_id)
    where l.line_item_id not in (select line_item_id from shares)
)

select
    x.line_item_id,
    x.project_id,
    pr.project_name,
    pr.owner_team,
    x.allocated_cost,
    x.share_pct,
    x.is_shared,
    x.allocation_status,
    x.rule_id,
    x.rule_version,
    x.step,
    x.method,
    l.project_id            as original_project_id,
    l.attribution_source,
    l.effective_cost        as line_effective_cost,
    l.billing_period,
    l.usage_date,
    l.account_id,
    l.account_name,
    l.product_code,
    l.resource_id,
    l.line_item_type,
    l.cost_class
from (select * from allocated union all select * from not_allocated) x
join lines l using (line_item_id)
left join {{ ref('projects') }} pr on pr.project_id = x.project_id
