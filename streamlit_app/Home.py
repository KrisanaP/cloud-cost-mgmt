"""Streamlit ของโปรเจกต์ Cloud Cost Management: 2 หน้า (ตั้งกฎการหาร, ตรวจย้อนกลับ)

รัน:  streamlit run streamlit_app/Home.py      (จาก root ของ repo หลัง dbt build)
"""
import streamlit as st

from lib import DB_PATH, query

st.set_page_config(page_title="Cloud Cost Management", page_icon="💸", layout="wide")
st.title("Cloud Cost Management")

if not DB_PATH.exists():
    st.error(f"ยังไม่มี {DB_PATH} ให้รัน `cd dbt && dbt build --profiles-dir .` ก่อน")
    st.stop()

st.markdown(
    """
แดชบอร์ดหลักอยู่ที่ Evidence (`dashboard/`) แอปนี้มี 2 หน้าที่แดชบอร์ดสำเร็จรูปทำไม่ได้

- **ตั้งกฎการหาร**: ดู/แก้กฎหาร shared cost, ตรวจก่อนบันทึก, preview ผลกระทบ แล้วรัน dbt
- **ตรวจย้อนกลับ**: เลือกโปรเจกต์ + เดือน แล้วไล่ลงไปถึงบรรทัดบิลต้นทาง
"""
)

totals = query(
    """
    select strftime(billing_period, '%Y-%m') as month,
           sum(total_cost) as total, sum(direct_cost) as direct, sum(shared_cost) as shared
    from mart_project_cost_monthly group by 1 order by 1
    """
)
st.subheader("ยอดต่อเดือน (หลังหาร = ยอดบิล)")
st.dataframe(totals, hide_index=True, column_config={
    c: st.column_config.NumberColumn(format="$%.2f") for c in ["total", "direct", "shared"]
})
