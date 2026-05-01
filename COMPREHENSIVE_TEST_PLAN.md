# 📋 Kế hoạch Test Toàn diện cho Zalo‑Doc‑Bot

**Ngày tạo:** 2026‑05‑01 | **Người tạo:** QA Team

---

## 1. Tổng quan Coverage hiện tại
| Module | Test hiện có | Ghi chú |
|---|---|---|
| `study_engine` | 23 unit + 12 edge | ✅ Đủ coverage |
| `db_service` | 3 unit | ✅ Đủ |
| `integration_study_mode` | 2 integration | ✅ Đủ |
| `ai_summarizer` | 1 unit (document type) | ❌ Chưa test full summarizer |
| `mode_detector` | Không có unit | ❌ |
| `document_parser` | Không có unit | ❌ |
| `tts_service` | Không có unit | ❌ |
| `token_store` | Không có unit | ❌ |
| `study_analytics` | Không có unit | ❌ |
| `zalo_webhook` | Không có unit | ❌ |

**Kết luận:** Cần bổ sung unit/integration cho 7 module trên và thêm các lớp test bảo mật, hiệu năng, triển khai.

---

## 2. Chiến lược Test
| Lớp Test | Mục tiêu | Công cụ | Tần suất |
|---|---|---|---|
| **Unit** | Kiểm tra logic riêng lẻ, các hàm, lớp | `pytest` | CI mỗi commit |
| **Integration** | Kiểm tra luồng dữ liệu giữa các service | `pytest` + mock external APIs | Nightly |
| **E2E** | Mô phỏng người dùng (chat, upload file, TTS) | `playwright`/`cypress` | Trước release |
| **Security** | Input validation, injection, auth, token refresh | `bandit`, custom fuzz | Khi có thay đổi security‑critical |
| **Performance** | Thời gian phản hồi, tải đồng thời | `locust`, benchmark scripts | Weekly |
| **Deployment** | Migration DB, token auto‑refresh, cleanup | Shell scripts, `gh` CI | Khi deploy |

---

## 3. Ma trận Test chi tiết
### 3.1 `mode_detector.py`
- **Unit Tests**
  - Detect STUDY_MATERIAL với từ khóa tiếng Việt
  - Detect BUSINESS_DOC với từ khóa doanh nghiệp
  - Detect GENERAL khi không đủ thông tin
  - Xử lý lỗi API (Gemini timeout, JSON parse error)
- **Integration**
  - Kết hợp với `study_engine` để xác nhận mode trước khi tạo quiz
- **Security**
  - Đảm bảo không có injection trong prompt (escape ký tự đặc biệt)

### 3.2 `document_parser.py`
- **Unit Tests**
  - `parse_pdf` thành công với pdfplumber & fallback PyMuPDF
  - Xử lý PDF rỗng, password, lỗi đọc
  - `parse_docx` đọc text, bảng, hình ảnh
  - Xử lý file không tồn tại → trả về ""
- **Performance**
  - Đọc PDF 50 trang < 2s
  - Đọc DOCX 10 MB < 1s

### 3.3 `tts_service.py`
- **Unit Tests**
  - `split_text_smart` chia đúng chuỗi
  - `_tts_single_chunk` trả về audio bytes khi API OK
  - Xử lý lỗi API (status != 200, timeout)
- **Integration**
  - `text_to_speech` tạo file MP3, lưu đúng `config.AUDIO_DIR`
  - `cleanup_audio` xóa file tạm
- **Security**
  - Kiểm tra không lưu key API vào log

### 3.4 `token_store.py`
- **Unit Tests**
  - Lưu/đọc token từ Supabase (mock client)
  - Fallback SQLite khi Supabase không khả dụng
  - Fallback env var khi cả hai đều không có
- **Security**
  - Đảm bảo token không log ra console
  - Kiểm tra auto‑refresh không gây race condition

### 3.5 `ai_summarizer.py`
- **Unit Tests**
  - Kiểm tra routing giữa Gemini & DeepSeek
  - Xử lý lỗi quota, fallback đúng
- **Integration**
  - Kết hợp với `document_parser` → summarizer trả về JSON đúng schema

### 3.6 `study_analytics.py`
- **Unit Tests**
  - Ghi log sự kiện quiz, flashcard, thời gian
  - Đảm bảo không gây lỗi khi DB unavailable

### 3.7 `zalo_webhook.py`
- **Unit Tests**
  - Xác thực chữ ký Zalo
  - Xử lý các event: `message`, `postback`
  - Trả về 200 OK trong mọi trường hợp
- **Security**
  - Kiểm tra replay attack (nonce)

---

## 4. Test Cases mẫu (được tự động sinh từ ma trận trên)
1. **ModeDetector – STUDY**
   - Input: "Đề thi Toán, có câu hỏi trắc nghiệm, công thức" → Expect `mode='STUDY_MATERIAL'` và confidence > 0.8.
2. **DocumentParser – PDF password**
   - Input: PDF có mật khẩu → Expect empty string và log warning.
3. **TTS – Chunk split**
   - Input: 1200 ký tự → Expect 3 chunks, mỗi chunk ≤ 450 ký tự.
4. **TokenStore – Supabase down**
   - Mock Supabase raise exception → Expect fallback SQLite lưu thành công.
5. **Security – Injection prompt**
   - Input chứa `"; rm -rf /"` vào `detect_mode` → Ensure prompt được escape, không thực thi lệnh.

---

## 5. Kế hoạch thực thi
1. **Cài đặt môi trường**
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-asyncio playwright locust bandit
   ```
2. **Chạy unit & integration**
   ```bash
   pytest tests/ -m "not e2e"
   ```
3. **Chạy E2E** (trong CI)
   ```bash
   playwright test e2e/
   ```
4. **Kiểm tra bảo mật**
   ```bash
   bandit -r services/
   ```
5. **Benchmark hiệu năng**
   ```bash
   locust -f benchmark_performance.py
   ```
6. **CI pipeline**
   - Lint → Test → Performance threshold → Deploy nếu pass.

---

## 6. Tiêu chí Pass
- **Unit/Integration:** 100% pass, coverage ≥ 90% cho các module mới.
- **E2E:** ≥ 95% pass, thời gian phản hồi < 5s cho mỗi bước.
- **Security:** Không có high‑severity findings.
- **Performance:** PDF 50‑page ≤ 30s, TTS ≤ 10s, concurrency 20 users ≤ 2s response.
- **Deployment:** Token auto‑refresh > 99.9% uptime, cleanup file < 1s.

---

## 7. Theo dõi tiến độ
- **Todo:** `TodoWrite` sẽ được cập nhật khi các test case được triển khai.
- **Bug tracker:** Mỗi lỗi sẽ ghi vào issue GitHub với label `test‑failure`.

> **GO/NO‑GO:** Khi tất cả mục 1‑6 đạt tiêu chuẩn, dự án sẵn sàng launch.
