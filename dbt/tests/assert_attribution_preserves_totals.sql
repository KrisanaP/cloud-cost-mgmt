-- attribution ต้องไม่ทำให้แถวงอก/หาย และยอดไม่เปลี่ยน (เทียบต่อ billing period)
-- แค่ "ติดป้ายเจ้าของ" เท่านั้น เงินรวมทั้งบริษัทต้องเท่าเดิมทุกเซ็นต์
with before as (
    select billing_period, count(*) n, sum(effective_cost) eff, sum(unblended_cost) ub
    from {{ ref('fct_cost_line_item') }} group by 1
),
after as (
    select billing_period, count(*) n, sum(effective_cost) eff, sum(unblended_cost) ub
    from {{ ref('fct_cost_attributed') }} group by 1
),
monthly as (
    select billing_period, sum(line_item_count) n, sum(effective_cost) eff
    from {{ ref('fct_project_cost_monthly') }} group by 1
)
select b.*, a.n a_n, a.eff a_eff, m.n m_n, m.eff m_eff
from before b
left join after a using (billing_period)
left join monthly m using (billing_period)
where a.n is distinct from b.n
   or m.n is distinct from b.n
   or abs(coalesce(a.eff, 1e18) - b.eff) > 0.01
   or abs(coalesce(a.ub, 1e18) - b.ub) > 0.01
   or abs(coalesce(m.eff, 1e18) - b.eff) > 0.01
