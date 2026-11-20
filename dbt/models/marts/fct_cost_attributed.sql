-- 1 แถว = 1 line item พร้อม project_id และ attribution_source
--
-- ทำไมเป็น table ไม่ใช่ incremental: แก้ seed ownership ย้อนหลังเมื่อไร ต้องคิดเจ้าของใหม่ "ทุกเดือน"
-- ถ้า incremental จะคิดใหม่แค่เดือนที่โหลดรอบนี้ เดือนเก่าจะค้างเจ้าของเดิม
-- (ต้นทุนดิบยัง incremental อยู่ที่ fct_cost_line_item ส่วนนี้แค่ join ทับ ข้อมูลหลักแสน-ล้านแถวยังเร็ว)

select
    a.*,
    p.project_name,
    p.owner_team,
    p.cost_center,
    p.is_shared
from {{ ref('int_cost__attributed') }} a
left join {{ ref('projects') }} p using (project_id)
