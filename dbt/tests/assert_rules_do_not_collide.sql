-- 1 บรรทัดเข้าได้แค่ 1 กฎต่อขั้น ถ้าเข้า 2 กฎในขั้นเดียวกัน แปลว่าตัวกรองของกฎทับกัน ต้องแก้ seed
select line_item_id, step, rules_matched_at_step
from {{ ref('int_alloc__pools') }}
where rules_matched_at_step > 1
