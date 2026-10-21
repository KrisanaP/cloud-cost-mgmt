-- Phase 1: สำรวจ CUR 2.0 ด้วย SQL
-- รัน:  duckdb -c ".read exercises/phase1.sql"   หรือเปิดใน DuckDB CLI / Jupyter
-- ทุกข้อเริ่มจาก view `cur` ด้านล่าง เติม SQL ใต้แต่ละข้อแล้วจดคำตอบไว้ใน comment

CREATE OR REPLACE VIEW cur AS SELECT * FROM 'data/cur2_sample.parquet';

-- ตัวอย่าง: ข้อมูลมีกี่แถว ช่วงวันไหน
SELECT count(*) AS n_rows,
       min(line_item_usage_start_date) AS first_day,
       max(line_item_usage_start_date) AS last_day
FROM cur;

-- 1) ยอดรวมแยกตาม line_item_line_item_type
--    คำถามต่อ: type ไหนควรตัดออก/ปรับเวลาคิด "ค่าใช้จ่ายของทีม" เพราะอะไร
-- TODO


-- 2) Top 10 service ตามค่าใช้จ่าย และ top 10 resource ID
-- TODO


-- 3) ค่าใช้จ่ายรายวันแยกตาม account (เอาไปวาดกราฟเส้นใน Jupyter)
-- TODO


-- 4) แตก tag user_team ออกจาก resource_tags แล้วหา % ค่าใช้จ่ายที่ไม่ได้ tag
--    hint: json_extract_string(resource_tags, '$.user_team')
--    ดูค่าที่ได้ด้วย — สะกดเหมือนกันหมดไหม?
-- TODO


-- 5) หาวันที่ S3 ของ acme-data เริ่มพุ่ง โดยเทียบกับค่าเฉลี่ย 7 วันก่อนหน้า
--    hint: AVG(...) OVER (ORDER BY day ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING)
-- TODO


-- 6) EC2 ที่ใช้ Savings Plan: on-demand cost vs effective cost ประหยัดไปเท่าไร
--    แล้วเทียบกับแถว SavingsPlanRecurringFee — ใช้ commitment เต็มไหม (utilization กี่ %)
-- TODO


-- 7) Week-over-week change ต่อ service
-- TODO


-- 8) ค่าใช้จ่ายแยก region และแยก usage type (เช่น NatGateway-Bytes vs NatGateway-Hours)
-- TODO


-- 9) Cost per environment ต่อ business unit จาก cost_category
-- TODO


-- 10) view daily_cost: 1 แถวต่อ วัน × account × service × team
--     คิดก่อนว่าคอลัมน์ cost ควรเป็น unblended หรือ amortized และจัดการ commitment rows ยังไง
-- CREATE OR REPLACE VIEW daily_cost AS
-- TODO
