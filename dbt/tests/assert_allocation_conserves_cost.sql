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
         then round(max(line_effective_cost), {{ precision }})
         else max(line_effective_cost) end
    - sum(allocated_cost)) > 1e-9
