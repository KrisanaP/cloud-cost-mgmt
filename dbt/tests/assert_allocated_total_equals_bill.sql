-- test สำคัญที่สุดของโปรเจกต์: ยอดหลังหารทั้งเดือน = ยอดบิลทั้งเดือน (จากไฟล์ดิบ) ถึงเซ็นต์
-- ไฟล์ดิบเทียบได้แค่เดือนที่อยู่ในไฟล์รอบนี้ (fct เป็น incremental)
-- ใช้ unblended ของไฟล์ดิบ เพราะ amortized ทั้งเดือน = unblended ทั้งเดือน (ดู decisions/0001)
with bill as (
    select cast(bill_billing_period_start_date as timestamp)::date as billing_period,
           sum(line_item_unblended_cost) as bill_total
    from {{ source('cur', 'cur2_raw') }}
    group by 1
),
allocated as (
    select billing_period, sum(allocated_cost) as allocated_total
    from {{ ref('fct_cost_allocated') }}
    group by 1
)
select *
from bill
left join allocated using (billing_period)
where abs(coalesce(allocated_total, 1e18) - bill_total) > 0.01
