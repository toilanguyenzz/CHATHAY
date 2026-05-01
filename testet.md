# 🧪 CHAT HAY — Test Plan (Pre-Launch QA)

> **Mục tiêu:** Giả lập trải nghiệm người dùng thực tế trước khi mở rộng.
> **Ngày tạo:** 2026-05-01 | **Tester:** QA Team

---

## 📋 Hướng dẫn

- ✅ Pass | ❌ Fail | ⏳ Chưa test | ⚠️ Pass có vấn đề nhỏ
- Ghi kết quả thực tế + thời gian phản hồi vào cột Ghi chú
- Mỗi test case chạy ít nhất 2 lần

---

## 1. 💬 CHAT THÔNG MINH

| # | User gửi | Kỳ vọng | Status | Ghi chú |
|---|---|---|---|---|
| 1.1 | "chào" | Chào lại ấm áp, giới thiệu bản thân | ⏳ | |
| 1.2 | "hello bạn ơi" | Tương tự, không lỗi | ⏳ | |
| 1.3 | "bạn giúp gì được cho tôi" | Giới thiệu tính năng | ⏳ | |
| 1.4 | "bạn là ai" | Trả lời CHAT HAY, KHÔNG nói là ChatGPT | ⏳ | |
| 1.5 | "giải bài toán 2+2" | Từ chối nhẹ nhàng, gợi ý gửi tài liệu | ⏳ | |
| 1.6 | "cảm ơn bạn nhé" | Đáp lại vui vẻ | ⏳ | |
| 1.7 | "haha" | Không crash, phản hồi thân thiện | ⏳ | |
| 1.8 | Gửi emoji/sticker | Không crash, có phản hồi | ⏳ | |
| 1.9 | "what can you do?" | Trả lời bằng tiếng Việt | ⏳ | |
| 1.10 | Spam 5 tin trong 3 giây | Bot vẫn phản hồi, không treo | ⏳ | |

---

## 2. 📄 GỬI FILE

### 2.1 PDF

| # | Hành động | Kỳ vọng | Status | Ghi chú |
|---|---|---|---|---|
| 2.1.1 | PDF text thuần (5 trang) | Tóm tắt đầy đủ + buttons | ⏳ | |
| 2.1.2 | PDF dài (50+ trang) | Tóm tắt OK, không timeout | ⏳ | |
| 2.1.3 | PDF scan (ảnh) | OCR fallback đọc được | ⏳ | |
| 2.1.4 | PDF trống | Báo không đọc được | ⏳ | |
| 2.1.5 | PDF có password | Báo lỗi rõ ràng | ⏳ | |

### 2.2 Word

| # | Hành động | Kỳ vọng | Status | Ghi chú |
|---|---|---|---|---|
| 2.2.1 | File .docx bình thường | Tóm tắt OK | ⏳ | |
| 2.2.2 | File .doc (Word 97-2003) | Fallback parser đọc được | ⏳ | |
| 2.2.3 | .docx từ Google Docs | XML fallback đọc được | ⏳ | |
| 2.2.4 | .docx có bảng biểu | Đọc được nội dung bảng | ⏳ | |

### 2.3 Excel

| # | Hành động | Kỳ vọng | Status | Ghi chú |
|---|---|---|---|---|
| 2.3.1 | .xlsx có data | Phân tích số liệu cụ thể | ⏳ | |
| 2.3.2 | .xls (Excel cũ) | Hướng dẫn convert sang .xlsx | ⏳ | |
| 2.3.3 | .xlsx nhiều sheet | Đọc multi-sheet | ⏳ | |

### 2.4 File không hỗ trợ

| # | Hành động | Kỳ vọng | Status | Ghi chú |
|---|---|---|---|---|
| 2.4.1 | File .zip | Báo không hỗ trợ | ⏳ | |
| 2.4.2 | File .mp3 | Báo không hỗ trợ | ⏳ | |
| 2.4.3 | File .pptx | Báo không hỗ trợ | ⏳ | |

---

## 3. 📸 GỬI ẢNH

| # | Hành động | Kỳ vọng | Status | Ghi chú |
|---|---|---|---|---|
| 3.1 | Ảnh slide bài giảng rõ nét | Tóm tắt chính xác | ⏳ | |
| 3.2 | Ảnh chụp sách tiếng Việt | Đọc được tiếng Việt có dấu | ⏳ | |
| 3.3 | Ảnh hóa đơn | Nhận dạng invoice, trích xuất số tiền | ⏳ | |
| 3.4 | Ảnh mờ / nghiêng | Cố đọc hoặc báo chụp rõ hơn | ⏳ | |
| 3.5 | Ảnh selfie | Nhận dạng photo, phản hồi phù hợp | ⏳ | |
| 3.6 | Ảnh tiếng Việt + Anh | Output tiếng Việt, KHÔNG tiếng Trung | ⏳ | |
| 3.7 | Gửi 3 ảnh liên tiếp | Mỗi ảnh xử lý riêng, không mất | ⏳ | |

---

## 4. 🔄 TƯƠNG TÁC SAU TÓM TẮT

| # | Hành động | Kỳ vọng | Status | Ghi chú |
|---|---|---|---|---|
| 4.1 | Bấm nút "📌 Ý 1" | Chi tiết ý 1 đầy đủ | ⏳ | |
| 4.2 | Bấm "📌 Ý 2", "📌 Ý 3"... | Đúng nội dung từng ý | ⏳ | |
| 4.3 | Nhắn số "1", "2", "3" | Chi tiết ý tương ứng | ⏳ | |
| 4.4 | Nhắn "chi tiết 2" | Chi tiết ý 2 | ⏳ | |
| 4.5 | Bấm "Xem thêm" | Hiện ý còn lại (>5 ý) | ⏳ | |
| 4.6 | Bấm "🔙 Xem tóm tắt" | Quay lại menu tóm tắt | ⏳ | |
| 4.7 | Nhắn "nghe 1" | File audio ý 1 | ⏳ | |
| 4.8 | Bấm "❓ Hỏi thêm" | Sẵn sàng nhận câu hỏi | ⏳ | |

---

## 5. ❓ HỎI ĐÁP (Q&A)

| # | Hành động | Kỳ vọng | Status | Ghi chú |
|---|---|---|---|---|
| 5.1 | Nhắn "hỏi thêm" sau gửi file | Bot sẵn sàng nhận câu hỏi | ⏳ | |
| 5.2 | Hỏi "Tổng số tiền bao nhiêu?" | Trả lời chính xác từ tài liệu | ⏳ | |
| 5.3 | Hỏi câu ngoài tài liệu | Từ chối, ngoài phạm vi | ⏳ | |
| 5.4 | Bấm suggested question | Trả lời đúng | ⏳ | |
| 5.5 | Hỏi quá 5 câu/tài liệu | Báo hết quota | ⏳ | |
| 5.6 | Hỏi quá 20 câu/ngày | Báo hết quota ngày | ⏳ | |

---

## 6. 📁 QUẢN LÝ FILE

| # | Hành động | Kỳ vọng | Status | Ghi chú |
|---|---|---|---|---|
| 6.1 | Nhắn "files" | Danh sách file đã gửi | ⏳ | |
| 6.2 | Nhắn "xóa" | Danh sách + hướng dẫn xóa | ⏳ | |
| 6.3 | Nhắn "xóa 1" | Xóa file 1, xác nhận | ⏳ | |
| 6.4 | Nhắn "xóa 99" | Báo số không hợp lệ | ⏳ | |
| 6.5 | Nhắn "xóa hết" | Xóa toàn bộ, xác nhận | ⏳ | |
| 6.6 | Gửi 6 file (giới hạn 5) | Cảnh báo đạt giới hạn | ⏳ | |

---

## 7. 📋 OCR & 🔊 TTS

| # | Hành động | Kỳ vọng | Status | Ghi chú |
|---|---|---|---|---|
| 7.1 | Gửi ảnh → "trích xuất" | Trả text thuần từ ảnh | ⏳ | |
| 7.2 | "trích xuất" khi chưa gửi ảnh | Báo gửi ảnh trước | ⏳ | |
| 7.3 | "nghe 1" sau tóm tắt | File audio .mp3 tiếng Việt | ⏳ | |
| 7.4 | "nghe" không có số | Hướng dẫn format đúng | ⏳ | |

---

## 8. 🌐 NGÔN NGỮ & CHẤT LƯỢNG AI

| # | Kiểm tra | Kỳ vọng | Status | Ghi chú |
|---|---|---|---|---|
| 8.1 | File tiếng Việt | Output 100% tiếng Việt có dấu | ⏳ | |
| 8.2 | File tiếng Anh | Output bằng tiếng Việt | ⏳ | |
| 8.3 | File có tiếng Trung | KHÔNG có ký tự Trung trong output | ⏳ | |
| 8.4 | Hợp đồng | Trích số tiền, ngày, tên cụ thể | ⏳ | |
| 8.5 | Detail ý chính | 4-8 câu, không cụt ngủn | ⏳ | |
| 8.6 | Action items | Bắt đầu bằng động từ | ⏳ | |
| 8.7 | Suggested questions | Liên quan nội dung tài liệu | ⏳ | |

---

## 9. ⚡ HIỆU NĂNG

| # | Kiểm tra | Kỳ vọng | Status | Ghi chú |
|---|---|---|---|---|
| 9.1 | Chat thường | < 5 giây | ⏳ | |
| 9.2 | Tóm tắt ảnh | < 15 giây | ⏳ | |
| 9.3 | Tóm tắt PDF 10 trang | < 30 giây | ⏳ | |
| 9.4 | Tóm tắt PDF 50+ trang | < 60 giây | ⏳ | |
| 9.5 | 10 request liên tiếp | Không treo | ⏳ | |
| 9.6 | DeepSeek lỗi → Gemini fallback | Tự chuyển, user không biết | ⏳ | |
| 9.7 | API quota hết | Thông báo rõ ràng | ⏳ | |

---

## 10. 🔒 BẢO MẬT

| # | Kiểm tra | Kỳ vọng | Status | Ghi chú |
|---|---|---|---|---|
| 10.1 | File bị xóa sau xử lý | Không còn trên server | ⏳ | |
| 10.2 | "xóa hết" xóa thật sự | DB sạch data user | ⏳ | |
| 10.3 | User A vs User B | Data hoàn toàn cách ly | ⏳ | |
| 10.4 | Token Zalo auto-refresh | Không expired giữa chừng | ⏳ | |

---

## 11. 🎓 STUDY MODE

| # | Hành động | Kỳ vọng | Status | Ghi chú |
|---|---|---|---|---|
| 11.1 | Gửi tài liệu học tập → "Làm Quiz" | Câu hỏi trắc nghiệm | ⏳ | |
| 11.2 | Chọn đáp án đúng | Thông báo đúng, tăng streak | ⏳ | |
| 11.3 | Chọn đáp án sai | Giải thích đáp án đúng | ⏳ | |
| 11.4 | Hoàn thành quiz | Điểm tổng kết | ⏳ | |
| 11.5 | Bấm "Flashcard" | Mặt trước thẻ | ⏳ | |
| 11.6 | "Lật thẻ" | Mặt sau + nút đánh giá | ⏳ | |
| 11.7 | "Nhớ rồi" / "Chưa nhớ" | Thẻ tiếp theo | ⏳ | |

---

## 12. 🧪 EDGE CASES

| # | Tình huống | Kỳ vọng | Status | Ghi chú |
|---|---|---|---|---|
| 12.1 | File 0 KB (rỗng) | Báo file trống | ⏳ | |
| 12.2 | File > 25 MB | Báo quá lớn | ⏳ | |
| 12.3 | File đổi đuôi (.pdf thật ra .jpg) | Xử lý hoặc báo lỗi rõ | ⏳ | |
| 12.4 | Bấm nút cũ sau gửi file mới | Xử lý đúng context mới | ⏳ | |
| 12.5 | "nghe 1" khi chưa gửi tài liệu | Báo gửi tài liệu trước | ⏳ | |
| 12.6 | "xóa 1" khi 0 file | Báo không có gì xóa | ⏳ | |
| 12.7 | Text 500+ ký tự | Xử lý như tài liệu, tóm tắt | ⏳ | |
| 12.8 | User mới lần đầu | Welcome + hướng dẫn | ⏳ | |
| 12.9 | File .doc có tiếng Trung | Output tiếng Việt | ⏳ | |
| 12.10 | Gửi video | Báo không hỗ trợ | ⏳ | |

---

## 13. 📱 TRẢI NGHIỆM UX (Scoring)

| # | Tiêu chí | Điểm (1-10) | Ghi chú |
|---|---|---|---|
| 13.1 | Dễ hiểu từ lần đầu? | /10 | |
| 13.2 | Tin nhắn độ dài phù hợp? | /10 | |
| 13.3 | Emoji vừa phải? | /10 | |
| 13.4 | Nút bấm dễ dùng? | /10 | |
| 13.5 | Tóm tắt hữu ích? | /10 | |
| 13.6 | Giọng bot thân thiện? | /10 | |
| 13.7 | Muốn dùng lại lần 2? | /10 | |
| 13.8 | Giới thiệu cho bạn bè? | /10 | |
| 13.9 | Thời gian chờ OK? | /10 | |
| 13.10 | **TỔNG UX** | **/90** | |

---

## 14. ✈️ LAUNCH CHECKLIST

| # | Mục | Status |
|---|---|---|
| 14.1 | Tất cả test Section 1-12 ≥ 90% Pass | ⏳ |
| 14.2 | Điểm UX ≥ 63/90 (70%) | ⏳ |
| 14.3 | 0 bug Critical (❌ ở mức nghiêm trọng) | ⏳ |
| 14.4 | Zalo Token auto-refresh OK | ⏳ |
| 14.5 | Railway stable > 24h | ⏳ |
| 14.6 | Logs sạch (no unhandled exception) | ⏳ |
| 14.7 | Rate limit hoạt động | ⏳ |
| 14.8 | File cleanup tự động | ⏳ |

---

## 📊 KẾT QUẢ TỔNG HỢP

| Section | Tổng | ✅ | ❌ | ⏳ |
|---|---|---|---|---|
| 1. Chat | 10 | | | |
| 2. File | 14 | | | |
| 3. Ảnh | 7 | | | |
| 4. Tương tác | 8 | | | |
| 5. Q&A | 6 | | | |
| 6. Quản lý file | 6 | | | |
| 7. OCR & TTS | 4 | | | |
| 8. Ngôn ngữ | 7 | | | |
| 9. Hiệu năng | 7 | | | |
| 10. Bảo mật | 4 | | | |
| 11. Study Mode | 7 | | | |
| 12. Edge Cases | 10 | | | |
| **TỔNG** | **90** | | | |

> **GO/NO-GO:** Pass rate ≥ 90% VÀ 0 Critical bugs → 🚀 LAUNCH!
