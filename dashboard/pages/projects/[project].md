---
title: รายละเอียดโปรเจกต์
---

```sql project_info
select * from ccm.projects where project_id = '${params.project}'
```

# {params.project}

ทีม **{project_info[0]?.owner_team ?? '-'}** · cost center {project_info[0]?.cost_center ?? '-'}

```sql months
select distinct strftime(billing_period, '%Y-%m') as month
from ccm.mart_project_cost_monthly
order by month desc
```

<Dropdown name=month data={months} value=month title="เดือน" />

```sql summary
select direct_cost, shared_cost, total_cost, prev_total_cost
from ccm.mart_project_cost_monthly
where project_id = '${params.project}'
  and strftime(billing_period, '%Y-%m') = '${inputs.month.value}'
```

<BigValue data={summary} value=total_cost title="รวม" fmt=usd2 comparison=prev_total_cost comparisonTitle="เดือนก่อน" comparisonFmt=usd2 />
<BigValue data={summary} value=direct_cost title="ต้นทุนตรง" fmt=usd2 />
<BigValue data={summary} value=shared_cost title="ได้รับหารมา" fmt=usd2 />

## ได้รับหารมาจากกฎอะไร

```sql shared
select rule_id, rule_name, method, sum(allocated_cost) as allocated_cost
from ccm.shared_by_rule
where project_id = '${params.project}'
  and strftime(billing_period, '%Y-%m') = '${inputs.month.value}'
group by all
order by allocated_cost desc
```

<DataTable data={shared}>
    <Column id=rule_id title="กฎ" />
    <Column id=rule_name title="คำอธิบาย" />
    <Column id=method title="วิธีหาร" />
    <Column id=allocated_cost title="ได้รับ" fmt=usd2 />
</DataTable>

ดูบรรทัดบิลต้นทางและ % ที่ได้ในแต่ละบรรทัด ได้ที่ Streamlit หน้าตรวจย้อนกลับ

## ต้นทุนรายเดือน

```sql monthly
select strftime(billing_period, '%Y-%m') as month, 'ต้นทุนตรง' as cost_type, direct_cost as cost
from ccm.mart_project_cost_monthly where project_id = '${params.project}'
union all
select strftime(billing_period, '%Y-%m'), 'ได้รับหารมา', shared_cost
from ccm.mart_project_cost_monthly where project_id = '${params.project}'
order by 1
```

<BarChart data={monthly} x=month y=cost series=cost_type yFmt=usd0 />

## รายวัน

```sql daily
select usage_date, cost_type, cost
from ccm.mart_project_cost_daily
where project_id = '${params.project}'
order by usage_date
```

<BarChart data={daily} x=usage_date y=cost series=cost_type yFmt=usd0
    title="รายวัน (วันที่ 1 ของเดือนมีค่ารายเดือนรวมอยู่)" />
