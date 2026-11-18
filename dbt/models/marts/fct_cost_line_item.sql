{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key='billing_period',
        on_schema_change='append_new_columns'
    )
}}
-- 1 แถว = 1 line item  (ตารางหลักที่ phase 2–3 จะต่อยอด)
--
-- Restatement: AWS เขียนทับไฟล์ของเดือนปัจจุบันวันละหลายรอบ (และแก้เดือนที่ปิดแล้วได้)
-- จึงไม่ append แต่ใช้ delete+insert ตาม billing_period:
--   billing period ไหนมีอยู่ในไฟล์ที่อ่านรอบนี้ -> ลบของเดิมทั้งเดือนแล้วใส่ใหม่
--   billing period ไหนไม่อยู่ในไฟล์ -> คงไว้ตามเดิม
-- (ไม่ต้องมี where ตอน incremental เพราะทุกแถวในไฟล์ถือว่าเป็นฉบับล่าสุดของเดือนนั้น)

select
    line_item_id,
    billing_period,
    usage_date,
    usage_start_at,
    usage_end_at,
    bill_type,
    invoice_id,
    payer_account_id,
    account_id,
    account_name,
    line_item_type,
    cost_class,
    product_code,
    service_code,
    usage_type,
    operation,
    region,
    availability_zone,
    resource_id,
    instance_type,
    pricing_term,
    usage_amount,
    currency_code,

    unblended_cost,
    net_unblended_cost,
    effective_cost,
    public_on_demand_cost,

    savings_plan_arn,
    reservation_arn,
    resource_tags_json,
    cost_category_business_unit,
    cost_category_environment,

    current_timestamp as loaded_at
from {{ ref('int_cost__effective') }}
