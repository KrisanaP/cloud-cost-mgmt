"""สร้าง dbt/seeds/usage_drivers.csv: ปริมาณการใช้ shared resource ต่อวันต่อโปรเจกต์

ของจริงไม่อยู่ในบิล ต้องมาจาก log / CloudWatch / OpenCost ไฟล์นี้จำลองตัวเลขแทน
ตอนนี้มี 1 metric: vcpu_hours บน EKS cluster กลาง (ใช้หาร eks-platform)

    python3 scripts/gen_usage_drivers.py               # ก.ค.–ก.ย. 2026, seed 42
"""
import argparse
import csv
import math
import random
from datetime import date, timedelta

ap = argparse.ArgumentParser()
ap.add_argument("--start", default="2026-07-01")
ap.add_argument("--days", type=int, default=92)
ap.add_argument("--seed", type=int, default=42)
ap.add_argument("--out", default="dbt/seeds/usage_drivers.csv")
args = ap.parse_args()

rng = random.Random(args.seed)
# vCPU-hours ต่อวันโดยประมาณ ของโปรเจกต์ที่รัน workload บน EKS กลาง
BASE = {"storefront": 220, "search-api": 140, "mobile-bff": 110, "payment-api": 90, "ml": 160}
GROWTH = {"ml": 0.004}  # บางโปรเจกต์โตขึ้นเรื่อยๆ ต่อวัน

start = date.fromisoformat(args.start)
rows = []
for d in range(args.days):
    day = start + timedelta(days=d)
    weekly = 0.85 if day.weekday() >= 5 else 1.0
    for project, base in BASE.items():
        trend = 1 + GROWTH.get(project, 0) * d
        noise = 1 + rng.uniform(-0.08, 0.08)
        qty = base * weekly * trend * noise
        rows.append([day.isoformat(), "vcpu_hours", project, round(qty, 2), "simulated"])

with open(args.out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["usage_date", "driver_metric", "project_id", "quantity", "source"])
    w.writerows(rows)
print(f"wrote {len(rows)} rows to {args.out}")
