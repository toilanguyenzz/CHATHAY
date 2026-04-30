# ✅ Task Tracking: Excel Support + Q&A Limit

## 📊 Tổng quan
- **Dự kiến:** ~2 giờ
- **Trạng thái:** COMPLETED ✅
- **Risk:** LOW (thêm nhánh, không sửa core)

---

## 🔧 File Changes Checklist

### 1. `requirements.txt`
- [x] Thêm `openpyxl==3.1.5`

### 2. `services/document_parser.py`
- [x] Thêm hàm `parse_xlsx()` (45 lines)
- [x] Update `get_file_type()`: thêm `.xlsx`, `.xls_legacy`
- [x] Update `extract_text()`: branch cho `xlsx`

### 3. `services/ai_summarizer.py`
- [x] Thêm `"spreadsheet": "📊 Bảng tính"` vào `DOC_TYPE_LABELS`
- [x] Update `_build_text_prompt()`: detect `[Excel:` + Excel hint
- [x] Update suggested_questions logic cho spreadsheet

### 4. `services/db_service.py`
- [x] Thêm `_memory_qa_count` dict + `QA_LIMIT_PER_DOC = 5`
- [x] Thêm `get_qa_count(user_id, doc_id)`
- [x] Thêm `increment_qa_count(user_id, doc_id)`
- [x] Thêm `reset_qa_count(user_id, doc_id)`
- [x] Update `delete_user_data()`: cleanup `_memory_qa_count`
- [x] Update `delete_document_by_id()`: cleanup counter

### 5. `zalo_webhook.py`
- [x] Xử lý `.xls_legacy` → thông báo yêu cầu `.xlsx`
- [x] Update `get_welcome_message()`: thêm "bảng tính Excel"
- [x] Update `get_upload_prompt()`: "PDF/Word/Excel"
- [x] Update `get_menu_message()`: cập nhật text
- [x] Update `handle_qa_session()`:
  - [x] Check document limit trước khi xử lý
  - [x] `increment_qa_count()` sau khi answer
  - [x] Hiển thị counter: "Đã hỏi X/5 câu"
  - [x] Update buttons: ẩn "Hỏi thêm" nếu hết lượt
- [x] Update `handle_interactive_command()`: check limit trong "HỎI THÊM"
- [x] Update `handle_zalo_file()`: `reset_qa_count()` sau khi summarize

---

## 🧪 Test Plan
- [ ] Parse .xlsx với nhiều sheets, merged cells
- [ ] .xls file → error message đúng
- [ ] Q&A 5 câu → block, 6th câu bị chặn
- [ ] Reset counter khi gửi file mới
- [ ] Counter cleanup khi xóa document
- [ ] Suggested questions cho Excel (tổng, trung bình, so sánh)
- [ ] Buttons hiển thị đúng (remaining count)

---

## 📈 Metrics
- **Lines of code new:** ~120
- **Lines of code modified:** ~40
- **Dependencies:** +1 (`openpyxl`)

---

## ⚠️ Known Issues / Future
- In-memory counter → reset khi server restart (accept)
- Excel row limit 500/sheet (configurable sau này)
- `.xls` không auto-convert (user phải chuyển thủ công)
