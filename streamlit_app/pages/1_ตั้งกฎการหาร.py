"""หน้า 1: ตั้งกฎการหาร shared cost

แก้ seeds/allocation_rules.csv และ allocation_rule_targets.csv
ตรวจก่อนบันทึก -> preview ผลกระทบบนสำเนา -> บันทึก -> รัน dbt build เฉพาะส่วนที่เกี่ยว
"""
import pandas as pd
import streamlit as st

from lib import (ALLOCATION_SELECTOR, METHODS, load_projects, load_rules, load_targets,
                 preview_allocation, run_dbt, save_seeds, validate)

st.set_page_config(page_title="ตั้งกฎการหาร", page_icon="⚖️", layout="wide")
st.title("ตั้งกฎการหาร shared cost")
st.caption(
    "1 แถว = 1 เวอร์ชันของกฎ จะเปลี่ยนกฎให้ปิดเวอร์ชันเดิมด้วย valid_to แล้วเพิ่มเวอร์ชันใหม่ "
    "ช่อง pool_* ว่าง = ไม่กรอง · ขั้น (step) 2 ใช้ยอดหลังหารขั้น 1 เป็นฐาน"
)

projects = load_projects()
pool_options = sorted(projects.loc[projects["is_shared"], "project_id"]) + ["unattributed"]
target_options = sorted(projects.loc[~projects["is_shared"] & (projects["project_id"] != "unattributed"), "project_id"])

with st.expander("วิธีหารแต่ละแบบ"):
    st.markdown(
        """
| method | หารตาม | ต้องกรอก |
| --- | --- | --- |
| `even` | เท่ากันทุกโปรเจกต์ (หรือเฉพาะ targets) | - |
| `fixed_pct` | % ที่ตกลงกัน | targets + pct รวม 100 |
| `proportional_direct` | ต้นทุนของแต่ละโปรเจกต์ในช่วงวันเดียวกัน | - (targets ถ้าอยากจำกัด) |
| `usage_driver` | ปริมาณใช้จริงจาก `usage_drivers` | driver_metric |
"""
    )

if "rules" not in st.session_state:
    st.session_state.rules = load_rules()
    st.session_state.targets = load_targets()

st.subheader("กฎ")
rules = st.data_editor(
    st.session_state.rules,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    key="rules_editor",
    column_config={
        "method": st.column_config.SelectboxColumn(options=METHODS, required=True),
        "pool_project_id": st.column_config.SelectboxColumn(options=pool_options, required=True),
        "pool_cost_class": st.column_config.SelectboxColumn(
            options=["", "direct", "commitment_unused", "tax", "support", "credit", "fee"]),
    },
)

st.subheader("โปรเจกต์ที่ร่วมหาร (targets)")
st.caption("กฎที่ไม่มีแถวตรงนี้ = หารให้ทุกโปรเจกต์ที่รับส่วนแบ่งได้")
targets = st.data_editor(
    st.session_state.targets,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    key="targets_editor",
    column_config={"project_id": st.column_config.SelectboxColumn(options=target_options, required=True)},
)

errors = validate(rules, targets, projects)
if errors:
    st.error("ยังบันทึกไม่ได้:\n\n" + "\n".join(f"- {e}" for e in errors))
else:
    st.success("ตรวจผ่าน: id/เวอร์ชันไม่ซ้ำ, ช่วงวันไม่ซ้อน, pct รวม 100, โปรเจกต์มีจริง, ไม่หารวน")

c1, c2, c3 = st.columns(3)

if c1.button("Preview ผลกระทบ", disabled=bool(errors), use_container_width=True):
    with st.spinner("ลองรัน dbt บนสำเนา (ไม่แตะไฟล์จริง)..."):
        diff, log = preview_allocation(rules, targets)
    if diff is None:
        st.error("dbt บนสำเนาไม่ผ่าน")
        st.code(log)
    else:
        diff["month"] = pd.to_datetime(diff["billing_period"]).dt.strftime("%Y-%m")
        changed = diff[diff["change"].abs() >= 0.005]
        st.write(f"โปรเจกต์ × เดือนที่ตัวเลขเปลี่ยน: {len(changed)} รายการ "
                 f"(ยอดรวมเปลี่ยน {diff['change'].sum():+.4f} USD ต้องเป็น 0)")
        st.dataframe(
            changed[["month", "project_id", "total_cost_before", "total_cost_after", "change"]],
            hide_index=True, use_container_width=True,
            column_config={c: st.column_config.NumberColumn(format="$%.2f")
                           for c in ["total_cost_before", "total_cost_after", "change"]},
        )

if c2.button("บันทึกลง seeds", disabled=bool(errors), use_container_width=True):
    save_seeds(rules, targets)
    st.session_state.rules = load_rules()
    st.session_state.targets = load_targets()
    st.success("บันทึกแล้ว อย่าลืม commit ไฟล์ใน dbt/seeds/ ถ้าอยากเก็บประวัติใน git")

if c3.button("รัน dbt build", use_container_width=True):
    with st.spinner(f"dbt build --select {ALLOCATION_SELECTOR} ..."):
        res = run_dbt(["build", "--select", ALLOCATION_SELECTOR, "--full-refresh"])
    (st.success if res.returncode == 0 else st.error)(
        "dbt build ผ่าน ตัวเลขในแดชบอร์ดอัปเดตแล้ว" if res.returncode == 0 else "dbt build ไม่ผ่าน")
    st.code(res.stdout[-3000:])
