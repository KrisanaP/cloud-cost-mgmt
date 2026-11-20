---
title: ต้นทุนคลาวด์ต่อโปรเจกต์
---

ยอดทุกตัวเป็น **effective (amortized) cost หลังหาร shared cost แล้ว** รวมทุกโปรเจกต์ = ยอดบิล AWS ของเดือนนั้น
กดชื่อโปรเจกต์ในตารางเพื่อดูว่าได้รับหารมาจากกฎอะไร

```sql months
select distinct strftime(billing_period, '%Y-%m') as month
from ccm.mart_project_cost_monthly
order by month desc
```

<Dropdown name=month data={months} value=month title="เดือน" />

```sql totals
select
    sum(total_cost)                                         as total_cost,
    sum(direct_cost)                                        as direct_cost,
    sum(shared_cost)                                        as shared_cost,
    sum(case when project_id = 'unattributed' then total_cost else 0 end) as unattributed_cost,
    sum(prev_total_cost)                                    as prev_total_cost
from ccm.mart_project_cost_monthly
where strftime(billing_period, '%Y-%m') = '${inputs.month.value}'
```

<BigValue data={totals} value=total_cost title="ยอดทั้งเดือน" fmt=usd0 comparison=prev_total_cost comparisonTitle="เดือนก่อน" comparisonFmt=usd0 />
<BigValue data={totals} value=direct_cost title="ต้นทุนตรง" fmt=usd0 />
<BigValue data={totals} value=shared_cost title="ได้รับหารมา" fmt=usd0 />
<BigValue data={totals} value=unattributed_cost title="ยังไม่มีเจ้าของ" fmt=usd0 />

## ต่อโปรเจกต์

```sql by_project
select
    project_id,
    project_name,
    owner_team,
    direct_cost,
    shared_cost,
    total_cost,
    mom_change_pct,
    '/projects/' || project_id as link
from ccm.mart_project_cost_monthly
where strftime(billing_period, '%Y-%m') = '${inputs.month.value}'
order by total_cost desc
```

```sql by_project_long
select project_id, 'ต้นทุนตรง' as cost_type, direct_cost as cost, total_cost
from ${by_project}
union all
select project_id, 'ได้รับหารมา', shared_cost, total_cost
from ${by_project}
order by total_cost desc
```

<BarChart
    data={by_project_long}
    x=project_id
    y=cost
    series=cost_type
    swapXY=true
    yFmt=usd0
    sort=false
    title="ต้นทุนตรง vs ได้รับหารมา"
/>

<DataTable data={by_project} link=link rows=20>
    <Column id=project_id title="โปรเจกต์" />
    <Column id=owner_team title="ทีม" />
    <Column id=direct_cost title="ต้นทุนตรง" fmt=usd2 />
    <Column id=shared_cost title="ได้รับหารมา" fmt=usd2 />
    <Column id=total_cost title="รวม" fmt=usd2 />
    <Column id=mom_change_pct title="เทียบเดือนก่อน" fmt=pct1 contentType=delta downIsGood=true />
</DataTable>

## แนวโน้มรายวัน

```sql daily
select usage_date, project_id, sum(cost) as cost
from ccm.mart_project_cost_daily
where project_id <> 'unattributed'
  and day(usage_date) <> 1   -- วันที่ 1 มีค่า support/tax รายเดือนลงไว้ จะเป็นยอดแหลมทุกเดือน
group by all
order by usage_date
```

<AreaChart data={daily} x=usage_date y=cost series=project_id yFmt=usd0
    title="ต้นทุนรายวัน (ไม่รวมวันที่ 1 ที่มีค่ารายเดือน)" />
