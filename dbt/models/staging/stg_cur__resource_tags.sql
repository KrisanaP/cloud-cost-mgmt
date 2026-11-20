-- 1 แถว = 1 line item × 1 tag key (เฉพาะไฟล์ที่อ่านรอบนี้)
-- key/value ถูก normalize เป็นตัวเล็กและตัดช่องว่าง, ค่าเดิมอยู่ใน *_raw
{{ explode_tags(ref('stg_cur__line_items')) }}
