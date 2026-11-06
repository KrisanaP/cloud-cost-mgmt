-- จุดเริ่มต้นของเฟส 1: ตอนนี้แค่อ่านไฟล์ดิบผ่าน source เพื่อให้ dbt build ผ่าน
-- เฟส 1 จะมาเลือกคอลัมน์, cast type และแตก JSON (resource_tags, cost_category) ที่ไฟล์นี้
select *
from {{ source('cur', 'cur2_sample') }}
