# effective cost: ทำไมบิล AWS มีหลายตัวเลข และควรใช้ตัวไหนคิดต้นทุนโปรเจกต์

*ร่าง · ตอนที่ 1 จาก 3*

ลองถามว่า "เดือนที่แล้วทีมเราใช้ AWS ไปเท่าไร" แล้วไปเปิด Cost and Usage Report (CUR) จะเจอคอลัมน์เงินหลายตัว:
`unblended_cost`, `blended_cost`, `net_unblended_cost`, `savings_plan_effective_cost`, `reservation_effective_cost` …
ถ้าเลือกผิดตั้งแต่ตรงนี้ ทุกอย่างหลังจากนั้นผิดหมด

## กับดักของ unblended

`unblended_cost` คือเงินที่ AWS เรียกเก็บในแต่ละบรรทัด ดูเหมือนตรงไปตรงมา แต่พอบริษัทซื้อ Savings Plan หรือ Reserved Instance:

- บรรทัด usage ที่ SP ครอบคลุม (`SavingsPlanCoveredUsage`) มีค่า on-demand และมีบรรทัด `SavingsPlanNegation` มาหักล้างจนเหลือ 0
- บรรทัด usage ที่ RI ครอบคลุม (`DiscountedUsage`) มี unblended = 0 ตั้งแต่แรก
- เงินจริงไปกองอยู่ในบรรทัด fee รายเดือน (`SavingsPlanRecurringFee`, `RIFee`) ของบัญชีที่ซื้อ

ผลคือทีมที่ใช้ commitment หนักๆ ดูเหมือนใช้ฟรี ส่วนบัญชีที่ซื้อดูแพงเกินจริง

## effective (amortized) cost

แนวคิดคือย้ายเงิน commitment ไปอยู่กับบรรทัดที่ใช้มันจริง:

| line item type | effective cost |
| --- | --- |
| Usage | unblended |
| SavingsPlanCoveredUsage | `savings_plan_effective_cost` |
| SavingsPlanNegation | 0 |
| SavingsPlanRecurringFee | commitment ทั้งหมด − ส่วนที่ใช้ไป = **ส่วนที่ใช้ไม่หมด** |
| DiscountedUsage | `reservation_effective_cost` |
| RIFee | ค่า RI ของชั่วโมงที่ไม่ได้ใช้ |
| Tax / Fee / Credit / Refund | unblended |

ส่วนที่ใช้ไม่หมดไม่ได้หายไป แต่แยกออกมาเป็น `cost_class = commitment_unused` เพื่อไปหารต่อทีหลัง

## พิสูจน์ด้วย test

เพราะข้อมูลนี้ไม่มี upfront ยอด effective ทั้งเดือนต้องเท่ายอด unblended ทั้งเดือนพอดี
นี่คือ test กระทบยอดที่ง่ายและทรงพลังที่สุด (`assert_totals_match_raw`):
ไฟล์ดิบ = staging = fact = mart ทุก billing period ทั้ง unblended, net และ effective ยอมให้ต่างไม่เกิน $0.01

อีก test ตรวจทีละ commitment ว่า fee ที่จ่าย = ส่วนที่ย้ายไปแถว usage + ส่วนที่ใช้ไม่หมด
ถ้าสูตรผิดแม้แต่บรรทัดเดียว test จะชี้ว่า SP หรือ RI ตัวไหน เดือนไหน

## Restatement

AWS เขียนทับไฟล์ของเดือนปัจจุบันวันละหลายรอบ ถ้า append จะได้ต้นทุนซ้ำ
`fct_cost_line_item` เลยเป็น incremental แบบ `delete+insert` ตาม billing period
และมีสคริปต์จำลอง: generate เดือน ก.ย. ใหม่ด้วย seed อื่น รันซ้ำ แล้วตรวจว่ายอดไม่เบิ้ล และเดือนอื่นไม่ถูกแตะ

โค้ด: `dbt/models/intermediate/int_cost__effective.sql` · เหตุผล: `docs/decisions/0001-effective-cost.md`
