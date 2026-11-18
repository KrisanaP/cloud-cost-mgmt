-- 1 แถว = 1 line item (grain เดียวกับ staging ไม่ตัดแถวทิ้ง เพื่อให้กระทบยอด unblended ได้ครบ)
-- คิด effective cost (= amortized cost) ต่อบรรทัด และจัด cost_class
-- เหตุผลที่เลือก effective cost: docs/decisions/0001-effective-cost.md
--
-- กฎ (ตรงกับสูตร amortized ของ AWS Cost Explorer / CUDOS):
--   Usage                    -> unblended_cost              (on-demand จ่ายตามจริง)
--   SavingsPlanCoveredUsage  -> sp_effective_cost           (ส่วนของ commitment ที่ใช้กับบรรทัดนี้)
--   SavingsPlanNegation      -> 0                           (ตัวหักล้าง on-demand ไม่ใช่ต้นทุนจริง)
--   SavingsPlanRecurringFee  -> total - used commitment     (เหลือแต่ส่วนที่ "ใช้ไม่หมด")
--   DiscountedUsage          -> ri_effective_cost           (ส่วนของ RI ที่ใช้กับบรรทัดนี้)
--   RIFee                    -> ri_unused_recurring_fee     (เหลือแต่ชั่วโมง RI ที่ไม่ได้ใช้)
--   Tax / Fee / Credit / Refund -> unblended_cost
--
-- ผลที่ได้: ยอด effective ทั้ง billing period = ยอด unblended (เพราะไม่มี upfront)
-- แต่ย้ายเงิน commitment จากแถว fee ไปอยู่ที่แถว usage ที่ใช้มันจริง -> หารให้ทีมได้

with li as (
    select * from {{ ref('stg_cur__line_items') }}
)

select
    li.*,

    case line_item_type
        when 'Usage'                   then unblended_cost
        when 'SavingsPlanCoveredUsage' then sp_effective_cost
        when 'SavingsPlanNegation'     then 0
        when 'SavingsPlanRecurringFee' then sp_total_commitment - sp_used_commitment
        when 'DiscountedUsage'         then ri_effective_cost
        when 'RIFee'                   then ri_unused_recurring_fee
        else unblended_cost
    end as effective_cost,

    case
        when line_item_type in ('Usage', 'SavingsPlanCoveredUsage', 'DiscountedUsage') then 'direct'
        when line_item_type = 'SavingsPlanNegation'                then 'commitment_offset'
        when line_item_type in ('SavingsPlanRecurringFee', 'RIFee') then 'commitment_unused'
        when line_item_type = 'Tax'                                then 'tax'
        when line_item_type = 'Fee' and product_code like 'AWSSupport%' then 'support'
        when line_item_type in ('Credit', 'Refund')                then 'credit'
        else 'fee'
    end as cost_class

from li
