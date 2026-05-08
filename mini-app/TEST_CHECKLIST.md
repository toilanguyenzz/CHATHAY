# 🧪 AI LEARNING PAGE — TEST CHECKLIST

## 📱 CÁCH TEST NHANH

### **1. Mở Browser**
```
http://localhost:5173
```

### **2. Kiểm tra từng mục**

| STT | Kiểm tra | Expected result | Pass/Fail |
|-----|----------|-----------------|-----------|
| 1 | Page load | Hiển thị loading → sau 2-3s hiện UI | |
| 2 | Header | "AI LEARNING" + role switcher (Student/Teacher) | |
| 3 | Coin Wallet | Gradient card với số Coin (0 nếu chưa nạp) | |
| 4 | Stats Row | 3 pills: Tài liệu (0), Flashcard (0), Quiz (0) | |
| 5 | Primary Card | 🚀 "Bắt đầu Study Session" với gradient purple-pink | |
| 6 | Tool Grid | 2x2 grid: Flashcard, Quiz, Hỏi AI, Giải bài tập | |
| 7 | Role switch | Click Teacher → cards thay đổi | |
| 8 | Streak Card | "Chuỗi học tập: 0 ngày" + 7-day calendar | |
| 9 | Daily Tip | Adaptive Learning tip ở dưới cùng | |

### **3. Test Interactions**

- **Click Primary Card** → Nên chuyển sang `/quiz` (nếu có docs) hoặc `/file-processing`
- **Click Tool Cards** → Chuyển đến page tương ứng
- **Teacher role** → Click "Tạo Đề Thi" → `/file-processing`
- **Long press** (nếu có) → Hiển thị tooltip?

---

## 🐛 **KNOWN ISSUES**

### **Auth/Dev Mode**
- Nếu chưa đăng nhập Zalo, page sẽ chạy ở **LOCAL DEV MODE** với mock user
- Console sẽ hiện: `🧪 Running in LOCAL DEV mode with mock user`

### **Backend API**
- Cần start backend: `cd zalo-doc-bot && python -m uvicorn zalo_webhook:app --reload --port 8000`
- Nếu API lỗi → Stats sẽ show 0, coins show 0
- Click cards → Có thể redirect đến login/upload

### **CORS**
- Backend phải cho phindre `http://localhost:5173`
- Trong `zalo_webhook.py` kiểm tra CORS middleware

---

## 🎯 **VISUAL INSPECTION**

### **Primary Card Should Look Like:**
```
┌────────────────────────────────────────┐
│  🚀  BẮT ĐẦU STUDY SESSION             │
│  📚 [Tên file] · Tự động tóm tắt...    │
│                                    ▶  │
└────────────────────────────────────────┘
```
- Gradient: Purple (#8B5CF6) → Pink (#EC4899)
- White text
- Floating orbs animation
- Shadow glow

### **Tool Grid Should Be:**
```
┌─────────┐ ┌─────────┐
│ 🗂️      │ │ 💬      │
│ Flash-  │ │ Hỏi AI │
│ card 3D │ │Chat w AI│
└─────────┘ └─────────┘
┌─────────┐ ┌─────────┐
│ 📝      │ │ 📸      │
│ Làm Quiz│ │Giải bài │
│         │ │tập     │
└─────────┘ └─────────┘
```

---

## 📊 **PERFORMANCE CHECK**

1. **Load time**: < 2s (lần đầu), < 1s (cached)
2. **FPS**: 60fps khi scroll
3. **No jank**: Cards should not lag on hover
4. **Bundle size**: Should be < 200KB gzipped

---

## 🔧 **DEBUGGING**

### **Open Console (F12)**
```
✅ Should see:
  "🔍 AI Learning Page: Mounting..."
  "✅ Data loaded: { coin: 0, docs: 0, streak: 0 }"

❌ Should NOT see:
  "Uncaught TypeError"
  "Failed to fetch"
```

### **Network Tab**
- `GET /api/miniapp/streak` → 200 OK
- `GET /api/miniapp/coin/balance` → 200 OK
- `GET /api/miniapp/documents` → 200 OK

---

## ✅ **PASS CRITERIA**

- [ ] Page loads within 3 seconds
- [ ] No console errors (only warnings OK)
- [ ] All 6 cards visible (Student) / 4 cards (Teacher)
- [ ] Primary card prominent (largest, gradient)
- [ ] Tool grid 2x2 layout
- [ ] Role switcher works
- [ ] Stats display correct numbers
- [ ] Clicking cards navigates correctly

---

## 🚨 **NẾU VẪN KHÔNG LOAD ĐƯỢC**

### **Step 1: Clear cache**
```bash
cd chat-hay/mini-app
rm -rf node_modules/.vite
npm run dev
```

### **Step 2: Check port conflict**
```bash
netstat -ano | grep 5173
# Nếu có process khác, kill nó
```

### **Step 3: Check dependencies**
```bash
npm install
```

### **Step 4: Build for production test**
```bash
npm run build
npm run preview
```

---

## 📈 **EXPECTED IMPROVEMENTS VS OLD**

| Metric | Old | New | Δ |
|--------|-----|-----|---|
| Cards count | 11 | 6 | -45% |
| Primary action visibility | Low | High | +200% |
| Decision time | ~8s | ~3s | -62% |
| Scroll length | ~800px | ~600px | -25% |

---

**Test và cho tôi biết kết quả!** 🚀
