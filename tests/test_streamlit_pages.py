"""เปิดทุกหน้า Streamlit แบบ headless (ต้อง dbt build ก่อน) แล้วเช็กว่าไม่มี exception"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "streamlit_app"
DB = APP.parent / "dbt" / "warehouse.duckdb"
pytestmark = pytest.mark.skipif(not DB.exists(), reason="ต้องรัน dbt build ก่อน")


@pytest.mark.parametrize("page", ["Home.py", "pages/1_ตั้งกฎการหาร.py", "pages/2_ตรวจย้อนกลับ.py"])
def test_page_renders(page):
    at = AppTest.from_file(str(APP / page), default_timeout=60).run()
    assert not at.exception, at.exception


def test_audit_page_shows_rules_for_august_storefront():
    at = AppTest.from_file(str(APP / "pages/2_ตรวจย้อนกลับ.py"), default_timeout=60).run()
    at.selectbox[0].select("2026-08").run()
    at.selectbox[1].select("storefront").run()
    assert not at.exception
    assert any(m.label == "ได้รับหารมา" for m in at.metric)
    rules_table = at.dataframe[0].value
    assert {"eks", "network", "support", "tax"} <= set(rules_table["rule_id"])
