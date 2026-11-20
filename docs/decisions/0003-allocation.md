# 0003 หาร shared cost ด้วยตารางกฎ

สถานะ: ใช้อยู่ (Phase 3)

## Pool คืออะไร

บรรทัดที่หลัง Phase 2 ตกอยู่ที่โปรเจกต์ **shared** (`eks-platform`, `shared-infra`) หรือ `unattributed`
แล้วเข้าตัวกรองของกฎใน `seeds/allocation_rules.csv` (ช่องว่าง = ไม่กรอง):
`pool_project_id`, `pool_cost_class`, `pool_product_code`, `pool_account_id` และช่วงวัน `[valid_from, valid_to)`

บรรทัดที่ไม่เข้ากฎไหนเลยคงอยู่ที่เจ้าของเดิม รวมถึงต้นทุนตรงที่ `unattributed` ซึ่งตั้งใจให้โผล่ในรายงาน
ไม่เอาไปหารกลบ เพราะนั่นคืองานที่ต้องตามหาเจ้าของ

## กฎตั้งต้น

| rule | pool | วิธี | ขั้น |
| --- | --- | --- | --- |
| eks | eks-platform | `usage_driver` vcpu_hours | 1 |
| network | shared-infra | `proportional_direct` | 1 |
| sp_unused | Savings Plan ที่ใช้ไม่หมด | `proportional_direct` | 1 |
| rds_ri_unused | RDS RI ที่ใช้ไม่หมด | `fixed_pct` payment-api 60 / ledger 40 | 1 |
| support | AWS Support | `proportional_direct` (ฐานรวมส่วนที่ได้จากขั้น 1) | 2 |
| tax | Tax | `proportional_direct` (ฐานรวมส่วนที่ได้จากขั้น 1) | 2 |
| credit | Credit/Refund | `even` | 2 |

ตัวเลข % และ driver เป็นสมมติฐาน แก้ได้ที่ seed (Phase 4 จะมีหน้า Streamlit ให้แก้)

## การตัดสินใจย่อย

- **ฐานหารตามช่วงของบรรทัด** ใช้ `[usage_start, usage_end)` บรรทัดรายวันใช้ฐานวันเดียว
  บรรทัดรายเดือน (support, tax, fee) ใช้ฐานทั้งเดือน ไม่ใช่แค่วันที่ 1 ที่บรรทัดนั้นลงวันไว้
- **Step-down** ขั้น k ใช้ฐาน = ต้นทุนตรง + ส่วนที่ได้รับจากขั้นก่อนหน้า (support/tax ตามยอดหลังหาร network/EKS)
- **ห้ามวน** pool ต้องเป็นโปรเจกต์ shared/unattributed และ target ต้องไม่ใช่ทั้งสองแบบ
  ส่วนที่หารแล้วจึงไม่มีทางกลับเข้า pool อีก ตรวจด้วย `assert_allocation_targets_valid`
- **เศษสตางค์** หารเป็นหน่วย 10^-6 ดอลลาร์ (var `alloc_precision`) แล้วใช้ largest remainder
  ผลรวมต่อบรรทัดตรงถึงหน่วยนั้น (unit test แสดง $10 ÷ 3 = 3.34 + 3.33 + 3.33 ที่ precision 2)
  ไม่ปัดถึงเซ็นต์ตรงๆ เพราะบิลจริงมีทศนิยมมากกว่า 2 ตำแหน่ง ปัดทีละบรรทัดหมื่นบรรทัดจะคลาดเป็นดอลลาร์
- **ไม่มีฐานหาร** (เช่น วันนั้นไม่มี driver) บรรทัดคงอยู่ที่เดิม `allocation_status = no_basis` ไม่หาย
- **1 บรรทัด 1 กฎ** ถ้าเข้าหลายขั้น ขั้นน้อยชนะ ถ้าเข้า 2 กฎในขั้นเดียวกัน test `assert_rules_do_not_collide` พัง

## usage_drivers

ปริมาณใช้จริงไม่อยู่ในบิล `seeds/usage_drivers.csv` จำลองด้วย `scripts/gen_usage_drivers.py`
ของจริงจะมาจาก CloudWatch Container Insights, OpenCost หรือ log ของ API gateway
