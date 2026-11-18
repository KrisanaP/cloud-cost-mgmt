-- 1 แถว = วัน × account × service × resource × cost_class  (สำหรับรายงาน/แดชบอร์ด)
-- resource_id ว่าง (เช่น tax, fee) รวมเป็นกลุ่มเดียวกันในแต่ละวัน
-- คอลัมน์ resource_key ใช้แทน resource_id ที่เป็น null เพื่อให้เป็น key ได้

select
    usage_date,
    billing_period,
    account_id,
    account_name,
    product_code,
    coalesce(resource_id, '(no resource)')  as resource_key,
    resource_id,
    cost_class,
    count(*)                                as line_item_count,
    sum(usage_amount)                       as usage_amount,
    sum(unblended_cost)                     as unblended_cost,
    sum(net_unblended_cost)                 as net_unblended_cost,
    sum(effective_cost)                     as effective_cost
from {{ ref('fct_cost_line_item') }}
group by all
