-- 1 แถว = วัน × โปรเจกต์ × direct/shared สำหรับกราฟแนวโน้ม
-- บรรทัดรายเดือน (support, tax, fee) ลงวันที่ 1 ของเดือน ตามที่ AWS บันทึก
select
    usage_date,
    billing_period,
    project_id,
    any_value(project_name) as project_name,
    case when allocation_status = 'allocated' then 'shared' else 'direct' end as cost_type,
    sum(allocated_cost) as cost
from {{ ref('fct_cost_allocated') }}
group by 1, 2, 3, 5
