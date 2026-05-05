# 🧭 LÕI CHIẾN LƯỢC SẢN PHẨM: OA vs MINI APP (RULE)

**Tài liệu này định nghĩa triết lý phát triển sản phẩm của "CHAT HAY". Mọi tính năng, luồng giao diện (UI/UX) và logic code đều phải tuân thủ nghiêm ngặt ranh giới giữa Zalo OA và Zalo Mini App được quy định dưới đây.**

---

## 1. 🚀 ZALO OA: PHỄU MARKETING & DEMO (THE ACQUISITION FUNNEL)

**Định vị:** Đây là bề nổi của tảng băng chìm. Nơi để người dùng mới trải nghiệm "WOW moment" (khoảnh khắc kinh ngạc) ngay trong 3 giây đầu tiên mà không cần cài đặt bất cứ thứ gì.

**Nguyên tắc thiết kế (Rules):**
- **Nhanh & Tối giản:** Chỉ nhận file -> Trả tóm tắt cực nhanh. Không bắt user phải cấu hình rườm rà.
- **Giới hạn "Mồi nhử" (Demo Limit):** 
  - Chỉ cho phép dùng miễn phí 1-2 file/ngày.
  - Giới hạn hỏi đáp (VD: 2-3 câu/file).
  - Bản tóm tắt là dạng ngắn gọn (Bullet points cơ bản).
- **Mục tiêu cốt lõi:** Lấy lượt chia sẻ (viral) và thu thập tập người dùng (Followers).
- **Call-to-Action (Kêu gọi hành động):** Khi user chạm mốc giới hạn hoặc muốn dùng tính năng nâng cao, Bot không báo lỗi khô khan, mà phải dẫn dụ: *"💡 Tính năng này đòi hỏi phân tích chuyên sâu. Mời bạn mở Mini App để trải nghiệm trọn vẹn (Tặng kèm 100 điểm cho lần đầu)!"*

---

## 2. 💎 ZALO MINI APP: HUB CHUYÊN SÂU & THU TIỀN (THE MONETIZATION ENGINE)

**Định vị:** Sản phẩm chủ lực. Nơi giữ chân người dùng (Retention) và tạo ra doanh thu. UI/UX phải cực kỳ tiện lợi, mượt mà như một App độc lập và phù hợp cho mọi lứa tuổi (từ học sinh đến người đi làm lớn tuổi).

**Nguyên tắc thiết kế (Rules):**
- **Trải nghiệm chuyên sâu (Deep Work):**
  - Quản lý kho tài liệu (Vault) lưu trữ vĩnh viễn.
  - Các chế độ học tập (Study Mode): Sinh tự động Flashcard, Trắc nghiệm (Quiz), Lộ trình ôn thi.
  - Hỏi đáp không giới hạn, chat với nhiều tài liệu cùng lúc.
- **Tối ưu UI/UX cho mọi lứa tuổi:**
  - Font chữ to, rõ ràng, độ tương phản cao (phù hợp người lớn tuổi đọc báo cáo).
  - Thao tác chạm vuốt trực quan (phù hợp học sinh/sinh viên dùng Flashcard).
- **Mô hình Thu tiền (Pay-as-you-go):**
  - Không bán gói tháng (Subscription) gây tâm lý dè chừng.
  - Sử dụng hệ thống "Ví/Coin" tích hợp trực tiếp **ZaloPay**. Nạp tiền nhỏ (10k, 20k) -> Trừ coin cho mỗi lần sử dụng tính năng sâu. Friction (độ ma sát) thanh toán phải bằng 0.

---

## ⚖️ MA TRẬN QUYẾT ĐỊNH TÍNH NĂNG (FEATURE DECISION MATRIX)

Mỗi khi định code thêm 1 tính năng mới, Developer phải check bảng này:

| Loại tính năng | Đặt ở Zalo OA (Chat) | Đặt ở Zalo Mini App |
| :--- | :---: | :---: |
| **Gửi file & Tóm tắt nhanh** | ✅ (Giới hạn độ dài) | ✅ (Full nội dung) |
| **Giao tiếp / Chào hỏi cơ bản** | ✅ (Tạo cảm giác thân thiện) | ❌ (Không cần thiết) |
| **Hỏi đáp Q&A** | ⚠️ (Chỉ 2-3 câu/file) | ✅ (Không giới hạn) |
| **Tạo Quiz / Flashcard học tập** | ❌ (UI chat không hỗ trợ tốt) | ✅ (Trải nghiệm chạm/vuốt) |
| **Quản lý danh sách file cũ** | ❌ (Trôi tin nhắn, khó tìm) | ✅ (Giao diện list/thư mục) |
| **Thanh toán / Nạp tiền** | ❌ (Trải nghiệm đứt gãy) | ✅ (Native ZaloPay) |

> **CHÂM NGÔN:** "OA dùng để thả thính, Mini App dùng để chốt đơn." Mọi code viết ra phải phục vụ đúng luồng tư duy này.
