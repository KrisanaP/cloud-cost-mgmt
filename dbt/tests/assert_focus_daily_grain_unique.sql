-- fct_focus_cost_daily ต้องมี 1 แถวต่อ grain เท่านั้น (คืน 0 แถว = ผ่าน)
select provider_name, charge_date, sub_account_id, service_category, service_name, charge_category, count(*) as n
from {{ ref('fct_focus_cost_daily') }}
group by all
having count(*) > 1
