-- กันการหารวน: pool ของกฎต้องเป็นโปรเจกต์ shared หรือ unattributed เท่านั้น
-- และโปรเจกต์ที่รับส่วนแบ่ง (targets / ผลลัพธ์) ต้องไม่ใช่ shared และไม่ใช่ unattributed
-- ส่วนที่หารแล้วจึงไม่มีทางถูกเลือกเป็น pool ซ้ำในขั้นถัดไป
select 'pool project is not shared' as problem, r.rule_id, r.pool_project_id as project_id
from {{ ref('allocation_rules') }} r
join {{ ref('projects') }} p on p.project_id = r.pool_project_id
where not p.is_shared and p.project_id <> 'unattributed'

union all
select 'rule without pool_project_id', rule_id, null
from {{ ref('allocation_rules') }}
where pool_project_id is null

union all
select 'target is shared/unattributed', t.rule_id, t.project_id
from {{ ref('allocation_rule_targets') }} t
join {{ ref('projects') }} p using (project_id)
where p.is_shared or p.project_id = 'unattributed'

union all
select 'allocated to shared/unattributed', a.rule_id, a.project_id
from {{ ref('fct_cost_allocated') }} a
join {{ ref('projects') }} p using (project_id)
where a.allocation_status = 'allocated' and (p.is_shared or p.project_id = 'unattributed')
