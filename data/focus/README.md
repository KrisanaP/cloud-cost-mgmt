# FOCUS 1.0 Sample Data (ข้อมูลจริงชุดที่สอง)

`focus_sample_100k.parquet` = 100,000 แถวจาก **FOCUS 1.0 Sample Data** ของ FinOps Foundation
แปลงจาก `focus_sample_100000.csv.gz` เป็น Parquet ด้วย `scripts/fetch_focus_sample.py` (ปัก commit `adbdd17`)
เนื้อหาไม่ถูกแก้ แค่ทำค่า `NULL` ให้เป็น null จริงและเก็บทุกคอลัมน์เป็นข้อความ

- ที่มา: https://github.com/FinOps-Open-Cost-and-Usage-Spec/FOCUS-Sample-Data
- License: [Creative Commons Attribution 4.0 (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)
  © FinOps Foundation / FOCUS project
- รายละเอียด: https://www.finops.org/insights/focus-sandbox/

## ในไฟล์มีอะไร

| Provider | แถว | หมายเหตุ |
|---|---:|---|
| AWS | 94,351 | ข้อมูลจริง (ปิดชื่อ) ก.ย. 2024 รายชั่วโมง 86 sub-account 50 บริการ |
| Microsoft | 4,964 | ตัวอย่างจาก Microsoft FinOps toolkit (demo account) |
| Oracle | 683 | ข้อมูลจริง (ปิดชื่อ) |
| Google Cloud | 2 | มีแค่ 2 แถวในชุด 100k |

## ข้อควรรู้ก่อนใช้

- **ใช้ `BilledCost` เป็นยอดหลัก** `EffectiveCost` ของ AWS และ Oracle ถูกปัดเป็นดอลลาร์เต็มตอนปิดชื่อ
  (ยอด effective รวมจึงต่ำกว่า billed มาก ไม่ใช่ส่วนลดจริง)
- **ค่า tag ถูกสุ่ม** (`application` มีหลายพันค่า) ดูได้ว่า resource ไหนมี/ไม่มี tag แต่เอาไปหาเจ้าของจริงไม่ได้
- ResourceId และชื่อบัญชีถูกสลับตัวอักษร, มีแค่เดือนเดียว จึงไม่ใช้กับ SCD2 / การหาร shared cost / restatement
- ค่าบางคอลัมน์สะกดไม่ตรง spec (เช่น `usage`, `Usage-based`) staging ทำให้เหมือนกันแล้ว

โมเดลที่ใช้ไฟล์นี้: `stg_focus__charges` → `fct_focus_cost_daily`, `mart_focus_tag_coverage`
คุมยอดด้วย `dbt/tests/assert_focus_totals_match_raw.sql`
