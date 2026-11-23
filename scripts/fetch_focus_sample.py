"""ดาวน์โหลด FOCUS 1.0 Sample Data (FinOps Foundation, CC BY 4.0) แล้วแปลงเป็น Parquet

ข้อมูลจริงที่ปิดชื่อแล้ว เดือน ก.ย. 2024 (AWS, Azure, OCI, GCP) ใช้เป็นข้อมูลชุดที่สองคู่กับ CUR จำลอง
ไฟล์ผลลัพธ์ data/focus/focus_sample_100k.parquet ถูก commit ไว้แล้ว รันสคริปต์นี้เมื่ออยากสร้างใหม่เท่านั้น

    python3 scripts/fetch_focus_sample.py

ที่มา: https://github.com/FinOps-Open-Cost-and-Usage-Spec/FOCUS-Sample-Data (ดู data/focus/README.md)
"""
import os
import tempfile
import urllib.request

import duckdb

# ปักไว้ที่ commit เดียว เพื่อให้ได้ข้อมูลเดิมทุกครั้ง
COMMIT = "adbdd17a132984d6e8583c149c236d2199c3f5bc"
URL = (
    "https://raw.githubusercontent.com/FinOps-Open-Cost-and-Usage-Spec/"
    f"FOCUS-Sample-Data/{COMMIT}/FOCUS-1.0/focus_sample_100000.csv.gz"
)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "focus", "focus_sample_100k.parquet")

with tempfile.TemporaryDirectory() as tmp:
    src = os.path.join(tmp, "focus.csv.gz")
    print(f"downloading {URL}")
    urllib.request.urlretrieve(URL, src)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    con = duckdb.connect()
    # ไฟล์ต้นทางเขียนค่าว่างเป็นคำว่า NULL; อ่านทุกคอลัมน์เป็นข้อความแล้วให้ dbt staging cast เอง
    con.execute(
        f"""
        copy (
            select * from read_csv('{src}', header = true, all_varchar = true,
                                   nullstr = ['NULL', ''])
        ) to '{OUT}' (format parquet, compression zstd)
        """
    )
    n = con.execute(f"select count(*) from '{OUT}'").fetchone()[0]
    print(f"{n} rows -> {os.path.relpath(OUT, ROOT)}")
