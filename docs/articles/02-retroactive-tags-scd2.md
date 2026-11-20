# Tag ไม่มีผลย้อนหลัง: แก้ด้วย SCD2 ใน dbt

*ร่าง · ตอนที่ 2 จาก 3*

AWS cost allocation tag มีผลตั้งแต่วันที่ติด ไม่ย้อนหลัง ถ้าทีมเพิ่งติด tag เดือน ก.ย. ต้นทุน ก.ค.–ส.ค. ของ resource นั้นจะไม่มีเจ้าของไปตลอด
และถ้า resource ย้ายทีมกลางเดือน tag ก็บอกได้แค่เจ้าของ ณ ตอนนี้

## แยก "ใครเป็นเจ้าของ" ออกจากบิล

แทนที่จะเชื่อ tag อย่างเดียว ใช้ลำดับการตัดสิน 4 ชั้น:

1. **override** ในตาราง `resource_ownership` ที่ช่วงวันครอบวันใช้งาน
2. **tag** ใน CUR (normalize ตัวเล็ก + ตัดช่องว่าง) แล้ว map เป็นโปรเจกต์
3. **ค่า default ของ account** สำหรับบัญชีที่ทำงานเดียว
4. **unattributed** ไม่ทิ้ง ต้องโผล่ในรายงาน

ทุกบรรทัดเก็บ `attribution_source` ไว้ เพื่อให้ตอบได้เสมอว่าได้เจ้าของมาจากไหน

## SCD2: effective date กับ record date

`resource_ownership` เป็นตาราง Slowly Changing Dimension type 2:

```
resource_id, project_id, valid_from, valid_to, source, changed_by, changed_at, reason
```

- `valid_from / valid_to` = เป็นเจ้าของจริงตั้งแต่เมื่อไร (effective date) ใช้ช่วงแบบ `[from, to)` รวมวันเริ่ม ไม่รวมวันจบ
- `changed_at` + `dbt snapshot` = เรารู้/แก้เมื่อไร (record date)

สองอย่างนี้ต่างกัน และต้องมีทั้งคู่ถึงจะตอบคำถามแบบ "ทำไมตัวเลข ก.ค. วันนี้ไม่เท่ากับที่รายงานเมื่อวาน" ได้

## เพิ่ม 1 บรรทัด แล้วประวัติเปลี่ยนตาม

ตัวอย่างใน repo: ตาราง DynamoDB ของทีม storefront ย้ายไปทีม mobile ตั้งแต่ 15 ส.ค.
เพิ่มบรรทัดเดียวใน seed แล้ว `dbt build`:

- ก.ค. ยังเป็นของ storefront ทั้งหมด
- ส.ค. แบ่งที่วันที่ 15 พอดี
- ก.ย. เป็นของ mobile ทั้งหมด
- ยอดรวมทั้งบริษัทไม่เปลี่ยนแม้แต่เซ็นต์

ตาราง attribution จึงเป็น `table` ที่คิดใหม่ทุกรอบ ไม่ใช่ incremental เพราะการแก้ย้อนหลังต้องมีผลทุกเดือน
(ต้นทุนดิบยัง incremental อยู่ ชั้นนี้แค่ join ทับ)

## Test ที่กันไม่ให้ยอดเบิ้ล

join แบบช่วงวันอันตราย ถ้าช่วงซ้อนกัน 1 บรรทัดบิลจะได้ 2 เจ้าของแล้วยอดเบิ้ล
- generic test `assert_no_overlapping_ranges` ต่อ resource
- จำนวนแถวและยอดเงินก่อน/หลัง attribution ต้องเท่ากันทุกเดือน
- unit test ของ dbt จำลอง: ย้ายเจ้าของกลางเดือน, ไม่มี tag, tag มาช้า, วันจบช่วงไม่นับ, tag สะกดตัวใหญ่มีช่องว่าง

โค้ด: `dbt/models/intermediate/int_cost__attributed.sql` · เหตุผล: `docs/decisions/0002-attribution.md`
