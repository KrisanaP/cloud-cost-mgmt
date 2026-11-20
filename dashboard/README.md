# แดชบอร์ด (Evidence)

หน้าเว็บ static สร้างจาก Markdown + SQL อ่าน marts ที่ dbt สร้าง

| หน้า | ตอบคำถาม |
| --- | --- |
| `pages/index.md` | แต่ละโปรเจกต์ใช้เท่าไร (ต้นทุนตรง vs ได้รับหารมา) เทียบเดือนก่อน |
| `pages/projects/[project].md` | โปรเจกต์ X ได้รับหารมาจากกฎอะไร เท่าไร |
| `pages/coverage.md` | ต้นทุนที่ยังไม่มีเจ้าของ อยู่ account/service/resource ไหน |

## รันบนเครื่อง (Mac)

```bash
cd dbt && dbt build --profiles-dir . && cd ..   # สร้าง dbt/warehouse.duckdb
python3 scripts/export_marts.py                 # ส่งออก marts เป็น dashboard/data/*.parquet
cd dashboard
npm install
npm run sources                                 # Evidence อ่าน Parquet เข้าแคชของตัวเอง
npm run dev                                     # เปิด http://localhost:3000/cloud-cost-mgmt
npm run build                                   # สร้างเว็บ static ใน build/ (CI ทำให้)
```

ทำไมต้องส่งออกเป็น Parquet: Evidence ใช้ DuckDB รุ่นเก่ากว่า dbt เลยเปิดไฟล์ `.duckdb` ที่ dbt เขียนไม่ได้

ครั้งแรกที่รัน `npm run sources` Evidence จะโหลด DuckDB extension จาก `extensions.duckdb.org`
ต้องต่อเน็ตได้ (sandbox ของ Claude บล็อกโดเมนนี้ เลย build หน้าเว็บใน sandbox ไม่ได้ แต่ GitHub Actions และ Mac ได้)
