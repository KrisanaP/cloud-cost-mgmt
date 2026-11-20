-- หน้าตรวจย้อนกลับ: 1 แถว = โปรเจกต์ × บรรทัดบิล
-- บอกว่าเงินก้อนนี้มาถึงโปรเจกต์ได้อย่างไร: ต้นทุนตรง (และได้เจ้าของจาก override/tag/account)
-- หรือหารมาจากกฎไหน เวอร์ชันไหน ได้กี่ %
select
    a.billing_period,
    a.usage_date,
    a.project_id,
    a.project_name,
    case when a.allocation_status = 'allocated' then 'shared' else 'direct' end as cost_type,
    a.allocated_cost,
    a.share_pct,
    a.rule_id,
    a.rule_version,
    r.rule_name,
    a.method,
    r.driver_metric,
    a.step,
    a.line_item_id,
    a.line_effective_cost,
    a.original_project_id,
    a.attribution_source,
    l.override_reason,
    l.tag_project_id,
    a.account_name,
    a.product_code,
    a.resource_id,
    a.line_item_type,
    a.cost_class
from {{ ref('fct_cost_allocated') }} a
left join {{ ref('fct_cost_attributed') }} l using (line_item_id)
left join {{ ref('allocation_rules') }} r
  on r.rule_id = a.rule_id and r.rule_version = a.rule_version
