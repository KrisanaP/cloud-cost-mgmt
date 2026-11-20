-- ต้นทุนที่ยังหาเจ้าของไม่ได้ (หลังหาร shared แล้ว ยังเหลือ unattributed เท่าไร)
-- 1 แถว = เดือน × account × service × resource  เรียงจากก้อนใหญ่ เพื่อรู้ว่าต้องไปแก้ tag ที่ไหนก่อน
-- total_cost_in_group = ยอดทั้งหมดของ เดือน × account × service ใช้คิด % coverage
with all_cost as (
    select billing_period, account_name, product_code,
           sum(allocated_cost) as total_cost_in_group
    from {{ ref('fct_cost_allocated') }}
    group by all
),

unattributed as (
    select
        billing_period,
        account_name,
        product_code,
        coalesce(resource_id, '(no resource)') as resource_key,
        count(*)                               as line_item_count,
        sum(allocated_cost)                    as unattributed_cost
    from {{ ref('fct_cost_allocated') }}
    where project_id = 'unattributed'
    group by all
)

select
    u.*,
    a.total_cost_in_group
from unattributed u
join all_cost a using (billing_period, account_name, product_code)
