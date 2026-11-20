{{ config(materialized='table') }}
-- ส่วนแบ่งของแต่ละโปรเจกต์ต่อ pool line: 1 แถว = pool line × target project
--
-- วิธีหาร (method)
--   even                 แบ่งเท่ากัน (targets ใน allocation_rule_targets หรือทุกโปรเจกต์ที่รับได้)
--   fixed_pct            ตาม pct ใน allocation_rule_targets (ต้องรวม = 100)
--   proportional_direct  ตามต้นทุนของโปรเจกต์ในช่วงวันของบรรทัด
--                        ขั้น 1 ใช้ต้นทุนตรง ขั้น k ใช้ต้นทุนตรง + ส่วนที่ได้รับจากขั้นก่อนหน้า (step-down)
--   usage_driver         ตามปริมาณใช้จริงใน usage_drivers (เช่น vcpu_hours)
--
-- เศษ: หารเป็นหน่วยเล็กสุด 10^-precision ดอลลาร์ (var alloc_precision ค่าเริ่ม 6)
-- แล้วใช้ largest remainder ให้เศษตกที่โปรเจกต์ที่มีเศษมากสุด -> ผลรวมต่อบรรทัดตรงเป๊ะ
--
-- กฎห้ามวน: pool เป็นได้แค่โปรเจกต์ shared หรือ unattributed และ target ต้องไม่ใช่ทั้งสองแบบ
-- ส่วนที่หารแล้วจึงไม่มีทางถูกเลือกเป็น pool อีก (test assert_allocation_targets_valid)

{% set precision = var('alloc_precision', 6) %}
{% set max_step = var('alloc_max_step', 3) %}

with pools as (
    select * from {{ ref('int_alloc__pools') }}
),

eligible_projects as (
    select project_id
    from {{ ref('projects') }}
    where not is_shared and project_id <> 'unattributed'
),

targets as (
    select * from {{ ref('allocation_rule_targets') }}
),

rule_has_targets as (
    select distinct rule_id, rule_version from targets
),

direct_basis as (
    select * from {{ ref('int_alloc__direct_basis') }}
),

drivers as (
    select usage_date, driver_metric, project_id, sum(quantity) as quantity
    from {{ ref('usage_drivers') }}
    group by all
),

-- target ที่อนุญาตต่อ pool line: ถ้ากฎระบุ targets ใช้ตามนั้น ไม่งั้นใช้ทุกโปรเจกต์ที่รับได้
allowed as (
    select p.line_item_id, t.project_id, t.pct
    from pools p
    join targets t using (rule_id, rule_version)
    union all
    select p.line_item_id, e.project_id, null as pct
    from pools p
    cross join eligible_projects e
    where not exists (
        select 1 from rule_has_targets h
        where h.rule_id = p.rule_id and h.rule_version = p.rule_version
    )
),

{% for step in range(1, max_step + 1) %}
-- ===== ขั้น {{ step }} =====
basis_{{ step }} as (
    {% if step == 1 %}
    select usage_date, project_id, basis from direct_basis
    {% else %}
    select usage_date, project_id, sum(basis) as basis
    from (
        select usage_date, project_id, basis from basis_{{ step - 1 }}
        union all
        select usage_date, project_id, weight_amount as basis
        from received_{{ step - 1 }}
    )
    group by all
    {% endif %}
),

weights_{{ step }} as (
    select
        p.line_item_id,
        a.project_id,
        case p.method
            when 'even'      then 1.0
            when 'fixed_pct' then a.pct
            when 'proportional_direct' then (
                select sum(b.basis) from basis_{{ step }} b
                where b.project_id = a.project_id
                  and b.usage_date >= p.window_start and b.usage_date < p.window_end)
            when 'usage_driver' then (
                select sum(d.quantity) from drivers d
                where d.project_id = a.project_id
                  and d.driver_metric = p.driver_metric
                  and d.usage_date >= p.window_start and d.usage_date < p.window_end)
        end as weight
    from pools p
    join allowed a using (line_item_id)
    where p.step = {{ step }}
),

-- ส่วนที่โปรเจกต์ได้รับจากขั้นนี้ (กระจายเป็นรายวันตาม usage_date ของ pool line) ใช้เป็น basis ขั้นถัดไป
received_{{ step }} as (
    select usage_date, project_id, sum(amount) as weight_amount
    from (
        select p.usage_date, w.project_id,
               p.pool_cost * w.weight / sum(w.weight) over (partition by w.line_item_id) as amount
        from weights_{{ step }} w
        join pools p using (line_item_id)
        where w.weight > 0
    )
    group by all
),
{% endfor %}

all_weights as (
    {% for step in range(1, max_step + 1) %}
    select * from weights_{{ step }} where weight > 0
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
),

shares as (
    select
        w.line_item_id,
        w.project_id,
        w.weight / sum(w.weight) over (partition by w.line_item_id) as share
    from all_weights w
),

-- largest remainder บนหน่วยเล็กสุด
units as (
    select
        s.line_item_id,
        s.project_id,
        s.share,
        sign(p.pool_cost)                                              as sgn,
        round(abs(p.pool_cost) * pow(10, {{ precision }}))::hugeint     as total_units,
        abs(p.pool_cost) * pow(10, {{ precision }}) * s.share           as raw_units
    from shares s
    join pools p using (line_item_id)
),

floored as (
    select
        *,
        floor(raw_units)::hugeint                     as base_units,
        raw_units - floor(raw_units)                  as remainder
    from units
),

ranked as (
    select
        *,
        total_units - sum(base_units) over (partition by line_item_id)               as leftover,
        row_number() over (partition by line_item_id order by remainder desc, project_id) as rnk
    from floored
)

select
    line_item_id,
    project_id,
    share,
    sgn * (base_units + case when rnk <= leftover then 1 else 0 end) / pow(10, {{ precision }}) as allocated_cost
from ranked
