-- 1 แถว = 1 charge จาก FOCUS 1.0 Sample Data (ข้อมูลจริงที่ปิดชื่อแล้ว ก.ย. 2024)
-- งานของ staging: cast type, ตั้งชื่อแบบ snake_case, ทำค่าที่สะกดไม่ตรงกันให้เหมือนกัน
--
-- ข้อควรรู้ของชุดนี้ (ดู data/focus/README.md):
--   * EffectiveCost ของ AWS และ Oracle ถูกปัดเป็นดอลลาร์เต็มตอนปิดชื่อ จึงใช้ billed_cost เป็นตัวหลัก
--   * tag ถูกสุ่มค่ามา ใช้ดูความครอบคลุมของ tag ได้ แต่อย่าใช้หาเจ้าของจริง

with source as (
    select * from {{ source('focus', 'focus_raw') }}
)

select
    -- keys / เวลา
    Id                                                          as charge_id,
    cast(BillingPeriodStart as timestamp)::date                 as billing_period,
    cast(ChargePeriodStart as timestamp)                        as charge_period_start_at,
    cast(ChargePeriodEnd as timestamp)                          as charge_period_end_at,
    cast(ChargePeriodStart as timestamp)::date                  as charge_date,

    -- ใครเป็นผู้ให้บริการ / บัญชี
    ProviderName                                                as provider_name,
    PublisherName                                               as publisher_name,
    InvoiceIssuerName                                           as invoice_issuer_name,
    BillingAccountId                                            as billing_account_id,
    BillingAccountName                                          as billing_account_name,
    SubAccountId                                                as sub_account_id,
    SubAccountName                                              as sub_account_name,

    -- charge (GCP เขียน usage ตัวเล็ก, AWS เขียน Usage-Based / Usage-based ปนกัน)
    case lower(ChargeCategory)
        when 'usage' then 'Usage' when 'purchase' then 'Purchase' when 'tax' then 'Tax'
        when 'credit' then 'Credit' when 'adjustment' then 'Adjustment'
        else ChargeCategory
    end                                                         as charge_category,
    ChargeClass                                                 as charge_class,
    case lower(ChargeFrequency)
        when 'usage-based' then 'Usage-Based' when 'one-time' then 'One-Time'
        when 'recurring' then 'Recurring'
        else ChargeFrequency
    end                                                         as charge_frequency,
    ChargeDescription                                           as charge_description,

    -- บริการ / resource
    coalesce(ServiceCategory, 'Other')                          as service_category,
    ServiceName                                                 as service_name,
    RegionId                                                    as region_id,
    AvailabilityZone                                            as availability_zone,
    ResourceId                                                  as resource_id,
    ResourceName                                                as resource_name,
    ResourceType                                                as resource_type,
    SkuId                                                       as sku_id,
    PricingCategory                                             as pricing_category,
    PricingUnit                                                 as pricing_unit,
    try_cast(PricingQuantity as double)                         as pricing_quantity,
    ConsumedUnit                                                as consumed_unit,
    try_cast(ConsumedQuantity as double)                        as consumed_quantity,

    -- commitment (RI / Savings Plan)
    CommitmentDiscountCategory                                  as commitment_discount_category,
    CommitmentDiscountType                                      as commitment_discount_type,
    CommitmentDiscountStatus                                    as commitment_discount_status,
    CommitmentDiscountId                                        as commitment_discount_id,

    -- เงิน (ไม่มี BillingCurrency 4 แถว ทั้งไฟล์เป็น USD จึงเติม USD)
    coalesce(BillingCurrency, 'USD')                            as billing_currency,
    cast(BilledCost as double)                                  as billed_cost,
    cast(EffectiveCost as double)                               as effective_cost,
    cast(ListCost as double)                                    as list_cost,
    cast(ContractedCost as double)                              as contracted_cost,

    -- tag (JSON) และ key ที่มีในชุดนี้
    Tags                                                        as tags,
    Tags is not null and Tags not in ('{}', '')                 as is_tagged,
    json_extract_string(Tags, '$.application')                  as tag_application,
    json_extract_string(Tags, '$.environment')                  as tag_environment,
    json_extract_string(Tags, '$.business_unit')                as tag_business_unit

from source
