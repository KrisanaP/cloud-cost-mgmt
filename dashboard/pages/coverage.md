---
title: ต้นทุนที่ยังไม่มีเจ้าของ
---

หลังหาร shared cost แล้ว ยังมีต้นทุนตรงที่หาโปรเจกต์ไม่ได้ (ไม่มี tag ที่ map ได้, ไม่มี override, account ไม่มี default)
แก้ได้ 2 ทาง: ติด tag `user_service` ที่ resource หรือเพิ่มแถวใน `dbt/seeds/resource_ownership.csv`

```sql months
select distinct strftime(billing_period, '%Y-%m') as month
from ccm.mart_attribution_coverage
order by month desc
```

<Dropdown name=month data={months} value=month title="เดือน" />

```sql mix
select attribution_source, sum(total_cost) as cost
from ccm.attribution_mix
where strftime(billing_period, '%Y-%m') = '${inputs.month.value}'
group by 1
order by cost desc
```

<BarChart data={mix} x=attribution_source y=cost yFmt=usd0 swapXY=true
    title="ได้เจ้าของมาจากทางไหน (ก่อนหาร shared)" />

```sql by_account_service
select
    account_name,
    product_code,
    sum(unattributed_cost)            as unattributed_cost,
    max(total_cost_in_group)          as total_cost,
    sum(unattributed_cost) / nullif(max(total_cost_in_group), 0) as unattributed_pct
from ccm.mart_attribution_coverage
where strftime(billing_period, '%Y-%m') = '${inputs.month.value}'
group by all
order by unattributed_cost desc
```

## แยก account × service

<DataTable data={by_account_service} rows=15>
    <Column id=account_name title="Account" />
    <Column id=product_code title="Service" />
    <Column id=unattributed_cost title="ไม่มีเจ้าของ" fmt=usd2 />
    <Column id=total_cost title="ยอดทั้งกลุ่ม" fmt=usd2 />
    <Column id=unattributed_pct title="%" fmt=pct1 />
</DataTable>

## Resource ที่ควรไปแก้ก่อน (ก้อนใหญ่สุด)

```sql top_resources
select account_name, product_code, resource_key, sum(line_item_count) as line_items, sum(unattributed_cost) as unattributed_cost
from ccm.mart_attribution_coverage
where strftime(billing_period, '%Y-%m') = '${inputs.month.value}'
group by all
order by unattributed_cost desc
limit 25
```

<DataTable data={top_resources} rows=25>
    <Column id=resource_key title="Resource" />
    <Column id=account_name title="Account" />
    <Column id=product_code title="Service" />
    <Column id=line_items title="บรรทัด" />
    <Column id=unattributed_cost title="ไม่มีเจ้าของ" fmt=usd2 />
</DataTable>
