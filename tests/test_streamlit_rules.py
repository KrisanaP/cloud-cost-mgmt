"""ตรวจ validate() ของหน้าตั้งกฎ ให้ตรงกับ dbt tests"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "streamlit_app"))
from lib import load_projects, load_rules, load_targets, validate  # noqa: E402


def test_current_seeds_are_valid():
    assert validate(load_rules(), load_targets(), load_projects()) == []


def test_fixed_pct_must_sum_to_100():
    targets = load_targets()
    targets.loc[targets["project_id"] == "ledger", "pct"] = "30"
    errors = validate(load_rules(), targets, load_projects())
    assert any("pct รวม 90" in e for e in errors)


def test_overlapping_versions_rejected():
    rules = load_rules()
    extra = rules[rules["rule_id"] == "tax"].copy()
    extra["rule_version"] = "2"
    extra["valid_from"] = "2026-08-01"
    errors = validate(pd.concat([rules, extra]), load_targets(), load_projects())
    assert any("ซ้อนกัน" in e for e in errors)


def test_pool_must_be_shared_and_target_not_shared():
    rules = load_rules()
    rules.loc[rules["rule_id"] == "tax", "pool_project_id"] = "storefront"
    targets = pd.concat([load_targets(), pd.DataFrame([{
        "rule_id": "rds_ri_unused", "rule_version": "1", "project_id": "eks-platform", "pct": "0"}])])
    errors = validate(rules, targets, load_projects())
    assert any("หารวน" in e for e in errors)
    assert any("รับส่วนแบ่งไม่ได้" in e for e in errors)
