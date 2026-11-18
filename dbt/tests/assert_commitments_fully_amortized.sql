-- ต่อ commitment (SP / RI) ต่อเดือน: ค่า fee ที่จ่าย = ส่วนที่ย้ายไปแถว usage + ส่วนที่ใช้ไม่หมด
-- ถ้าไม่เท่า แปลว่าเงิน commitment หายหรือถูกนับซ้ำระหว่างทาง
-- test ผ่าน = คืน 0 แถว

with fee as (
    select billing_period, coalesce(savings_plan_arn, reservation_arn) as commitment_arn,
           sum(unblended_cost) as fee_paid,
           sum(effective_cost) as unused
    from {{ ref('fct_cost_line_item') }}
    where line_item_type in ('SavingsPlanRecurringFee', 'RIFee')
    group by all
),

used as (
    select billing_period, coalesce(savings_plan_arn, reservation_arn) as commitment_arn,
           sum(effective_cost) as used
    from {{ ref('fct_cost_line_item') }}
    where line_item_type in ('SavingsPlanCoveredUsage', 'DiscountedUsage')
    group by all
)

select fee.*, used.used
from fee
left join used using (billing_period, commitment_arn)
where abs(fee.fee_paid - (coalesce(used.used, 0) + fee.unused)) > 0.01
