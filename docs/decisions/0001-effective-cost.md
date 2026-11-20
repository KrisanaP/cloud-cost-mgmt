# 0001 ใช้ effective (amortized) cost เป็นฐานคิดต้นทุนให้โปรเจกต์

สถานะ: ใช้อยู่ (Phase 1)

## ปัญหา

CUR มีตัวเลขเงินหลายแบบ และถ้าเลือกผิด การหารต้นทุนใน Phase 3 จะผิดตามหมด

| แบบ | คืออะไร | ปัญหาถ้าใช้หารให้ทีม |
| --- | --- | --- |
| unblended | เงินที่ถูกเรียกเก็บตามจริงในแต่ละบรรทัด | ค่า SP/RI ไปกองอยู่ที่แถว fee ของบัญชีที่ซื้อ ทีมที่ใช้ RI จริงเห็นต้นทุน = 0 (DiscountedUsage), ส่วน SP covered + negation หักล้างกันเป็น 0 |
| blended | เฉลี่ยราคาใน consolidated billing | เป็นค่าเฉลี่ยข้ามบัญชี ไม่ตรงกับอะไรเลย AWS เองก็ไม่แนะนำ |
| net unblended | unblended หลังหักส่วนลด (EDP ฯลฯ) | ปัญหาเดียวกับ unblended แค่สุทธิกว่า |
| **effective (amortized)** | กระจายค่า commitment ไปให้บรรทัด usage ที่ใช้มันจริง | ส่วนที่ซื้อแล้วใช้ไม่หมดยังต้องมีคนรับ (แยกเป็น `commitment_unused`) |

## ตัดสินใจ

ใช้ `effective_cost` ตามสูตร amortized ของ AWS (แบบเดียวกับ Cost Explorer และ CUDOS)

| line_item_type | effective_cost | cost_class |
| --- | --- | --- |
| Usage | `unblended_cost` | direct |
| SavingsPlanCoveredUsage | `savings_plan_savings_plan_effective_cost` | direct |
| SavingsPlanNegation | 0 | commitment_offset |
| SavingsPlanRecurringFee | `total_commitment_to_date - used_commitment` | commitment_unused |
| DiscountedUsage | `reservation_effective_cost` | direct |
| RIFee | `reservation_unused_recurring_fee` | commitment_unused |
| Tax | `unblended_cost` | tax |
| Fee (AWSSupport*) | `unblended_cost` | support |
| Fee (อื่นๆ) | `unblended_cost` | fee |
| Credit, Refund | `unblended_cost` | credit |

## ผลที่ตามมา

- ยอด effective ทั้งเดือน = ยอด unblended ทั้งเดือน (ข้อมูลนี้ไม่มี upfront) ใช้เป็น test กระทบยอดได้ตรงๆ
- ต่อ commitment ต่อเดือน: fee ที่จ่าย = ส่วนที่ย้ายไปแถว usage + ส่วนที่ใช้ไม่หมด (`assert_commitments_fully_amortized`)
- ไม่ตัดแถว negation ทิ้ง (effective = 0) เพื่อให้ยอด unblended ใน fact ยังกระทบกับไฟล์ดิบได้
- `commitment_unused`, `tax`, `support`, `credit` ยังไม่มีเจ้าของ จะไปหารใน Phase 3 ด้วยกฎ shared cost
- ถ้าวันหน้ามี RI/SP แบบ Partial/All Upfront ต้องเพิ่ม amortized upfront เข้าไปในสูตร และในฝั่ง raw ของ test กระทบยอด
