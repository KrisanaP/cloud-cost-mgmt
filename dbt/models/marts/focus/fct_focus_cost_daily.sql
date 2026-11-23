-- FOCUS sample รวมเป็นรายวัน
-- grain: provider × sub account × service × charge category × วัน
-- ยอดหลักคือ billed_cost (effective_cost ของ AWS/Oracle ในชุดนี้ถูกปัดเป็นดอลลาร์เต็ม)

select
    provider_name,
    billing_period,
    charge_date,
    sub_account_id,
    any_value(sub_account_name)                       as sub_account_name,
    service_category,
    coalesce(service_name, '(none)')                  as service_name,
    charge_category,
    count(*)                                          as charge_count,
    sum(billed_cost)                                  as billed_cost,
    sum(effective_cost)                               as effective_cost,
    sum(list_cost)                                    as list_cost,
    sum(case when is_tagged then billed_cost else 0 end) as tagged_billed_cost
from {{ ref('stg_focus__charges') }}
group by provider_name, billing_period, charge_date, sub_account_id,
         service_category, coalesce(service_name, '(none)'), charge_category
