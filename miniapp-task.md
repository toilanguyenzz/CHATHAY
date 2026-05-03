# 📱 Task Tracking: Zalo Mini App (Frontend)

## 🎯 Mục tiêu
Xây dựng "CHAT HAY" - ứng dụng học tập với Flashcard 3D, Quiz và quản lý tài liệu. MVP tập trung trải nghiệm người dùng đột phá.

## 📋 Checklist Công Việc

### Giai đoạn 1: Khung Giao Diện & Xác Thực ✅
- [x] Xóa giao diện "Hello World" mặc định
- [x] Thiết kế lại `HomePage`: Ví Coin, nút Nạp Xu, số liệu người dùng
- [x] Thiết kế tab `Kho Tài Liệu (Vault)`: Danh sách tài liệu mẫu
- [x] Tích hợp `getAccessToken()` từ `zmp-sdk`
- [x] Setup TabLayout 2 tab: Trang chủ & Kho tài liệu

### Giai đoạn 2: Tính năng "Deep Work" (Trọng tâm) ✅
- [x] UI Flashcard 3D: Lật thẻ mượt mà, vuốt chuyển thẻ
- [x] UI Quiz: Chọn A/B/C/D, hiện kết quả và giải thích
- [x] Màn hình kết quả Quiz với điểm số và progress bar
- [ ] Tích hợp ZaloPay (Native Checkout) - ĐANG LÀM
- [ ] Kết nối Backend FastAPI để lưu tiến độ

### Giai đoạn 3: Backend & Thanh Toán
- [ ] Tạo endpoint `/api/miniapp/auth` trên Python Backend
- [ ] Backend gọi API Zalo để đổi Token lấy `user_id`
- [ ] API lấy danh sách tài liệu, flashcard, quiz từ DB
- [ ] Webhook ZaloPay xử lý thanh toán Coin

---
*Cập nhật: 2026-05-01 - Hoàn thành MVP UI (Flashcard + Quiz + Vault)*
