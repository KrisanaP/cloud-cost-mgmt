-- marts ของแดชบอร์ดต้องรวมได้เท่ากับ fct_cost_allocated ทุกเดือน (ไม่มีอะไรหล่นระหว่างทาง)
with f as (select billing_period, sum(allocated_cost) t from {{ ref('fct_cost_allocated') }} group by 1),
m as (select billing_period, sum(total_cost) t, sum(direct_cost + shared_cost) t2 from {{ ref('mart_project_cost_monthly') }} group by 1),
d as (select billing_period, sum(cost) t from {{ ref('mart_project_cost_daily') }} group by 1),
a as (select billing_period, sum(allocated_cost) t from {{ ref('mart_allocation_audit') }} group by 1)
select f.billing_period, f.t, m.t, m.t2, d.t, a.t
from f join m using (billing_period) join d using (billing_period) join a using (billing_period)
where abs(f.t - m.t) > 0.01 or abs(f.t - m.t2) > 0.01 or abs(f.t - d.t) > 0.01 or abs(f.t - a.t) > 0.01
