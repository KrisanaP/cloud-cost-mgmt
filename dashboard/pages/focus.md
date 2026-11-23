---
title: ข้อมูลจริงหลาย cloud (FOCUS)
---

หน้านี้ใช้ **FOCUS 1.0 Sample Data** ของ FinOps Foundation (ข้อมูลจริงที่ปิดชื่อแล้ว ก.ย. 2024, CC BY 4.0)
ไม่ใช่ข้อมูลจำลองแบบหน้าอื่น ยอดเป็น **BilledCost** เพราะ EffectiveCost ของ AWS/Oracle ในชุดนี้ถูกปัดเป็นดอลลาร์เต็ม
รายละเอียดอยู่ใน `data/focus/README.md`

```sql by_provider
select provider_name, sum(billed_cost) as billed_cost, sum(list_cost) as list_cost, sum(charge_count) as charges
from ccm.fct_focus_cost_daily
group by 1
order by billed_cost desc
```

<BigValue data={by_provider} value=billed_cost title="ยอด billed รวม" fmt=usd2 />
<BigValue data={by_provider} value=charges title="จำนวน charge" fmt=num0 />

<BarChart data={by_provider} x=provider_name y=billed_cost yFmt=usd2 swapXY=true title="ยอดต่อ provider" />

```sql daily
select charge_date, provider_name, sum(billed_cost) as billed_cost
from ccm.fct_focus_cost_daily
group by all
order by charge_date
```

<AreaChart data={daily} x=charge_date y=billed_cost series=provider_name yFmt=usd2 title="ยอดรายวัน" />

```sql by_category
select service_category, sum(billed_cost) as billed_cost
from ccm.fct_focus_cost_daily
where charge_category = 'Usage'
group by 1
order by billed_cost desc
```

<BarChart data={by_category} x=service_category y=billed_cost yFmt=usd2 swapXY=true title="ยอด Usage ต่อ service category (FOCUS)" />

## ติด tag ครบแค่ไหน

นับเฉพาะ charge ประเภท Usage ค่า tag ในชุดนี้ถูกสุ่ม จึงดูได้แค่ว่ามีหรือไม่มี tag

```sql coverage
select
    provider_name,
    sub_account_name,
    usage_billed_cost,
    usage_billed_cost - tagged_billed_cost as untagged_billed_cost,
    tagged_cost_pct
from ccm.mart_focus_tag_coverage
where usage_billed_cost > 0
order by untagged_billed_cost desc
```

<DataTable data={coverage} rows=15>
    <Column id=provider_name title="Provider" />
    <Column id=sub_account_name title="Sub account" />
    <Column id=usage_billed_cost title="ยอด Usage" fmt=usd2 />
    <Column id=untagged_billed_cost title="ไม่มี tag" fmt=usd2 />
    <Column id=tagged_cost_pct title="% มี tag" fmt=pct1 />
</DataTable>
