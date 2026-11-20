# 0002 ระบุเจ้าของต้นทุนแบบย้อนหลังได้ (SCD2)

สถานะ: ใช้อยู่ (Phase 2)

## โปรเจกต์คืออะไร

ข้อมูลจำลองไม่มีแนวคิด "โปรเจกต์" จึงกำหนดว่า **1 โปรเจกต์ = 1 ค่าของ tag `user_service`** (12 โปรเจกต์)
บวก `unattributed` สำหรับบรรทัดที่หาเจ้าของไม่ได้ ทีมเจ้าของและ cost center อยู่ใน `seeds/projects.csv`
`eks-platform` กับ `shared-infra` ติด `is_shared = true` เพราะ Phase 3 จะหารต่อให้โปรเจกต์อื่น

ถ้าวันหน้าอยากให้โปรเจกต์ = ทีม หรือรวมหลาย service แก้แค่ `projects.csv` กับ `tag_project_map.csv`

## ลำดับการตัดสินเจ้าของ (`int_cost__attributed`)

1. **override** ใน `resource_ownership` ที่ช่วงวันครอบ `usage_date`
2. **tag** ใน CUR หลัง normalize (ตัวเล็ก + trim) แล้ว map ด้วย `tag_project_map`
3. **account_default** ตาม `account_default_project` (ตอนนี้มีแค่ acme-security และ acme-network ที่ใช้งานเดียวทั้งบัญชี)
4. **unattributed** ไม่ทิ้ง ต้องโผล่ในรายงาน (รวม tax, support, commitment ที่ใช้ไม่หมด ซึ่งจะหารใน Phase 3)

ทุกบรรทัดเก็บ `attribution_source` และ `tag_project_id` ไว้ เพื่อให้หน้าตรวจย้อนกลับบอกได้ว่าได้เจ้าของมาจากไหน
และ tag เดิมบอกว่าอะไร แม้ override จะชนะ

## ช่วงวัน

- ใช้แบบ `[valid_from, valid_to)` รวมวันเริ่ม ไม่รวมวันจบ `valid_to` ว่าง = ยังมีผล
  ช่วงต่อกันจึงเขียนได้ตรงๆ (ช่วงแรกจบ 1 ส.ค., ช่วงสองเริ่ม 1 ส.ค.) ไม่ต้องลบ 1 วัน
- ห้ามซ้อนกันต่อ resource (`assert_no_overlapping_ranges`) ไม่งั้น join แล้วแถวงอก ยอดเบิ้ล
- เทียบกับ `usage_date` ทีละวัน ย้ายเจ้าของกลางเดือนจึงแบ่งเดือนนั้นได้ถูกต้อง

## Tag มาช้า

ไม่เดา tag ย้อนหลังให้อัตโนมัติ แต่ให้คนเพิ่มแถวใน `resource_ownership` ด้วย `source = tag_backfill`
เพราะการเดาผิดเงียบๆ อันตรายกว่า และแถวใน seed ตรวจย้อนได้ว่าใครเป็นคนตัดสิน (Phase 6 มีไอเดียให้ AI เสนอแถวเหล่านี้)

## effective date กับ record date

- `valid_from/valid_to` = เป็นเจ้าของจริงตั้งแต่เมื่อไร
- `changed_by/changed_at` + snapshot `snap_resource_ownership` = เรารู้/แก้เมื่อไร
  ตอบได้ว่า "ทำไมตัวเลข ก.ค. วันนี้ไม่เท่ากับที่รายงานเมื่อวาน"

## ทำไม `fct_cost_attributed` เป็น table ไม่ใช่ incremental

แก้ ownership ย้อนหลังเมื่อไร ต้องคิดเจ้าของใหม่ทุกเดือน ถ้า incremental เดือนเก่าจะค้างเจ้าของเดิม
ต้นทุนดิบยัง incremental อยู่ที่ `fct_cost_line_item` ชั้นนี้แค่ join ทับ จึงยังเร็ว

## ตัวอย่างใน seed

แถวเดียวใน `resource_ownership.csv` เป็นตัวอย่าง: ตาราง DynamoDB `storefront-table0` ใน staging ย้ายไปทีม mobile
ตั้งแต่ 15 ส.ค. ต้นทุนก่อนวันนั้นยังเป็น storefront หลังจากนั้นเป็น mobile-bff ยอดรวมบริษัทไม่เปลี่ยน
สถานการณ์อื่น (ไม่มี tag, tag มาช้า, วันจบช่วง) อยู่ใน unit test `attribution_rules_and_date_ranges`
