-- grain ของ fct_cost_daily ต้องไม่ซ้ำ
select usage_date, account_id, product_code, resource_key, cost_class, count(*) as n
from {{ ref('fct_cost_daily') }}
group by all
having count(*) > 1
