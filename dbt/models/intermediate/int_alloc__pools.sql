-- บรรทัดที่เป็น shared cost: 1 แถว = 1 line item ที่เข้ากฎ 1 กฎ
--
-- กฎ (allocation_rules) เลือกบรรทัดด้วยตัวกรอง 4 ช่อง ช่องว่าง = ไม่กรอง
--   pool_project_id / pool_cost_class / pool_product_code / pool_account_id
-- และต้องอยู่ในช่วงวันที่กฎมีผล [valid_from, valid_to)
-- ถ้าเข้าหลายกฎ ขั้น (step) น้อยกว่าชนะ; ขั้นเดียวกันห้ามเข้า 2 กฎ (test assert_rules_do_not_collide)
--
-- ช่วงวันที่ใช้หาร (basis window) = [usage_start, usage_end) ของบรรทัดนั้น
--   บรรทัดรายวัน -> ใช้ basis วันนั้นวันเดียว
--   บรรทัดรายเดือน (fee, support, tax) -> ใช้ basis ทั้งเดือน ไม่ใช่แค่วันที่ 1

with lines as (
    select * from {{ ref('fct_cost_attributed') }}
),

rules as (
    select * from {{ ref('allocation_rules') }}
),

matched as (
    select
        l.line_item_id,
        l.billing_period,
        l.usage_date,
        l.usage_start_at::date as window_start,
        greatest(l.usage_end_at::date, l.usage_start_at::date + 1) as window_end,
        l.project_id           as pool_project_id,
        l.effective_cost       as pool_cost,
        r.rule_id,
        r.rule_version,
        r.step,
        r.method,
        r.driver_metric,
        count(*) over (partition by l.line_item_id, r.step) as rules_matched_at_step
    from lines l
    join rules r
      on (r.pool_project_id   is null or r.pool_project_id   = l.project_id)
     and (r.pool_cost_class   is null or r.pool_cost_class   = l.cost_class)
     and (r.pool_product_code is null or r.pool_product_code = l.product_code)
     and (r.pool_account_id   is null or r.pool_account_id   = l.account_id)
     and l.usage_date >= r.valid_from
     and (r.valid_to is null or l.usage_date < r.valid_to)
)

select *
from matched
qualify row_number() over (partition by line_item_id order by step, rule_id) = 1
