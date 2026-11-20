-- ฐานของการหารแบบ proportional_direct ขั้นแรก: ต้นทุนตรงของโปรเจกต์ที่รับส่วนแบ่งได้ ต่อวัน
-- รับส่วนแบ่งได้ = ไม่ใช่โปรเจกต์ shared และไม่ใช่ unattributed (กันการหารวนกลับเข้า pool)
-- ไม่นับบรรทัดที่เป็น pool เอง และนับเฉพาะ cost_class = direct
select
    l.usage_date,
    l.project_id,
    sum(l.effective_cost) as basis
from {{ ref('fct_cost_attributed') }} l
join {{ ref('projects') }} p using (project_id)
where not p.is_shared
  and l.project_id <> 'unattributed'
  and l.cost_class = 'direct'
  and l.line_item_id not in (select line_item_id from {{ ref('int_alloc__pools') }})
group by all
having sum(l.effective_cost) > 0
