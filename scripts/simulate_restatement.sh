#!/usr/bin/env bash
# จำลอง restatement: AWS เขียนทับไฟล์เดือน ก.ย. ด้วยตัวเลขใหม่
# 1) build ปกติจากไฟล์ 3 เดือน
# 2) generate ก.ย. ใหม่ด้วย seed อื่น แล้ว build อีกรอบโดยชี้ไปไฟล์นั้นอย่างเดียว
# 3) ตรวจว่า ก.ย. ถูกแทนที่ทั้งเดือน (ไม่ซ้ำ) และ ก.ค./ส.ค. ยังอยู่ครบ
# รันจาก root ของ repo:  bash scripts/simulate_restatement.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
export DBT_DUCKDB_PATH="$TMP/restatement.duckdb"

python3 "$ROOT/scripts/gen_cur2.py" --start 2026-09-01 --days 30 --seed 7 --out "$TMP/cur2_sep_restated" > /dev/null

cd "$ROOT/dbt"
dbt build --profiles-dir . --quiet
dbt build --profiles-dir . --quiet --vars "{cur_path: '$TMP/cur2_sep_restated.parquet'}"

python3 - "$DBT_DUCKDB_PATH" "$ROOT/data/cur2_sample.parquet" "$TMP/cur2_sep_restated.parquet" <<'PY'
import sys, duckdb
db, original, restated = sys.argv[1:]
c = duckdb.connect(db, read_only=True)
q = """select cast(bill_billing_period_start_date as timestamp)::date p, count(*) n, round(sum(line_item_unblended_cost), 2) c
       from read_parquet('{}') group by 1"""
expected = {p: (n, c) for p, n, c in c.execute(q.format(original)).fetchall()}
expected.update({p: (n, c) for p, n, c in c.execute(q.format(restated)).fetchall()})
actual = {p: (n, c) for p, n, c in c.execute(
    "select billing_period, count(*), round(sum(unblended_cost), 2) from fct_cost_line_item group by 1").fetchall()}
for p in sorted(expected):
    print(p, "expected", expected[p], "actual", actual.get(p))
assert actual == expected, "restatement ผิด: ยอดใน fct_cost_line_item ไม่ตรงกับไฟล์ฉบับล่าสุดของแต่ละเดือน"
print("OK: ก.ย. ถูกแทนที่ทั้งเดือน ก.ค./ส.ค. ยังอยู่ครบ ไม่มีแถวซ้ำ")
PY
rm -rf "$TMP"
