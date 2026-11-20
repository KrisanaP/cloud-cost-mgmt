-- กระทบยอด: ต่อ billing period ยอดในไฟล์ดิบ = staging = fact = daily
-- ตรวจทั้ง unblended, net unblended, effective และจำนวนแถว ยอมให้ต่างไม่เกิน $0.01
-- effective: เพราะข้อมูลไม่มี upfront fee ยอด amortized ทั้งเดือนต้องเท่ายอด unblended พอดี
--   (ถ้าวันหน้ามี Partial/All Upfront ต้องบวก upfront ที่ amortize ของเดือนนั้นเข้าฝั่ง raw)
-- test ผ่าน = query นี้คืน 0 แถว
-- fact เป็น incremental อาจมีเดือนเก่าที่ไม่อยู่ในไฟล์รอบนี้ จึงเทียบเฉพาะเดือนที่อยู่ในไฟล์

{% set tolerance = 0.01 %}

with raw as (
    select
        cast(bill_billing_period_start_date as timestamp)::date as billing_period,
        count(*)                                  as n_rows,
        sum(line_item_unblended_cost)             as unblended,
        sum(line_item_net_unblended_cost)         as net_unblended
    from {{ source('cur', 'cur2_raw') }}
    group by 1
),

stg as (
    select billing_period, count(*) as n_rows, sum(unblended_cost) as unblended
    from {{ ref('stg_cur__line_items') }}
    group by 1
),

fct as (
    select
        billing_period,
        count(*)                as n_rows,
        sum(unblended_cost)     as unblended,
        sum(net_unblended_cost) as net_unblended,
        sum(effective_cost)     as effective
    from {{ ref('fct_cost_line_item') }}
    group by 1
),

daily as (
    select billing_period, sum(line_item_count) as n_rows, sum(unblended_cost) as unblended, sum(effective_cost) as effective
    from {{ ref('fct_cost_daily') }}
    group by 1
),

compared as (
    select
        raw.billing_period,
        raw.n_rows                as raw_rows,
        stg.n_rows                as stg_rows,
        fct.n_rows                as fct_rows,
        daily.n_rows              as daily_rows,
        raw.unblended             as raw_unblended,
        stg.unblended             as stg_unblended,
        fct.unblended             as fct_unblended,
        daily.unblended           as daily_unblended,
        raw.net_unblended         as raw_net_unblended,
        fct.net_unblended         as fct_net_unblended,
        fct.effective             as fct_effective,
        daily.effective           as daily_effective
    from raw
    left join stg   using (billing_period)
    left join fct   using (billing_period)
    left join daily using (billing_period)
)

select *
from compared
where stg_rows is distinct from raw_rows
   or fct_rows is distinct from raw_rows
   or daily_rows is distinct from raw_rows
   or abs(coalesce(stg_unblended, 1e18)   - raw_unblended)     > {{ tolerance }}
   or abs(coalesce(fct_unblended, 1e18)   - raw_unblended)     > {{ tolerance }}
   or abs(coalesce(daily_unblended, 1e18) - raw_unblended)     > {{ tolerance }}
   or abs(coalesce(fct_net_unblended, 1e18) - raw_net_unblended) > {{ tolerance }}
   or abs(coalesce(fct_effective, 1e18)   - raw_unblended)     > {{ tolerance }}
   or abs(coalesce(daily_effective, 1e18) - raw_unblended)     > {{ tolerance }}
