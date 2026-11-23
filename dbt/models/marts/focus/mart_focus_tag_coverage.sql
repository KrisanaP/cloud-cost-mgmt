-- ข้อมูลจริงติด tag ครบแค่ไหน แยก provider × sub account
-- นับเฉพาะ charge ประเภท Usage เพราะ credit / tax / purchase ปกติไม่มี resource ให้ติด tag
-- ใช้เทียบกับ mart_attribution_coverage ของข้อมูลจำลอง

with usage as (
    select *
    from {{ ref('stg_focus__charges') }}
    where charge_category = 'Usage'
)

select
    provider_name,
    sub_account_id,
    any_value(sub_account_name)                                   as sub_account_name,
    count(*)                                                      as usage_charge_count,
    count(*) filter (where is_tagged)                             as tagged_charge_count,
    sum(billed_cost)                                              as usage_billed_cost,
    sum(case when is_tagged then billed_cost else 0 end)          as tagged_billed_cost,
    sum(case when is_tagged then billed_cost else 0 end)
        / nullif(sum(billed_cost), 0)                             as tagged_cost_pct,
    sum(case when tag_environment is not null then billed_cost else 0 end)
        / nullif(sum(billed_cost), 0)                             as env_tagged_cost_pct
from usage
group by provider_name, sub_account_id
