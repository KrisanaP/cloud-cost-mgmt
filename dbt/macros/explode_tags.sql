{#
  แปลง JSON ของ tag เป็นแบบยาว: 1 แถว = 1 line item × 1 tag key
  normalize: ตัดช่องว่างหัวท้าย + ตัวพิมพ์เล็ก ทั้ง key และ value, ค่าว่างถูกตัดทิ้ง
  ใช้ทั้งใน staging (ไฟล์รอบนี้) และ intermediate (ทุกเดือนที่อยู่ใน fct_cost_line_item)
#}
{% macro explode_tags(relation, id_col='line_item_id', json_col='resource_tags_json') %}
with src as (
    select {{ id_col }} as line_item_id, {{ json_col }} as tags_json
    from {{ relation }}
    where {{ json_col }} is not null
      and {{ json_col }} not in ('', '{}')
),

exploded as (
    select line_item_id, tags_json, unnest(json_keys(tags_json)) as tag_key_raw
    from src
),

valued as (
    select
        line_item_id,
        tag_key_raw,
        json_extract_string(tags_json, '$."' || tag_key_raw || '"') as tag_value_raw
    from exploded
)

select
    line_item_id,
    lower(trim(tag_key_raw))   as tag_key,
    tag_key_raw,
    lower(trim(tag_value_raw)) as tag_value,
    tag_value_raw
from valued
where nullif(trim(tag_value_raw), '') is not null
{% endmacro %}
