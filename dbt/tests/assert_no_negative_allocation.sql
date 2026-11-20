-- allocated_cost ติดลบได้เฉพาะเมื่อบรรทัดต้นทางติดลบ (credit/refund) และเครื่องหมายต้องตรงกับต้นทาง
select line_item_id, project_id, cost_class, line_effective_cost, allocated_cost
from {{ ref('fct_cost_allocated') }}
where (allocated_cost < 0 and cost_class <> 'credit')
   or (allocated_cost < 0 and line_effective_cost >= 0)
   or (allocated_cost > 0 and line_effective_cost < 0)
