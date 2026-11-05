# Handoff: สิ่งที่คุยกันมาก่อนเริ่มโปรเจกต์

สรุปจากแชทใน Claude app (21–22 ต.ค. 2026) ก่อนย้ายมาทำใน Claude Code
อ่านไฟล์นี้คู่กับ `CLAUDE.md` และ `docs/ROADMAP.md`

> **อัปเดต 5 พ.ย. 2026: เปลี่ยนแผน** — ดูส่วน "แผนใหม่ (5 พ.ย. 2026)" ด้านล่างก่อน
> แผนเดิม (Phase 0–6 แบบมี API + frontend) ย้ายไปเก็บที่ `docs/archive/ROADMAP_v1.md`
> ส่วนอื่นของไฟล์นี้ยังเป็นบันทึกเดิม เก็บไว้เป็นประวัติและ research

## ใครทำอะไร

- **คนตั้งโจทย์** คือแฟนของคนทำ เป็นคนเริ่มแชท ขอ dataset และ roadmap
- **คนทำโปรเจกต์** (ผู้ใช้ใน session นี้) **มาจากสาย data** ถนัด SQL/Python
  แต่ "คืนวิชา frontend ให้อาจารย์ไปตั้งแต่เรียนจบ" แล้ว
- เป้าหมาย: ฝึกสร้าง Cloud Cost Management แบบ Datadog จาก AWS CUR 2.0 เพื่อเรียนรู้ ไม่ใช่ทำขาย

## ลำดับสิ่งที่เกิดขึ้น

1. ขอ dataset CUR 2.0 จำลอง → ได้ชุดแรกขนาดเล็ก (875 แถว, 1 เดือน) แล้วถูกแทนที่ด้วยชุดปัจจุบัน
2. ขอ roadmap ตั้งแต่ศึกษาจนถึงสร้าง software → เขียนเป็น doc (Phase 0–6, ~18–22 สัปดาห์)
   ฉบับเดียวกันอยู่ใน `docs/ROADMAP.md`
3. ขอให้ dataset มีบริการแบบ enterprise (ECS, EKS, RDS, S3, EC2-Other, AWS Backup, SNS, SQS ฯลฯ)
   → เขียน `scripts/gen_cur2.py` ใหม่ทั้งหมด ได้ข้อมูล 3 เดือน 7 บัญชี 50+ บริการ
   พร้อมฝัง "เรื่องผิดปกติ" 12 เรื่องไว้ให้ค้นหา
4. จัดเป็น repo นี้เพื่อย้ายมา Claude Code (มี git commit แรกแล้ว)
5. ถามเรื่อง open source ที่ลอกได้, OptScale ต่อ AWS ยังไง, ClickHouse คืออะไร (สรุปด้านล่าง)
6. คุยว่าส่วนที่ยากคือ data eng หรือ dashboard → สรุปว่า data eng ยากกว่า เพราะ "ผิดแล้วไม่มีใครรู้"

## การตัดสินใจที่ทำไปแล้ว

- ใช้ **CUR 2.0 เป็นแหล่งข้อมูลหลัก** ไม่ใช้ Cost Explorer API
  (API คิดเงินต่อ request, ข้อมูลระดับ resource ย้อนได้แค่ 14 วัน, ได้ยอดที่ aggregate แล้ว)
  Cost Explorer API อาจใช้ทีหลังเพื่อเทียบตัวเลขเท่านั้น
- เริ่มด้วย **DuckDB + Parquet** ค่อยพิจารณา ClickHouse เมื่อข้อมูลใหญ่หรือมีผู้ใช้หลายคน
- `ANSWER_KEY.md` (เฉลยเรื่องที่ซ่อนในข้อมูล) **ตั้งใจไม่ใส่ไว้ใน repo** และอยู่ใน `.gitignore`

## แผนใหม่ (5 พ.ย. 2026)

คนทำโปรเจกต์สรุปแผนของตัวเองกับ AI อีกห้อง (4 พ.ย.) แล้วตัดสินใจใช้แผนนั้นเป็นหลัก
แผนเดิมในไฟล์นี้เป็นของคนตั้งโจทย์ (สามี)

- **เป้าหมาย**: พอร์ตโฟลิโอสายดาต้า (อาจต่อยอดเป็นโปรดักต์) จากปัญหาจริงของสามี
  ซึ่งเป็น IT manager ดูแลคลาวด์ของบริษัทใหญ่ในไทย: ไม่รู้ว่าแต่ละโปรเจกต์ใช้เงินเท่าไร
  เพราะมี resource ใช้ร่วมกัน, และ tag ไม่มีผลย้อนหลัง
- **ไม่มีชั้น API** — dbt เขียนตารางรายงาน แดชบอร์ดอ่านตรง
- **แกนหลัก**: dbt-duckdb บน Parquet → tag ย้อนหลังแบบ SCD2 → กฎหาร shared cost
  (เท่ากัน / ตามสัดส่วน / ตามปริมาณใช้จริง) → test ว่ายอดหลังหาร = ยอดบิล
- **แสดงผล**: แดชบอร์ดสำเร็จรูป (Evidence หรือ Metabase ยังไม่ไฟนอล; roadmap แนะนำ Evidence เพราะทำบน iPad ได้)
  + Streamlit เขียนเอง 2 หน้า: ตั้งกฎการหาร, ตรวจย้อนกลับ
- **เวลา**: เสาร์อาทิตย์เต็มวัน, วันธรรมดา 1–2 ชม., ส่วนใหญ่ใช้ iPad/มือถือ → ทำงานผ่าน Claude Code บนเว็บหรือ Codespaces
- ข้อมูลจำลองเดิมยังใช้ต่อ แต่ต้องเพิ่ม seed เรื่องโปรเจกต์, ownership ที่เปลี่ยนกลางทาง และ usage driver
- ห้ามใช้บิลจริงของบริษัทสามีโดยไม่ได้รับอนุญาต

Phase ใหม่ (รายละเอียดใน `docs/ROADMAP.md`):
0 ตั้งเครื่องมือ → 1 staging + effective cost + กระทบยอด → 2 tag ย้อนหลัง SCD2
→ 3 หาร shared cost → 4 แดชบอร์ด + Streamlit 2 หน้า → 5 ทำเป็นพอร์ต → 6 ต่อยอด

### เรื่องที่ยังค้าง

- [ ] เลือก Evidence หรือ Metabase (ตัดสินใจตอนเริ่ม Phase 4 ก็ได้)
- [ ] push repo ขึ้น GitHub
- [ ] ถามสามี:
  - เรื่องหลักอีกเรื่องที่ยังจำไม่ได้คืออะไร
  - มุมมองไหนที่อยากเห็นแต่แดชบอร์ดของ AWS ทำไม่ได้
  - เครื่องมือที่เคยลอง แต่ละตัวขาดอะไร
  - ทุกวันนี้หาร shared cost ยังไง ใช้เวลาเดือนละกี่ชั่วโมง
  - ใครอ่านรายงาน เอาไปตัดสินใจเรื่องอะไร
  - มีค่าใช้จ่ายอื่นปนไหม (ไลเซนส์, AI API, ตัวแทนจำหน่าย, on-prem)
  - ใช้ Kubernetes cluster ร่วมกันหลายโปรเจกต์ไหม
  - มีกี่บัญชี กี่โปรเจกต์ บริการอะไรที่ใช้ร่วมกัน

### เรื่องค้างจากแผนเดิม (ปิดแล้ว)

- [x] ~~Phase 4 เปลี่ยนจาก React เป็น Streamlit~~ → แทนด้วยแดชบอร์ดสำเร็จรูป + Streamlit 2 หน้า
- [x] ~~ปรับ timeline~~ → roadmap ใหม่
- [x] ~~ปรับ `CLAUDE.md`~~ → ทำแล้ว 5 พ.ย.
- [ ] (ทางเลือก) `docs/REFERENCES.md` รวม open source ด้านล่าง
- [ ] (ทางเลือก) จำลอง EKS split cost allocation (`split_line_item_*`) ถ้าทำเรื่อง Kubernetes ใน Phase 6

## สิ่งที่รู้เกี่ยวกับ dataset

- `data/cur2_sample.parquet` 28,381 แถว, 63 คอลัมน์, 1 ก.ค. – 30 ก.ย. 2026, รายวัน, UTC, USD
- ยอดรวม (รวม tax/fee) ราว $36k / $38k / $41k ต่อเดือน
- ราคาเป็นค่าประมาณแถว ap-southeast-1 ไม่ใช่ราคาจริงเป๊ะ
- ต่างจาก CUR 2.0 จริง: คอลัมน์ nested เป็น JSON string (จริงเป็น `map<string,string>`),
  มีแค่ราว 60 จาก ~125 คอลัมน์, ไม่มีข้อมูลรายชั่วโมง, ไม่มี `split_line_item_*`
- เรื่องผิดปกติที่ซ่อนไว้ **อย่าเปิดเผยถ้าผู้ใช้ไม่ได้ขอเฉลย** — ประเภทกว้างๆ คือ:
  cost spike ชั่วคราว, ค่าใช้จ่ายที่พุ่งแล้วไม่ลง, resource ที่ถูกลืม, ค่าที่โตต่อเนื่อง,
  บริการใหม่ที่โผล่มากลางทาง, commitment ใช้ไม่เต็ม, tag ไม่ครบ/สะกดไม่ตรง,
  โอกาสประหยัดแบบ quick win, และ pattern วันหยุดที่ anomaly detector ไม่ควรฟ้อง
- generator: `python3 scripts/gen_cur2.py --start YYYY-MM-DD --days N --seed S --out data/<name>`
  แต่ "เรื่องผิดปกติ" ผูกกับวันที่ ก.ค.–ก.ย. 2026 ใน `quantity()` ถ้าเปลี่ยนช่วงวันจะไม่เกิด

## Research ที่ทำไปแล้ว

### Open source ที่ใช้อ้างอิงได้

| โปรเจกต์ | ใช้ทำอะไร | License |
|---|---|---|
| [Cloud Intelligence Dashboards (CID/CUDOS)](https://github.com/aws-solutions-library-samples/cloud-intelligence-dashboards-framework) | SQL สำหรับ amortized cost, SP/RI coverage — ใช้เป็น "เฉลย" เทียบตัวเลข Phase 1–2, 5 (UI เป็น QuickSight ลอกไม่ได้) | MIT-0 |
| [OptScale](https://github.com/hystax/optscale) | สถาปัตยกรรม FinOps platform ทั้งระบบ, กฎ recommendation (Phase 5–6) ใหญ่มาก อ่านเป็นตัวอย่าง ไม่ควรใช้เป็นฐาน | Apache-2.0 |
| [OpenCost](https://www.opencost.io/) (CNCF) | แบ่งค่า Kubernetes ลง namespace/pod (Phase 5 container cost) | Apache-2.0 |
| [FOCUS converters](https://github.com/finopsfoundation/focus_converters) | แปลง CUR → FOCUS (Phase 6) | — |
| OpenOps | FinOps automation แบบ no-code เน้น workflow ไม่ใช่ dashboard | Apache-2.0 |
| Komiser | บริการแม่ (Tailwarden) หยุดพัฒนาแล้ว ต้องเช็กสถานะ repo ก่อนใช้ | — |

### OptScale ต่อ AWS ยังไง (จาก [เอกสาร](https://hystax.com/documentation/optscale/e2e-guides/e2e-aws.html) + อ่านโค้ดจริง)

- **ค่าใช้จ่าย**: อ่าน CUR (2.0 หรือ legacy) จาก S3 ไม่ใช้ Cost Explorer API
  สร้าง export ให้อัตโนมัติได้เฉพาะ management/standalone account; import ทุกชั่วโมง, AWS อัปเดตไฟล์วันละครั้ง
- **Resource/metrics สำหรับ recommendation**: เรียก `ec2:Describe*`, `elasticloadbalancing:Describe*`,
  `cloudwatch:GetMetricData` แยกต่างหาก
- **Multi-account**: member ไม่มี export ของตัวเอง ต้องเพิ่มทีละ account, รองรับ AssumeRole
- **Pipeline** (`diworker/diworker/importers/base.py`, `importers/aws.py`):
  1. `rest_api` ตั้งเวลา → ส่ง task เข้า RabbitMQ exchange `billing-reports` → `diworker` ทำงาน
  2. ดาวน์โหลดไฟล์ CUR → แปลงคอลัมน์ CUR 2.0 กลับเป็นชื่อแบบ legacy → upsert ทุก line item ลง **MongoDB** (raw)
  3. ย่อเป็นต้นทุนต่อ resource ต่อวัน (ใช้ **BlendedCost** หารเฉลี่ยตามจำนวนวัน) ลง **ClickHouse** ตาราง `expenses`
     มีแค่ `cloud_account_id, resource_id, date, cost, sign` (metadata ของ resource แยกเก็บอีกที่)
  4. Restatement: ฝั่ง raw ลบตั้งแต่ `period_start` แล้ว import ใหม่; ฝั่ง ClickHouse ใช้
     `CollapsingMergeTree(sign)` — insert แถวยอดเก่า `sign=-1` + ยอดใหม่ `sign=+1`, query ด้วย `sum(cost*sign)`
  5. หลัง import: alerts, traffic tasks, RI/SP tasks (`risp`); recommendation อยู่ที่ `bumiworker`
- ข้อสังเกตที่คุยกันไว้: OptScale ใช้ BlendedCost ไม่ใช่ amortized → เห็นภาพ commitment ไม่ละเอียด
  เป็นโจทย์ให้ถกได้ว่าแบบไหนดีกว่าสำหรับโปรเจกต์นี้

### ClickHouse (สรุปสั้น)

- ฐานข้อมูล column-oriented สำหรับงาน OLAP aggregate ข้อมูลพันล้านแถวได้ระดับวินาที บีบอัดดีมาก
- UPDATE/DELETE ทีละแถวไม่ดี → ใช้ engine ตระกูล MergeTree
  (`ReplacingMergeTree`, `CollapsingMergeTree`, `SummingMergeTree`) จัดการแทน
- ใน roadmap เดิม (v1): DuckDB ใช้ Phase 1–2, ClickHouse ช่วงปลาย Phase 2 หรือ Phase 6, Postgres เก็บข้อมูล app
- ลองได้โดยไม่ต้องตั้ง server: `clickhouse local -q "... FROM file('data/cur2_sample.parquet') ..."`

## จุดเริ่มต้นที่แนะนำ

1. Phase 0 ใน `docs/ROADMAP.md`: push ขึ้น GitHub, `dbt init` ด้วย dbt-duckdb, ตั้ง CI
2. ระหว่างนั้นถามสามีตามรายการด้านบน
3. Phase 1: โมเดล staging ตัวแรก + test กระทบยอด
