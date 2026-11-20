-- 1 แถว = 1 line item (grain เดิม ห้ามงอก ห้ามหาย) + เจ้าของโปรเจกต์
--
-- ลำดับการตัดสินเจ้าของ (อันแรกที่เจอชนะ):
--   1. override   : resource_ownership ที่ช่วงวันครอบ usage_date
--   2. tag        : tag ใน CUR (หลัง normalize) ที่ map ได้ใน tag_project_map
--   3. account_default : account_default_project ที่ช่วงวันครอบ usage_date
--   4. unattributed : ไม่ทิ้ง ต้องโผล่ในรายงาน
--
-- ช่วงวันใช้แบบ [valid_from, valid_to)  คือรวมวันเริ่ม ไม่รวมวันจบ, valid_to ว่าง = ยังมีผลอยู่
-- ช่วงวันซ้อนกันไม่ได้ (test assert_no_overlapping_ranges) ไม่งั้น 1 บรรทัดได้ 2 เจ้าของแล้วยอดเบิ้ล

with li as (
    select * from {{ ref('fct_cost_line_item') }}
),

ownership as (
    select * from {{ ref('resource_ownership') }}
),

account_default as (
    select * from {{ ref('account_default_project') }}
),

-- tag -> project ต่อ line item ถ้าเข้าหลาย key ให้ key ที่เรียงก่อนชนะ (ตอนนี้ map แค่ user_service)
tag_project as (
    select t.line_item_id, m.project_id, t.tag_key, t.tag_value
    from {{ ref('int_cost__line_item_tags') }} t
    join {{ ref('tag_project_map') }} m
      on m.tag_key = t.tag_key
     and m.tag_value = t.tag_value
    qualify row_number() over (partition by t.line_item_id order by t.tag_key) = 1
),

joined as (
    select
        li.*,
        o.project_id   as override_project_id,
        o.reason       as override_reason,
        tp.project_id  as tag_project_id,
        ad.project_id  as account_default_project_id
    from li
    left join ownership o
      on o.resource_id = li.resource_id
     and li.usage_date >= o.valid_from
     and (o.valid_to is null or li.usage_date < o.valid_to)
    left join tag_project tp
      on tp.line_item_id = li.line_item_id
    left join account_default ad
      on ad.account_id = li.account_id
     and li.usage_date >= ad.valid_from
     and (ad.valid_to is null or li.usage_date < ad.valid_to)
)

select
    * exclude (override_project_id, override_reason, tag_project_id, account_default_project_id),

    coalesce(override_project_id, tag_project_id, account_default_project_id, 'unattributed') as project_id,

    case
        when override_project_id is not null        then 'override'
        when tag_project_id is not null             then 'tag'
        when account_default_project_id is not null then 'account_default'
        else 'unattributed'
    end as attribution_source,

    tag_project_id,       -- เก็บไว้ดูว่า tag บอกอะไร แม้ override จะชนะ
    override_reason
from joined
