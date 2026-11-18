-- 1 แถว = 1 line item จากไฟล์ CUR
-- งานของชั้น staging: เลือกคอลัมน์ที่ใช้, cast type, ตั้งชื่อให้อ่านง่าย, แตก JSON ที่ใช้บ่อย
-- ยังไม่คิด logic ทางธุรกิจใดๆ (effective cost อยู่ที่ int_cost__effective)

with source as (
    select * from {{ source('cur', 'cur2_raw') }}
)

select
    -- keys
    identity_line_item_id                                       as line_item_id,
    cast(bill_billing_period_start_date as timestamp)::date     as billing_period,
    cast(line_item_usage_start_date as timestamp)               as usage_start_at,
    cast(line_item_usage_end_date as timestamp)                 as usage_end_at,
    cast(line_item_usage_start_date as timestamp)::date         as usage_date,

    -- บิลและบัญชี
    bill_bill_type                                              as bill_type,
    nullif(bill_invoice_id, '')                                 as invoice_id,
    bill_payer_account_id                                       as payer_account_id,
    bill_payer_account_name                                     as payer_account_name,
    line_item_usage_account_id                                  as account_id,
    line_item_usage_account_name                                as account_name,

    -- line item
    line_item_line_item_type                                    as line_item_type,
    line_item_product_code                                      as product_code,
    nullif(product_servicecode, '')                             as service_code,
    nullif(line_item_usage_type, '')                            as usage_type,
    nullif(line_item_operation, '')                             as operation,
    nullif(line_item_availability_zone, '')                     as availability_zone,
    nullif(product_region_code, '')                             as region,
    nullif(line_item_resource_id, '')                           as resource_id,
    line_item_line_item_description                             as description,
    nullif(product_product_family, '')                          as product_family,
    nullif(product_instance_type, '')                           as instance_type,
    nullif(pricing_term, '')                                    as pricing_term,
    nullif(pricing_unit, '')                                    as pricing_unit,
    line_item_currency_code                                     as currency_code,

    -- ปริมาณ
    line_item_usage_amount                                      as usage_amount,
    line_item_normalized_usage_amount                           as normalized_usage_amount,

    -- เงิน (ยังเป็นตัวเลขดิบจาก AWS)
    line_item_unblended_cost                                    as unblended_cost,
    line_item_net_unblended_cost                                as net_unblended_cost,
    line_item_blended_cost                                      as blended_cost,
    pricing_public_on_demand_cost                               as public_on_demand_cost,

    -- commitment: Savings Plans
    nullif(savings_plan_savings_plan_a_r_n, '')                 as savings_plan_arn,
    savings_plan_savings_plan_effective_cost                    as sp_effective_cost,
    savings_plan_total_commitment_to_date                       as sp_total_commitment,
    savings_plan_used_commitment                                as sp_used_commitment,

    -- commitment: Reserved Instances
    nullif(reservation_reservation_a_r_n, '')                   as reservation_arn,
    reservation_effective_cost                                  as ri_effective_cost,
    reservation_unused_recurring_fee                            as ri_unused_recurring_fee,
    -- CUR จริงมีคอลัมน์ unused amortized upfront ด้วย แต่ข้อมูลจำลองมีแต่ No Upfront จึงไม่มีคอลัมน์นี้

    -- JSON (ใน export จริงเป็น map) เก็บไว้ทั้งก้อน + แตก key ที่ใช้บ่อย
    resource_tags                                               as resource_tags_json,
    cost_category                                               as cost_category_json,
    json_extract_string(cost_category, '$.business_unit')       as cost_category_business_unit,
    json_extract_string(cost_category, '$.environment')         as cost_category_environment

from source
