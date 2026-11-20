"""ของที่ทั้ง 2 หน้าใช้ร่วมกัน: path, อ่าน DuckDB, อ่าน/เขียน seed, ตรวจกฎ, รัน dbt"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DBT_DIR = ROOT / "dbt"
SEEDS = DBT_DIR / "seeds"
DB_PATH = Path(os.environ.get("DBT_DUCKDB_PATH", DBT_DIR / "warehouse.duckdb"))

RULES_CSV = SEEDS / "allocation_rules.csv"
TARGETS_CSV = SEEDS / "allocation_rule_targets.csv"
PROJECTS_CSV = SEEDS / "projects.csv"

METHODS = ["even", "fixed_pct", "proportional_direct", "usage_driver"]
RULE_COLUMNS = [
    "rule_id", "rule_version", "rule_name", "step",
    "pool_project_id", "pool_cost_class", "pool_product_code", "pool_account_id",
    "method", "driver_metric", "valid_from", "valid_to", "changed_by", "changed_at",
]
TARGET_COLUMNS = ["rule_id", "rule_version", "project_id", "pct"]
ALLOCATION_SELECTOR = "allocation_rules+ allocation_rule_targets+"
# path ไฟล์ดิบแบบ absolute เพราะตอน preview dbt รันจากสำเนาในโฟลเดอร์ชั่วคราว
CUR_PATH = os.environ.get("CUR_PATH", str(ROOT / "data" / "cur2_sample.parquet"))


# ---------- อ่านข้อมูล ----------

def query(sql: str, params: list | None = None, db_path: Path | None = None) -> pd.DataFrame:
    """อ่านอย่างเดียว เปิด/ปิดทุกครั้ง เพื่อไม่ล็อกไฟล์ตอน dbt เขียน"""
    con = duckdb.connect(str(db_path or DB_PATH), read_only=True)
    try:
        return con.execute(sql, params or []).df()
    finally:
        con.close()


def load_rules() -> pd.DataFrame:
    df = pd.read_csv(RULES_CSV, dtype=str, keep_default_na=False)
    return df.reindex(columns=RULE_COLUMNS, fill_value="")


def load_targets() -> pd.DataFrame:
    df = pd.read_csv(TARGETS_CSV, dtype=str, keep_default_na=False)
    return df.reindex(columns=TARGET_COLUMNS, fill_value="")


def load_projects() -> pd.DataFrame:
    df = pd.read_csv(PROJECTS_CSV, dtype=str, keep_default_na=False)
    df["is_shared"] = df["is_shared"].str.lower() == "true"
    return df


def save_seeds(rules: pd.DataFrame, targets: pd.DataFrame, seeds_dir: Path = SEEDS) -> None:
    clean(rules, RULE_COLUMNS).to_csv(seeds_dir / "allocation_rules.csv", index=False)
    clean(targets, TARGET_COLUMNS).to_csv(seeds_dir / "allocation_rule_targets.csv", index=False)


def clean(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.reindex(columns=columns).fillna("").astype(str)
    out = out.apply(lambda c: c.str.strip())
    return out[(out != "").any(axis=1)]  # ตัดแถวว่างที่ data_editor เพิ่มมา


# ---------- ตรวจกฎก่อนบันทึก (ตรงกับ dbt tests) ----------

def validate(rules: pd.DataFrame, targets: pd.DataFrame, projects: pd.DataFrame) -> list[str]:
    """คืนรายการปัญหา (ภาษาไทย) ว่างเปล่า = บันทึกได้"""
    rules = clean(rules, RULE_COLUMNS)
    targets = clean(targets, TARGET_COLUMNS)
    errors: list[str] = []

    known = set(projects["project_id"])
    pool_ok = set(projects.loc[projects["is_shared"], "project_id"]) | {"unattributed"}
    target_ok = known - pool_ok

    for i, r in rules.iterrows():
        tag = f"กฎ {r['rule_id'] or '(ไม่มี id)'} v{r['rule_version'] or '?'}"
        for col in ["rule_id", "rule_version", "step", "method", "valid_from", "pool_project_id"]:
            if not r[col]:
                errors.append(f"{tag}: ต้องกรอก {col}")
        if r["rule_version"] and not r["rule_version"].isdigit():
            errors.append(f"{tag}: rule_version ต้องเป็นตัวเลข")
        if r["step"] and not r["step"].isdigit():
            errors.append(f"{tag}: step ต้องเป็นตัวเลข")
        if r["method"] and r["method"] not in METHODS:
            errors.append(f"{tag}: method ต้องเป็น {', '.join(METHODS)}")
        if r["method"] == "usage_driver" and not r["driver_metric"]:
            errors.append(f"{tag}: usage_driver ต้องระบุ driver_metric")
        if r["pool_project_id"] and r["pool_project_id"] not in pool_ok:
            errors.append(f"{tag}: pool ต้องเป็นโปรเจกต์ shared หรือ unattributed (กันการหารวน)")
        for col in ["valid_from", "valid_to"]:
            if r[col] and pd.isna(pd.to_datetime(r[col], errors="coerce")):
                errors.append(f"{tag}: {col} ต้องเป็นวันที่ YYYY-MM-DD")

    dup = rules[rules.duplicated(["rule_id", "rule_version"], keep=False)]
    for _, r in dup.drop_duplicates(["rule_id", "rule_version"]).iterrows():
        errors.append(f"กฎ {r['rule_id']} v{r['rule_version']}: id + version ซ้ำกัน")

    errors += overlapping_ranges(rules)

    for _, t in targets.iterrows():
        tag = f"target ของ {t['rule_id']} v{t['rule_version']}"
        if t["project_id"] not in known:
            errors.append(f"{tag}: ไม่มีโปรเจกต์ {t['project_id']}")
        elif t["project_id"] not in target_ok:
            errors.append(f"{tag}: {t['project_id']} เป็น shared/unattributed รับส่วนแบ่งไม่ได้")
        if not ((rules["rule_id"] == t["rule_id"]) & (rules["rule_version"] == t["rule_version"])).any():
            errors.append(f"{tag}: ไม่มีกฎนี้")

    for _, r in rules[rules["method"] == "fixed_pct"].iterrows():
        t = targets[(targets["rule_id"] == r["rule_id"]) & (targets["rule_version"] == r["rule_version"])]
        total = pd.to_numeric(t["pct"], errors="coerce").sum()
        if abs(total - 100) > 1e-9:
            errors.append(f"กฎ {r['rule_id']} v{r['rule_version']}: pct รวม {total:g} ต้องเป็น 100")

    return errors


def overlapping_ranges(rules: pd.DataFrame) -> list[str]:
    errors = []
    far = pd.Timestamp("9999-12-31")
    for rule_id, g in rules.groupby("rule_id"):
        rows = [
            (r["rule_version"], pd.to_datetime(r["valid_from"], errors="coerce"),
             pd.to_datetime(r["valid_to"], errors="coerce") if r["valid_to"] else far)
            for _, r in g.iterrows()
        ]
        for a in range(len(rows)):
            va, fa, ta = rows[a]
            if pd.notna(fa) and pd.notna(ta) and ta <= fa:
                errors.append(f"กฎ {rule_id} v{va}: valid_to ต้องหลัง valid_from")
            for b in range(a + 1, len(rows)):
                vb, fb, tb = rows[b]
                if all(pd.notna(x) for x in (fa, ta, fb, tb)) and fa < tb and fb < ta:
                    errors.append(f"กฎ {rule_id}: ช่วงวันของ v{va} กับ v{vb} ซ้อนกัน")
    return errors


# ---------- รัน dbt ----------

def run_dbt(args: list[str], db_path: Path | None = None, project_dir: Path = DBT_DIR) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    if db_path:
        env["DBT_DUCKDB_PATH"] = str(db_path)
    return subprocess.run(
        ["dbt", *args, "--profiles-dir", str(project_dir), "--project-dir", str(project_dir),
         "--vars", f"{{cur_path: '{CUR_PATH}'}}"],
        cwd=project_dir, env=env, capture_output=True, text=True,
    )


def preview_allocation(rules: pd.DataFrame, targets: pd.DataFrame) -> tuple[pd.DataFrame | None, str]:
    """ลองใช้กฎใหม่บนสำเนา (ไม่แตะไฟล์จริง) แล้วคืนตารางก่อน/หลังต่อเดือน × โปรเจกต์"""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        proj = tmp / "dbt"
        shutil.copytree(DBT_DIR, proj, ignore=shutil.ignore_patterns("target", "logs", "*.duckdb*"))
        db = tmp / "preview.duckdb"
        shutil.copy(DB_PATH, db)
        save_seeds(rules, targets, proj / "seeds")
        res = run_dbt(["build", "--select", ALLOCATION_SELECTOR, "--full-refresh"], db_path=db, project_dir=proj)
        if res.returncode != 0:
            return None, res.stdout[-4000:]
        sql = "select billing_period, project_id, total_cost from mart_project_cost_monthly"
        before = query(sql)
        after = query(sql, db_path=db)
    df = before.merge(after, on=["billing_period", "project_id"], how="outer", suffixes=("_before", "_after")).fillna(0)
    df["change"] = df["total_cost_after"] - df["total_cost_before"]
    return df.sort_values(["billing_period", "project_id"]), res.stdout[-4000:]
