"""ส่งออกตารางที่แดชบอร์ดใช้จาก dbt/warehouse.duckdb เป็น Parquet ใน dashboard/data/

ทำไมไม่ให้ Evidence อ่านไฟล์ .duckdb ตรงๆ: Evidence ใช้ DuckDB รุ่นเก่ากว่า dbt
เปิดไฟล์ฐานข้อมูลรุ่นใหม่ไม่ได้ แต่ Parquet อ่านได้ทุกรุ่น

    python3 scripts/export_marts.py        # รันหลัง dbt build (จาก root ของ repo)
"""
import os
import sys

import duckdb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get("DBT_DUCKDB_PATH", os.path.join(ROOT, "dbt", "warehouse.duckdb"))
OUT = os.path.join(ROOT, "dashboard", "data")
TABLES = [
    "mart_project_cost_monthly",
    "mart_project_cost_daily",
    "mart_attribution_coverage",
    "mart_allocation_audit",
    "projects",
    "fct_focus_cost_daily",
    "mart_focus_tag_coverage",
]

if not os.path.exists(DB):
    sys.exit(f"ไม่เจอ {DB} ให้รัน dbt build ก่อน")

os.makedirs(OUT, exist_ok=True)
con = duckdb.connect(DB, read_only=True)
for t in TABLES:
    path = os.path.join(OUT, f"{t}.parquet")
    con.execute(f"copy (select * from {t}) to '{path}' (format parquet)")
    n = con.execute(f"select count(*) from {t}").fetchone()[0]
    print(f"{t:32s} {n:>7d} rows -> dashboard/data/{t}.parquet")
