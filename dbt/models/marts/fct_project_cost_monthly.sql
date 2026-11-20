-- 1 แถว = billing period × project × cost_class × attribution_source  (ตอบ "โปรเจกต์ X ใช้เท่าไร มาจากไหน")
select
    billing_period,
    project_id,
    project_name,
    owner_team,
    is_shared,
    cost_class,
    attribution_source,
    count(*)            as line_item_count,
    sum(effective_cost) as effective_cost,
    sum(unblended_cost) as unblended_cost
from {{ ref('fct_cost_attributed') }}
group by all
