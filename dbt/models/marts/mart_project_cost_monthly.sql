-- 1 แถว = เดือน × โปรเจกต์ : direct / shared (ได้รับจากกฎ) / total และเทียบเดือนก่อน
-- แดชบอร์ดหน้า Overview อ่านตารางนี้
with base as (
    select
        billing_period,
        project_id,
        any_value(project_name) as project_name,
        any_value(owner_team)   as owner_team,
        sum(case when allocation_status = 'allocated' then 0 else allocated_cost end) as direct_cost,
        sum(case when allocation_status = 'allocated' then allocated_cost else 0 end) as shared_cost,
        sum(allocated_cost)                                                           as total_cost
    from {{ ref('fct_cost_allocated') }}
    group by 1, 2
)

select
    *,
    lag(total_cost) over (partition by project_id order by billing_period) as prev_total_cost,
    total_cost - lag(total_cost) over (partition by project_id order by billing_period) as mom_change,
    total_cost / nullif(lag(total_cost) over (partition by project_id order by billing_period), 0) - 1 as mom_change_pct
from base
