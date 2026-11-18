-- 1 แถว = 1 line item × 1 tag key
-- แปลง JSON เป็นแบบยาว (long) เพื่อให้ join / pivot / นับ coverage ได้ง่าย
-- normalize: ตัดช่องว่างหัวท้ายและทำเป็นตัวพิมพ์เล็ก ทั้ง key และ value
-- เก็บค่าเดิมไว้ใน tag_value_raw เพื่อดูย้อนได้ว่าก่อน normalize เป็นอะไร

with line_items as (
    select line_item_id, resource_tags_json
    from {{ ref('stg_cur__line_items') }}
    where resource_tags_json is not null
      and resource_tags_json not in ('', '{}')
),

exploded as (
    select
        line_item_id,
        unnest(json_keys(resource_tags_json)) as tag_key_raw,
        resource_tags_json
    from line_items
)

select
    line_item_id,
    lower(trim(tag_key_raw))                                         as tag_key,
    tag_key_raw,
    lower(trim(json_extract_string(resource_tags_json, '$."' || tag_key_raw || '"'))) as tag_value,
    json_extract_string(resource_tags_json, '$."' || tag_key_raw || '"')              as tag_value_raw
from exploded
where nullif(trim(json_extract_string(resource_tags_json, '$."' || tag_key_raw || '"')), '') is not null
