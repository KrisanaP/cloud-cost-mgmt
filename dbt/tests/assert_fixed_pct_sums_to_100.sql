-- กฎ fixed_pct ทุกเวอร์ชันต้องมี targets และ pct รวม = 100
select r.rule_id, r.rule_version, sum(t.pct) as total_pct
from {{ ref('allocation_rules') }} r
left join {{ ref('allocation_rule_targets') }} t using (rule_id, rule_version)
where r.method = 'fixed_pct'
group by 1, 2
having abs(coalesce(sum(t.pct), 0) - 100) > 1e-9
