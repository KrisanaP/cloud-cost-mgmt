"""หน้า 2: ตรวจย้อนกลับ ไล่จากยอดโปรเจกต์ลงไปถึงบรรทัดบิล

โปรเจกต์ + เดือน -> direct / shared -> กฎ -> บรรทัดบิลต้นทาง + attribution_source
และประวัติการแก้ ownership จาก dbt snapshot
"""
import streamlit as st

from lib import query

st.set_page_config(page_title="ตรวจย้อนกลับ", page_icon="🔎", layout="wide")
st.title("ตรวจย้อนกลับ: เงินก้อนนี้มาจากไหน")

months = query("select distinct strftime(billing_period, '%Y-%m') as m from mart_project_cost_monthly order by 1 desc")["m"]
projects = query("select project_id from mart_project_cost_monthly group by 1 order by sum(total_cost) desc")["project_id"]

c1, c2 = st.columns(2)
month = c1.selectbox("เดือน", months)
project = c2.selectbox("โปรเจกต์", projects)
period = f"{month}-01"

summary = query(
    "select direct_cost, shared_cost, total_cost, prev_total_cost from mart_project_cost_monthly "
    "where project_id = ? and billing_period = ?::date", [project, period])
if summary.empty:
    st.info("ไม่มีต้นทุนในเดือนนี้")
    st.stop()
s = summary.iloc[0]
m1, m2, m3 = st.columns(3)
m1.metric("รวม", f"${s.total_cost:,.2f}",
          None if s.prev_total_cost != s.prev_total_cost else f"{s.total_cost - s.prev_total_cost:+,.2f} จากเดือนก่อน",
          delta_color="inverse")
m2.metric("ต้นทุนตรง", f"${s.direct_cost:,.2f}")
m3.metric("ได้รับหารมา", f"${s.shared_cost:,.2f}")

tab_shared, tab_direct = st.tabs(["ได้รับหารมา (shared)", "ต้นทุนตรง (direct)"])

with tab_shared:
    by_rule = query(
        """
        select rule_id, rule_version, any_value(rule_name) as rule_name, any_value(method) as method,
               any_value(driver_metric) as driver_metric, any_value(step) as step,
               count(*) as line_items, sum(allocated_cost) as received,
               sum(line_effective_cost) as pool_total,
               sum(allocated_cost) / nullif(sum(line_effective_cost), 0) as avg_share
        from mart_allocation_audit
        where project_id = ? and billing_period = ?::date and cost_type = 'shared'
        group by 1, 2 order by received desc
        """, [project, period])
    st.dataframe(by_rule, hide_index=True, use_container_width=True, column_config={
        "received": st.column_config.NumberColumn("ได้รับ", format="$%.2f"),
        "pool_total": st.column_config.NumberColumn("ยอดก้อนเต็ม", format="$%.2f"),
        "avg_share": st.column_config.NumberColumn("ได้ %", format="%.2f"),
    })
    if not by_rule.empty:
        rule = st.selectbox("ดูบรรทัดบิลของกฎ", by_rule["rule_id"])
        lines = query(
            """
            select usage_date, line_item_id, account_name, product_code, resource_id, cost_class,
                   original_project_id as pool, line_effective_cost as pool_line_cost,
                   share_pct, allocated_cost
            from mart_allocation_audit
            where project_id = ? and billing_period = ?::date and rule_id = ?
            order by allocated_cost desc limit 500
            """, [project, period, rule])
        st.caption("share_pct = ส่วนที่โปรเจกต์นี้ได้จากบรรทัดนั้น (คิดจากฐานของวันนั้น / ทั้งเดือนสำหรับบรรทัดรายเดือน)")
        st.dataframe(lines, hide_index=True, use_container_width=True, column_config={
            "pool_line_cost": st.column_config.NumberColumn(format="$%.4f"),
            "allocated_cost": st.column_config.NumberColumn(format="$%.4f"),
            "share_pct": st.column_config.NumberColumn(format="%.4f"),
        })

with tab_direct:
    src = query(
        """
        select attribution_source, count(*) as line_items, sum(allocated_cost) as cost
        from mart_allocation_audit
        where project_id = ? and billing_period = ?::date and cost_type = 'direct'
        group by 1 order by cost desc
        """, [project, period])
    st.caption("override = แก้ใน resource_ownership · tag = จาก tag user_service · account_default = ตาม account")
    st.dataframe(src, hide_index=True, column_config={"cost": st.column_config.NumberColumn(format="$%.2f")})

    resources = query(
        """
        select resource_id, any_value(account_name) as account_name, any_value(product_code) as product_code,
               string_agg(distinct attribution_source, ', ') as attribution_source,
               any_value(override_reason) as override_reason,
               count(*) as line_items, sum(allocated_cost) as cost
        from mart_allocation_audit
        where project_id = ? and billing_period = ?::date and cost_type = 'direct'
        group by 1 order by cost desc limit 200
        """, [project, period])
    st.dataframe(resources, hide_index=True, use_container_width=True,
                 column_config={"cost": st.column_config.NumberColumn(format="$%.2f")})

st.subheader("ประวัติการแก้เจ้าของ resource (ย้อนหลัง)")
st.caption("valid_from/valid_to = เป็นเจ้าของจริงเมื่อไร · dbt_valid_from = วันที่ระบบเห็นการแก้ (จาก snapshot)")
history = query(
    """
    select s.resource_id, s.project_id, s.valid_from, s.valid_to, s.source, s.changed_by, s.changed_at,
           s.reason, s.dbt_valid_from as recorded_at, s.dbt_valid_to as superseded_at
    from snap_resource_ownership s
    where s.project_id = ?
       or s.resource_id in (select resource_id from mart_allocation_audit
                            where project_id = ? and billing_period = ?::date and resource_id is not null)
    order by s.resource_id, s.dbt_valid_from
    """, [project, project, period])
if history.empty:
    st.write("ไม่มีการแก้ ownership ที่เกี่ยวกับโปรเจกต์นี้")
else:
    st.dataframe(history, hide_index=True, use_container_width=True)
