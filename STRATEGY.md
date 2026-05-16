# 🎯 CHAT HAY — CHIẾN LƯỢC SẢN PHẨM & KINH DOANH
> **Cập nhật:** 2026-05-09
> **Trạng thái:** Active — Đọc file này TRƯỚC khi quyết định build feature mới

---

## 1. POSITIONING — CHAT HAY LÀ GÌ?

### ❌ Chat Hay KHÔNG PHẢI:
- Không phải LMS (Google Classroom, Moodle đã thắng)
- Không phải quiz platform (Azota, Quizizz đã có)
- Không phải flashcard app (Quizlet, Anki đã làm 15 năm)
- Không phải video bài giảng (VioEdu, Hocmai đã có Viettel/VTC đứng sau)
- Không phải thêm 1 app giáo dục nữa trong hàng trăm app

### ✅ Chat Hay LÀ:
> **"Công cụ AI giúp học sinh xử lý bài vở trên Zalo nhanh nhất có thể — ngay trong Zalo, không cần rời đi đâu."**

Chat Hay biến Zalo từ "ứng dụng giao việc đáng sợ" → thành nơi học sinh có **phản xạ tự nhiên**: nhận bài → forward vào Chat Hay → xong trong 10 giây.

### Khác biệt cốt lõi (vs. mọi đối thủ):

| Yếu tố | Đối thủ | Chat Hay |
|---|---|---|
| **Nơi hoạt động** | App riêng / Web riêng | **TRONG Zalo** — nơi 75M người Việt đã ở |
| **Ai setup** | Giáo viên phải tạo nội dung | **Không ai cần setup** — chụp/forward → AI làm hết |
| **Tốc độ** | Mở app → đăng nhập → tìm → làm | **1 chạm forward → 10 giây có kết quả** |
| **Nội dung** | Bài chung cho cả nước | **Bài CỦA BẠN** — sách bạn, bài tập bạn, đề thi bạn |
| **Tích lũy** | Bắt đầu lại từ đầu | Càng dùng → kho tài liệu + flashcard RIÊNG → không bỏ được |

---

## 2. INSIGHT NỀN TẢNG — TẠI SAO ZALO?

### 2.1 "Zalo = Stress" — Nhưng đó là CƠ HỘI

Thực tế tâm lý người Việt:
- Học sinh **sợ mở Zalo** vì ngập bài tập, deadline, nhóm lớp ping liên tục
- Giáo viên **ngán Zalo** vì phụ huynh hỏi, hiệu trưởng giao việc
- Phụ huynh **lo lắng** mỗi khi Zalo có thông báo từ trường

**→ Ai giải quyết được nỗi đau này trong Zalo = thắng.**

Chat Hay không thêm stress — Chat Hay **giảm stress**:
```
TRƯỚC: Nhận 10 trang PDF → ngồi đọc 45 phút → không hiểu → stress
SAU:   Nhận 10 trang PDF → forward Chat Hay → tóm tắt 30s → hiểu → xong
```

### 2.2 Trigger tự nhiên, miễn phí, hàng ngày

Không cần marketing. Zalo marketing HỘ bạn:
```
Mỗi ngày, mỗi học sinh:
├── Nhận 2-5 bài tập/file từ giáo viên qua Zalo
├── Nhận tin nhắn nhóm lớp về bài vở
├── Nhận thông báo kiểm tra/thi
└── → 3-5 lần trigger TỰ NHIÊN để mở Chat Hay

× 22 triệu học sinh
= 66-110 triệu triggers/ngày mà KHÔNG TỐN 1 ĐỒNG MARKETING
```

---

## 3. HOOK MODEL — TẠO THÓI QUEN HÀNG NGÀY

```
TRIGGER (Tự nhiên)         Nhận bài/file trên Zalo
       ↓                   Xảy ra 3-5 lần/ngày, tự động
ACTION (Cực dễ)            Forward vào Chat Hay (1 chạm)
       ↓                   Không suy nghĩ, không rời Zalo
REWARD (Cực nhanh)         10s: tóm tắt / giải bài / quiz
       ↓                   Nhanh hơn 18x so với tự làm
INVESTMENT (Tích lũy)      Kho tài liệu, flashcard, lịch sử
       ↓                   Càng dùng → càng không bỏ được
       ↓
       └──→ Ngày mai trigger lại → THÓI QUEN (30 ngày = locked in)
```

### Switching Cost sau 1 tháng:
- 30+ tài liệu đã tóm tắt
- 50+ bài tập đã giải (có lời giải chi tiết)
- 200+ flashcard từ nội dung RIÊNG
- AI "biết" mình yếu chương nào, mạnh chương nào
- **→ Chuyển sang app khác = MẤT HẾT → Không ai bỏ**

---

## 4. BA CORE FLOWS — TẬP TRUNG MÀI SẮC

> ⚠️ NGUYÊN TẮC: Không build feature mới cho đến khi 3 flow này CỰC NHANH, CỰC MƯỢT, CỰC ĐẸP.

### Flow #1: Forward to Learn (KILLER FEATURE)
```
Nhóm Zalo lớp → Cô gửi PDF → Học sinh nhấn "Chia sẻ" → chọn Chat Hay
→ 8 giây sau:
  ✅ Tóm tắt nội dung
  📖 Xem lý thuyết chi tiết
  ✏️ AI giải bài tập trong file
  🧠 Tạo quiz ôn tập
  💾 Lưu vào kho tài liệu cá nhân
```
- **Hiện tại:** Zalo Share Intent đã có, nhưng buggy, cần fix
- **Target:** < 10 giây từ forward → kết quả hiển thị
- **Metric:** Share Intent success rate > 95%

### Flow #2: Snap & Solve (SPEED)
```
Đang làm bài, kẹt → Chụp ảnh câu hỏi → Gửi Chat Hay
→ 8 giây sau:
  📝 Đề bài (OCR)
  📖 Giải chi tiết từng bước (tiếng Việt, đúng SGK)
  💡 Mẹo ghi nhớ
  🔄 Tạo 3 câu tương tự luyện thêm
```
- **Hiện tại:** Hoạt động nhưng chưa tối ưu tốc độ
- **Target:** < 10 giây từ chụp → giải xong hiển thị
- **Metric:** Accuracy > 90% cho Toán/Lý/Hóa phổ thông VN

### Flow #3: Quick Quiz (REINFORCE)
```
Vừa đọc tóm tắt / vừa giải xong bài → 1 tap "Ôn nhanh"
→ Ngay lập tức:
  🧠 5 câu quiz từ NỘI DUNG VỪA HỌC
  ⏱️ 30 giây mỗi câu
  ✅ Kết quả + giải thích câu sai
  📸 Share kết quả cho bạn (viral)
```
- **Hiện tại:** Có nhưng transition chưa smooth
- **Target:** 1 tap → quiz bắt đầu ngay, không loading
- **Metric:** % users tạo quiz sau khi giải bài > 30%

---

## 5. COMPETITIVE ANALYSIS — TẠI SAO ĐÁNG SỢ KHÔNG?

### Đối thủ trực tiếp trong Zalo:
```
Hiện tại: KHÔNG CÓ AI làm EdTech Mini App trong Zalo đáng kể.
→ Blue ocean. Nhưng sẽ không lâu nếu không nhanh.
```

### Đối thủ gián tiếp:

| Đối thủ | Điểm mạnh | Điểm yếu (vs. Chat Hay) |
|---|---|---|
| **ChatGPT / Gemini** | AI mạnh nhất | Phải rời Zalo, không hiểu SGK VN, không tích lũy |
| **Google Classroom** | Miễn phí, trường dùng nhiều | Không có AI, chỉ là LMS, giáo viên phải tự tạo |
| **Azota** | Quiz VN phổ biến | Giáo viên phải tự tạo đề, không AI auto-generate |
| **VioEdu (Viettel)** | Vốn lớn, nội dung nhiều | Bài chung cho cả nước, không personalized, app riêng |
| **Quizizz** | Gamification hay | Phải vào web riêng, giáo viên setup, tiếng Anh |
| **PhotoMath** | OCR toán tốt | App riêng, không tích hợp Zalo, không có quiz/flashcard |

### Moat (hào nước bảo vệ):
1. **Network effect trong Zalo:** 1 học sinh share → 5 bạn dùng → lan cả lớp
2. **Data moat:** Càng nhiều user → AI hiểu SGK VN càng tốt → kết quả càng chính xác
3. **Switching cost:** Kho tài liệu + flashcard cá nhân → không bỏ được
4. **Zalo distribution:** Đối thủ muốn vào Zalo phải build Mini App từ đầu

---

## 6. PLATFORM RISK — RỦI RO VÀ PHÒNG VỆ

### 6.1 Rủi ro thật khi build trên Zalo:
- VNG đổi chính sách Mini App → app bị ảnh hưởng
- VNG tự build tính năng tương tự (có VioEdu/Viettel làm tiền lệ)
- Zalo thu commission trên payment → giảm margin
- Zalo rate-limit API hoặc block tính năng
- **Không sở hữu dữ liệu liên lạc user** (Zalo giữ user_id)

### 6.2 Chiến lược phòng vệ — "Zalo = cửa trước, không phải nhà"

```
KIẾN TRÚC:
                    ┌─────────────┐
                    │  CORE TECH  │  ← CỦA BẠN, không ai lấy được
                    │  (Backend)  │
                    │ • AI Engine │
                    │ • User Data │
                    │ • Supabase  │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼────┐ ┌────▼─────┐ ┌────▼─────┐
        │  Zalo    │ │  Web App │ │ Telegram │
        │ Mini App │ │  (PWA)   │ │   Bot    │
        └──────────┘ └──────────┘ └──────────┘
         Kênh chính   Backup       Mở rộng
```

### 6.3 Hành động phòng vệ cụ thể:

| Hành động | Khi nào | Mục đích |
|---|---|---|
| Thu thập email/SĐT khi đăng ký Pro | Từ khi có monetization | Liên lạc user ngoài Zalo |
| Build Web App (PWA) cùng backend | Song song, ưu tiên trung bình | Insurance nếu mất Zalo |
| Giữ backend platform-agnostic | Luôn luôn | Core tech không phụ thuộc Zalo |
| Lưu data trên Supabase (CỦA MÌNH) | Đã làm ✅ | Zalo không lấy được data |
| Có thể thêm Telegram bot sau | Khi có 10K users | Giảm phụ thuộc 1 platform |

### 6.4 Nguyên tắc vàng:
> **Dùng platform lớn để CÓ USERS → kéo users vào hệ sinh thái RIÊNG → nếu mất platform, không mất users.**

---

## 7. MONETIZATION — KIẾM TIỀN THẾ NÀO?

### 7.1 Mô hình Freemium:

| Tier | Giá | Đối tượng | Được gì |
|---|---|---|---|
| **Free** | 0đ | Mọi học sinh | 3 lần giải bài/ngày, 2 tóm tắt/ngày, quiz cơ bản |
| **Pro Student** | 49K-79K/tháng | Học sinh cần nhiều hơn | Unlimited giải bài, quiz, flashcard, kho lưu trữ |
| **Parent Pack** | 99K/tháng | Phụ huynh mua cho con | Pro + báo cáo tiến độ gửi qua Zalo cho phụ huynh |
| **School License** | 2-5M/tháng | Trường (SAU KHI có traction) | Bulk accounts + teacher analytics |

### 7.2 Tại sao Parent Pack là Gold Mine:
```
Phụ huynh Việt Nam:
├── Chi 200-500K/buổi cho gia sư → 79K/tháng = RẺ HƠN 1 buổi
├── Đã có Zalo, đã quen thanh toán
├── Nhận báo cáo "con học gì hôm nay" → yên tâm → tiếp tục trả tiền
└── Bạn không bán cho học sinh, bạn bán CHO PHỤ HUYNH
```

### 7.3 Viral loop tự nhiên = $0 CAC:
```
Học sinh A giải bài → share bài giải vào nhóm lớp
→ 30 bạn thấy → 10 bạn click → 5 bạn dùng
→ 3 bạn về nhà: "Mẹ ơi mua Pro cho con"
→ 3 × 79K = 237K MRR từ 1 học sinh ban đầu
→ Chi phí marketing: 0 đồng
```

---

## 8. ROADMAP — LÀM GÌ, THỨ TỰ NÀO?

### Phase 1: Nail the Core (2-4 tuần) 🔥 ĐANG LÀM
```
Mục tiêu: 3 core flows phải CỰC NHANH, CỰC MƯỢT, CỰC ĐẸP
KPI: 1 học sinh dùng xong → nói "WOW" → share cho bạn

Việc cần làm:
├── ✅ Fix Zalo Share Intent (Flow #1: Forward to Learn)
├── ✅ Tối ưu tốc độ Snap & Solve < 10 giây (Flow #2)
├── ✅ Smooth Quick Quiz flow (Flow #3)
├── ✅ Refactor file-processing.tsx (1388 dòng → tách components)
├── ✅ Cleanup 3 bản file-processing trùng
├── ✅ Fix TypeScript any types
└── ✅ Polish UI/UX cho 3 flows chính

KHÔNG LÀM:
├── ❌ Teacher Dashboard
├── ❌ Leaderboard phức tạp
├── ❌ B2B multi-tenancy
├── ❌ Coin system phức tạp
└── ❌ Bất kỳ feature mới nào
```

### Phase 2: Viral Engine (tháng 2-3)
```
Mục tiêu: 1 user → kéo 5 users tự nhiên
KPI: 1,000 active users

Việc cần làm:
├── Share bài giải đẹp qua Zalo (viral card có branding Chat Hay)
├── "Mở Chat Hay" CTA trong shared content
├── Referral tracking (ai invite ai)
├── Notification nhắc ôn bài (push qua Zalo OA)
└── Polish onboarding flow (first-time user → WOW trong 30 giây)
```

### Phase 3: Monetize (tháng 3-4)
```
Mục tiêu: Revenue > 0
KPI: 50 paying subscribers, MRR 3-5 triệu VNĐ

Việc cần làm:
├── Free limit (3 lần/ngày) → upsell Pro
├── ZaloPay subscription (49K-79K/tháng)
├── Thu thập email/SĐT khi mua Pro
├── Parent Report qua Zalo OA
└── Build Web App (PWA) song song — backup channel
```

### Phase 4: Scale (tháng 5-8)
```
Mục tiêu: Product-market fit rõ ràng
KPI: 10,000 users, MRR 20-50 triệu VNĐ

Việc cần làm:
├── Parent Pack (báo cáo chi tiết cho phụ huynh)
├── AI cá nhân hóa (biết học sinh yếu chương nào)
├── Pitch VNG/Zalo cho partnership
├── Thêm Telegram bot (giảm platform risk)
└── School License (nếu trường tự tìm đến)
```

### Phase 5: B2B (tháng 9+, CHỈ KHI có traction B2C)
```
Điều kiện: > 5,000 active users + > 100 paying subscribers
Lý do: Lúc này trường/giáo viên TỰ TÌM ĐẾN, không phải mình đi bán

Việc cần làm:
├── Teacher Dashboard
├── Class management
├── Bulk student import
├── Analytics cho trường
└── Multi-tenancy database
```

---

## 9. METRIC QUAN TRỌNG NHẤT

> **"Từ lúc mở Chat Hay đến lúc HIỂU BÀI mất bao lâu?"**
> **Target: < 2 phút** cho 1 bài tập / 1 tài liệu

### Metrics theo thứ tự ưu tiên:

| # | Metric | Target | Tại sao quan trọng |
|---|---|---|---|
| 1 | **Time to Value** | < 2 phút | User phải WOW nhanh nhất có thể |
| 2 | **D1 Retention** | > 40% | Ngày mai có quay lại không? |
| 3 | **D7 Retention** | > 20% | 1 tuần sau còn dùng không? |
| 4 | **Viral Coefficient** | > 1.0 | 1 user kéo > 1 user mới? |
| 5 | **Share Rate** | > 15% | Bao nhiêu % user share bài giải? |
| 6 | **Conversion Free→Pro** | > 3% | Khi có monetization |

---

## 10. QUYẾT ĐỊNH ĐÃ ĐƯA RA

| Quyết định | Lý do | Ngày |
|---|---|---|
| B2C trước, B2B sau | B2B cần case study, cần traction trước | 2026-05-09 |
| Không build LMS features | Google Classroom/Azota đã thắng, không cạnh tranh | 2026-05-09 |
| Focus 3 core flows, không thêm feature | Mài sắc > mở rộng ở giai đoạn này | 2026-05-09 |
| Bán cho phụ huynh, không bán cho học sinh | PH có tiền, có motivation, có Zalo | 2026-05-09 |
| Giữ Zalo là kênh chính nhưng không phụ thuộc 100% | Platform risk. Cần web app backup + thu email/SĐT | 2026-05-09 |
| Hoãn Teacher Dashboard, Leaderboard, Coin phức tạp | Không phải core value, phân tán focus | 2026-05-09 |

---

*💡 Hướng dẫn cho AI: Đọc file này TRƯỚC khi đề xuất feature mới. Mọi đề xuất phải align với 3 core flows và positioning ở trên. Nếu feature không giúp "nhận bài trên Zalo → xử lý xong trong 2 phút" thì KHÔNG LÀM.*
