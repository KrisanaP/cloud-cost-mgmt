-- ต่อ line item (และจึงต่อวัน ต่อก้อน): ยอดหลังหาร = ยอดก่อนหาร
-- หารในหน่วย 10^-alloc_precision แล้ว largest remainder จึงต้องตรงถึงหน่วยนั้น (เผื่อ float นิดเดียว)
{% set precision = var('alloc_precision', 6) %}
select
    line_item_id,
    max(line_effective_cost) as before_cost,
    sum(allocated_cost)      as after_cost
from {{ ref('fct_cost_allocated') }}
group by 1
-- บรรทัดที่หาร: ต้องเท่ายอดเดิมที่ปัดถึง precision; บรรทัดที่ไม่หาร: ต้องเท่ายอดเดิมเป๊ะ
having abs(
    case when bool_or(allocation_status = 'allocated')
         -- ปัดแบบเดียวกับ int_alloc__shares (คูณเป็นหน่วยก่อนแล้ว round) ไม่ใช้ round(x, n)
         -- เพราะ DuckDB 2.0 เปลี่ยนวิธีปัด round(double, n) ที่ค่ากึ่งกลาง ทำให้ต่างกัน 1 หน่วย
         then sign(max(line_effective_cost))
              * round(abs(max(line_effective_cost)) * pow(10, {{ precision }})) / pow(10, {{ precision }})
         else max(line_effective_cost) end
    - sum(allocated_cost)) > 1e-9
