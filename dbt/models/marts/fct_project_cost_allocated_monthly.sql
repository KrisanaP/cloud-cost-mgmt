-- 1 แถว = billing period × project × (ต้นทุนตรง / ส่วนที่ได้รับจากกฎ)  สำหรับแดชบอร์ด
select
    billing_period,
    project_id,
    project_name,
    owner_team,
    coalesce(rule_id, 'direct')                     as cost_source,
    sum(allocated_cost)                             as allocated_cost
from {{ ref('fct_cost_allocated') }}
group by all
