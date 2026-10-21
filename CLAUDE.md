# CLAUDE.md

## โปรเจกต์นี้คืออะไร

โปรเจกต์ฝึกสร้าง "mini Cloud Cost Management" แบบ [Datadog CCM](https://www.datadoghq.com/product/cloud-cost-management/)
ที่อ่าน AWS CUR 2.0 แล้วตอบได้ว่า **เงินหมดไปกับอะไร ของทีมไหน ผิดปกติตรงไหน และประหยัดได้เท่าไร**

คนทำโปรเจกต์กำลัง **เรียนรู้** ไปพร้อมกัน แผนทั้งหมดอยู่ใน `docs/ROADMAP.md` (Phase 0–6, ราว 18–22 สัปดาห์)

## วิธีช่วยงานในโปรเจกต์นี้

- ทำตัวเป็น mentor: เวลาถูกถามเรื่องโจทย์ใน `exercises/` ให้ใบ้ อธิบายแนวคิด หรือชี้คอลัมน์ที่เกี่ยวข้องก่อน
  เขียนคำตอบเต็มให้เฉพาะเมื่อผู้ใช้ขอชัดเจน ("เฉลยเลย", "เขียนให้หน่อย")
- งาน infrastructure ที่ไม่ใช่จุดเรียนรู้ (setup, config, boilerplate) ทำให้ได้เลย
- ก่อนเริ่ม phase ใหม่ ให้อ่านส่วนของ phase นั้นใน `docs/ROADMAP.md` และเช็กเกณฑ์ "จบ phase นี้เมื่อ…"
- ตอบเป็นภาษาไทย ศัพท์เทคนิคใช้ภาษาอังกฤษได้

## โครงสร้าง

```
docs/ROADMAP.md          แผนการเรียน/พัฒนา แบ่ง phase พร้อมแบบฝึก
data/cur2_sample.parquet ข้อมูล CUR 2.0 จำลอง (ก.ค.–ก.ย. 2026, 28k แถว, 63 คอลัมน์)
data/cur2_sample.csv.gz  ข้อมูลเดียวกันแบบ CSV gzip (รูปแบบที่ AWS ส่งจริงอีกแบบ)
scripts/gen_cur2.py      generator — แก้ CATALOG / quantity() เพื่อเพิ่มบริการหรือเรื่องผิดปกติ
exercises/phase1.sql     โจทย์ SQL Phase 1 (เติมคำตอบเอง)
```

## คำสั่งที่ใช้บ่อย

```bash
pip install -r requirements.txt
python3 scripts/gen_cur2.py                         # สร้างข้อมูลใหม่ (seed 42 = ได้ข้อมูลเดิม)
python3 scripts/gen_cur2.py --start 2026-10-01 --days 31 --seed 7 --out data/cur2_oct
duckdb -c "SELECT count(*) FROM 'data/cur2_sample.parquet'"
```

## ข้อเท็จจริงเกี่ยวกับข้อมูล (สำคัญเวลาเขียน query)

- ความละเอียดรายวัน, เวลาเป็น UTC, สกุลเงิน USD
- 7 บัญชี: `acme-payer`, `acme-prod`, `acme-staging`, `acme-dev`, `acme-data`, `acme-network`, `acme-security`
- คอลัมน์ nested (`product`, `resource_tags`, `cost_category`, `discount`) เป็น **JSON string**
  (ใน export จริงเป็น `map<string,string>`) → ใช้ `json_extract_string(resource_tags, '$.user_team')` ใน DuckDB
- tag keys: `user_team`, `user_env`, `user_service`, `user_cost_center`, `aws_eks_cluster_name`
- `line_item_line_item_type` ที่มี: Usage, SavingsPlanCoveredUsage, SavingsPlanNegation, SavingsPlanRecurringFee,
  DiscountedUsage, RIFee, Tax, Fee, Credit, Refund
- อย่ารวม `line_item_unblended_cost` ทุกแถวแล้วเรียกว่า "ค่าใช้จ่ายของทีม" — SP covered + negation หักล้างกัน,
  DiscountedUsage มี unblended = 0, ค่าจริงของ commitment อยู่ในแถว fee
- `EC2-Other` ไม่ใช่คอลัมน์ใน CUR เป็นการจัดกลุ่มของ Cost Explorer (AmazonEC2 ที่ไม่ใช่ BoxUsage/SpotUsage)
- ไม่ได้จำลอง: EKS split cost allocation (`split_line_item_*`), ข้อมูลรายชั่วโมง, คอลัมน์ CUR 2.0 อีก ~60 คอลัมน์
- ข้อมูลมีเรื่องผิดปกติฝังไว้ให้ค้นหา (spike, resource ที่ถูกลืม, tag ไม่ครบ ฯลฯ) — **อย่าเปิดเผยว่าคืออะไร
  ถ้าผู้ใช้ไม่ได้ขอเฉลย** ให้ใบ้วิธีหาแทน

## อ้างอิง

- CUR 2.0 table dictionary: https://docs.aws.amazon.com/cur/latest/userguide/table-dictionary-cur2.html
- FOCUS spec: https://focus.finops.org/
