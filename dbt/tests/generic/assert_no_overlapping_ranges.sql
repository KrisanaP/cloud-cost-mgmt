{#
  ช่วงวัน [valid_from, valid_to) ของ key เดียวกันต้องไม่ซ้อนกัน และ valid_to ต้องมากกว่า valid_from
  ถ้าซ้อน 1 บรรทัดบิลจะ join ได้ 2 เจ้าของ แล้วยอดเบิ้ล
#}
{% test assert_no_overlapping_ranges(model, key, from_col='valid_from', to_col='valid_to') %}
with r as (
    select row_number() over () as rid, {{ key }} as k, {{ from_col }} as f, {{ to_col }} as t
    from {{ model }}
)
select a.k, a.f as a_from, a.t as a_to, b.f as b_from, b.t as b_to, 'overlap' as problem
from r a
join r b
  on a.k = b.k
 and a.rid < b.rid
 and a.f < coalesce(b.t, date '9999-12-31')
 and b.f < coalesce(a.t, date '9999-12-31')
union all
select k, f, t, null, null, 'valid_to <= valid_from'
from r
where t is not null and t <= f
{% endtest %}
