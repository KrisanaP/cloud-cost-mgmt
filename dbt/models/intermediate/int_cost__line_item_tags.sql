-- tag แบบยาวของ "ทุกเดือน" ใน fct_cost_line_item
-- (staging เห็นแค่ไฟล์รอบล่าสุด แต่ attribution ต้องคิดใหม่ทั้งประวัติทุกครั้ง)
{{ explode_tags(ref('fct_cost_line_item')) }}
