# 🧠 CHAT HAY: PROJECT MEMORY & STATE
> **Mục đích:** File này lưu trữ trạng thái toàn bộ dự án. AI ĐỌC FILE NÀY TRƯỚC KHI LÀM BẤT CỨ ĐIỀU GÌ để hiểu rõ ngữ cảnh, tránh phá code cũ, và tiết kiệm token.
> **Cập nhật lần cuối:** 2026-05-09

---

## 📁 1. CẤU TRÚC DỰ ÁN TỔNG QUAN

Dự án "Chat Hay" gồm **2 repo chính** nằm cạnh nhau trong thư mục `read AI/`:

```
read AI/
├── chat-hay/                    # ← FRONTEND (Zalo Mini App)
│   ├── mini-app/                # ← ĐANG ACTIVE CODE (Bản chính)
│   │   ├── src/
│   │   │   ├── pages/           # 7 trang UI chính
│   │   │   ├── components/      # 5 component dùng chung
│   │   │   ├── services/        # 4 service gọi API backend
│   │   │   ├── hooks/           # 3 custom hooks
│   │   │   ├── contexts/        # 1 React Context (SharedFile)
│   │   │   ├── utils/           # 1 utility (greeting)
│   │   │   └── css/             # app.scss (22KB design system)
│   │   ├── .env                 # VITE_API_URL=http://localhost:8000
│   │   └── package.json         # React 18, Vite, zmp-sdk, jotai
│   ├── src/                     # Bản cũ (KHÔNG DÙNG, giữ để tham khảo)
│   ├── AI_RULES.md              # Luật cấm kỵ cho AI
│   ├── PROJECT_STATE.md         # File này
│   └── MASTER_PLAN_B2B.md       # Chiến lược kinh doanh
│
└── zalo-doc-bot/                # ← BACKEND (FastAPI + Python)
    ├── zalo_webhook.py          # Main server (3400+ dòng, 156KB)
    ├── config.py                # Cấu hình: Gemini, DeepSeek, Supabase, FPT.AI
    ├── services/                # 16 service files
    │   ├── ai_summarizer.py     # AI tóm tắt (Gemini + DeepSeek hybrid)
    │   ├── db_service.py        # Supabase database (39KB)
    │   ├── rag_service.py       # RAG Q&A pipeline (Gemini Embedding)
    │   ├── study_engine.py      # Quiz + Flashcard SM-2 engine
    │   ├── coin_service.py      # Hệ thống Coin/Xu
    │   ├── document_parser.py   # Parse PDF/Word/Excel/Image
    │   ├── solve_service.py     # Giải bài tập từ ảnh
    │   ├── tts_service.py       # Text-to-Speech (FPT.AI)
    │   ├── token_store.py       # Zalo OAuth token management
    │   ├── zalopay_service.py   # ZaloPay thanh toán
    │   ├── broadcast_service.py # Broadcast message hàng loạt
    │   ├── mode_detector.py     # Phát hiện loại tài liệu (education/business)
    │   └── study_analytics.py   # Phân tích học tập
    ├── requirements.txt         # FastAPI, Gemini, Supabase, PyMuPDF, pdfplumber...
    ├── Dockerfile               # Deploy container
    └── railway.toml             # Railway deployment config
```

---

## 🏗️ 2. TECH STACK CHI TIẾT

### Frontend (mini-app/)
| Thành phần | Công nghệ | Ghi chú |
|---|---|---|
| **Framework** | React 18.3 + TypeScript | Strict mode |
| **Bundler** | Vite 5.2 | SPA mode với `spaFallback()` plugin |
| **UI Kit** | zmp-ui 1.11.12 | Zalo Mini App UI components |
| **SDK** | zmp-sdk 2.49.5 | Zalo SDK cho auth, share, haptic |
| **State** | Jotai (atom-based) | Dùng cho auth state |
| **Styling** | Custom SCSS (app.scss, 22KB) | **KHÔNG DÙNG TAILWIND trong JSX** |
| **Router** | React Router v6 via `ZMPRouter` + `AnimationRoutes` | Catch-all `*` → redirect `/` |
| **Font** | Inter (Google Fonts) | Qua CSS variables |
| **Icons** | Custom SVG components (`icons.tsx`) | 18 icon tự vẽ |

### Backend (zalo-doc-bot/)
| Thành phần | Công nghệ | Ghi chú |
|---|---|---|
| **Server** | FastAPI + Uvicorn | Port 8000, CORS enabled |
| **AI chính** | Google Gemini (gemini-2.0-flash) | Multi-key rotation (3 keys) |
| **AI phụ** | DeepSeek V4 Flash | Cho text tasks (rẻ 9x so với Gemini) |
| **Database** | Supabase (PostgreSQL) | Documents, users, coins, streak, sessions |
| **File Parse** | PyMuPDF + pdfplumber + python-docx + openpyxl | PDF, Word, Excel |
| **OCR** | Gemini Vision API | Đọc chữ từ ảnh |
| **TTS** | FPT.AI (voice: banmai) | Text-to-speech tiếng Việt |
| **Embedding** | Gemini Embedding API | Cho RAG pipeline (không dùng sentence-transformers) |
| **Payment** | ZaloPay SDK | Nạp xu |
| **Deploy** | Railway (production) | Auto-deploy từ Git |
| **Token Mgmt** | Auto-refresh Zalo OAuth | Proactive refresh mỗi 30 phút |

---

## ✅ 3. TÍNH NĂNG ĐÃ HOÀN THÀNH (COMPLETED)

### 3.1 Frontend — Các trang UI

- [x] **Hub Page (`Index.tsx`, 297 dòng):** Trang chủ điều hướng trung tâm. Hero gradient header với logo + streak badge. 3 stat cards (Xu, Tài liệu, Streak). 3 entry point lớn: Chat Hay AI (solve-problem), Tóm tắt & Giải thích (file-processing), AI Learning. Quick access bar (Vault, Flashcard, Quiz). Daily tip.
- [x] **File Processing Page (`file-processing.tsx`, 1388 dòng):** Trang xử lý file chính. Upload file (PDF/Word/Image) → AI tóm tắt. Camera capture + Gallery upload. Giải bài tập AI (chụp ảnh đề → AI giải từng bước). SummaryWithQA component tích hợp (tóm tắt + Q&A trong cùng 1 panel). Text selection → "Hỏi AI về đoạn này" tooltip. TTS đọc tóm tắt (Web Speech API). Share tóm tắt qua Zalo. Rename/Delete document. Bảng xếp hạng, Nhóm học tập, Chế độ giáo viên (placeholder UI). Nhắc ôn bài toggle (localStorage).
- [x] **AI Learning Page (`ai-learning.tsx`, 411 dòng):** Dashboard học tập. Role switcher (Học Sinh / Giáo Viên). Coin Wallet card (gradient, animated number). 3 learning stats (Tài liệu, Flashcard, Quiz count). 6 Student features + 4 Teacher features (Bento grid cards). Streak Progress (7-day visual). Camera → Quiz shortcut. Daily tip (Adaptive Learning SM-2).
- [x] **Quiz Page (`quiz.tsx`, 509 dòng):** Quiz timer 30 giây mỗi câu. Sound effects (Web Audio API: correct/wrong/tick). Progress bar + Category badge. Skip question + Explanation. Quiz Done screen (Score, Share, Review sai, Next doc suggestion). Review Mode xem lại câu sai chi tiết. Session persistence (sessionStorage).
- [x] **Flashcard Page (`flashcard.tsx`, 272 dòng):** 3D flip card (CSS transform). SM-2 spaced repetition (Again/Hard/Good/Easy rating). Swipe navigation (touch gesture). Shuffle cards. Dot indicators. Session tracking via backend. Difficulty badges (Dễ/Trung bình/Khó).
- [x] **Solve Problem Page (`solve-problem.tsx`, 399 dòng):** Chat interface kiểu iMessage. Camera + Gallery upload ảnh đề bài. AI OCR + giải chi tiết (Đề bài → Steps → Đáp án). SolutionCard component. "Tạo Quiz ôn tập từ bài giải" button. Suggested prompts (Toán, Tích phân, Hóa học). Typing dots animation.
- [x] **Vault Page (`vault.tsx`, 213 dòng):** Kho tài liệu. Search bar + Filter chips (Tất cả/PDF/Word/PPT). Document list (emoji icon theo loại, ngày, kích thước). Delete document. Responsive.

### 3.2 Frontend — Components & Hooks & Services

- [x] **Layout (`layout.tsx`):** SharedFileProvider wrapper. API base URL setup từ `.env`. Zalo Share Intent handling (nhận file share từ Zalo chat). Loading splash screen. 7 routes đã đăng ký.
- [x] **Icons (`icons.tsx`):** 18 custom SVG icon components (IconBrain, IconCoin, IconFire, IconFlashcard, IconQuiz, IconCheck, IconChevronLeft/Right, IconLightbulb, IconRefresh, IconAlertTriangle, IconDoc, IconUpload, IconSearch, IconFolder, IconCamera, IconImage, IconInbox).
- [x] **EmptyState (`EmptyState.tsx`):** Reusable empty state component (emoji, title, desc, primary + secondary action buttons).
- [x] **Logo (`logo.tsx`):** Custom SVG logo (9.9KB).
- [x] **Clock (`clock.tsx`):** Clock component.
- [x] **useAuth hook:** Jotai atom-based. Zalo SDK token → Backend auth exchange → localStorage cache. Fallback local dev mode (`local_dev_user_001`). Timeout 3s cho Zalo SDK (tránh hang ngoài app Zalo).
- [x] **useAnimatedNumber hook:** Cubic easing counter animation. Dùng chung cho Hub, File Processing, AI Learning.
- [x] **useSound hook:** Web Audio API, 3 sounds: `playCorrectSound()` (ascending C5→E5→G5), `playWrongSound()` (descending sawtooth), `playTickSound()` (1000Hz tick for timer warning).
- [x] **SharedFileContext:** React Context cho Zalo Share Intent (nhận file từ Zalo chat → tự upload).
- [x] **API Client (`api.ts`):** Custom fetch wrapper. GET/POST/PUT/DELETE + POST FormData. Token + UserId headers. Error handling.
- [x] **CoinService:** Balance, History, Earn, Invite friend.
- [x] **DocumentService:** Upload & Process, Auto-generate, CRUD documents, Get flashcards/quiz, Solve problem, Generate quiz from solution, Rename.
- [x] **StudyService:** Start quiz/flashcard session, Answer quiz, Get result/review, SM-2 flashcard review, Get streak, Get progress, Share text generators.

### 3.3 Frontend — Design System (app.scss, 22KB)

- [x] CSS Variables đầy đủ: colors, gradients, typography, spacing, radius, shadows, transitions.
- [x] Animation keyframes: `pulseGlow`, `floatOrb`, `scaleIn`, `fadeIn`, `slideUp`, `bounce`, `slideIn`, `shimmer`.
- [x] Component classes: `.ch-page`, `.ch-container`, `.ch-card`, `.ch-btn-primary/secondary`, `.ch-quiz-option`, `.ch-flashcard`, `.ch-progress`, `.ch-skeleton`, `.ch-toast`, `.ch-search`, `.ch-empty`, `.ch-doc-item`, `.ch-explanation`, `.ch-badge`, `.ch-fab`, `.ch-dots`, `.ch-stat-pill`, `.ch-stagger`, `.ch-bento-card`.
- [x] Flashcard 3D CSS (`.ch-flashcard-scene`, `.ch-flashcard-face`, `.flipped`).

### 3.4 Backend — API Endpoints

- [x] **Zalo OA Webhook** (`/webhook`): Nhận message, file, image từ Zalo. Tóm tắt, Q&A, OCR, TTS. Study mode (Quiz/Flashcard) qua Zalo chat. Rate limiting (5 lượt/ngày free). Cooldown chống spam (15s).
- [x] **Mini App API** (`/api/miniapp/*`):
  - `POST /auth` — Zalo access token → user_id
  - `GET/POST /documents` — CRUD tài liệu
  - `POST /auto-generate` — Upload → tự động tạo summary + quiz + flashcard
  - `POST /solve-problem` — Chụp ảnh đề → AI giải
  - `POST /generate-quiz-from-solution` — Tạo quiz từ bài giải
  - `POST /quiz/start` + `/quiz/answer` + `GET /quiz/{id}/result` + `/quiz/{id}/review`
  - `POST /flashcard/start` + `/flashcard/review` (SM-2)
  - `GET /streak` — Chuỗi học tập
  - `GET /coin/balance` + `/coin/history` + `POST /coin/earn` + `/coin/invite`
  - `POST /chat/ask` — RAG Q&A về tài liệu
  - `GET /documents/{id}/progress` — Tiến độ học tập
- [x] **Zalo Token Management:**
  - Auto-refresh proactive mỗi 30 phút
  - Retry khi token expired (-216)
  - DB persistence (Supabase)
  - Sync token giữa local ↔ Railway

### 3.5 Backend — AI Services

- [x] **Hybrid AI Routing:** Gemini cho vision/image tasks, DeepSeek cho text tasks (rẻ hơn 9x). Auto-fallback khi 1 provider lỗi.
- [x] **Document Summarization:** Structured output (overview, points[], action_items[], suggested_questions[], document_type). Hỗ trợ PDF (text + image-based), Word (.doc/.docx), Excel (.xlsx), Image.
- [x] **RAG Q&A Pipeline:** Gemini Embedding → vector search → context-aware answer. Giới hạn 5 câu/document.
- [x] **Study Engine:** Quiz session management. Flashcard SM-2 spaced repetition. Streak tracking (current + longest).
- [x] **Coin System:** Earn coins (quiz complete, streak maintain, share). Spend coins (premium features). Transaction history. Invite friend bonus.
- [x] **OCR:** Gemini Vision → extract text from images. Vietnamese + English support.
- [x] **TTS:** FPT.AI Vietnamese TTS (voice: banmai). Audio cleanup after send.
- [x] **ZaloPay Integration:** Create payment order, Verify callback.

---

## ✅ BETA TEST PREP (2026-05-16)

### Đã hoàn thành cho Beta Test:
- [x] **Paste ảnh từ clipboard** - Hỗ trợ Ctrl+V trên 4 trang (Upload, Solve Problem, File Processing, AI Learning)
- [x] **Feature-specific rate limits** - Giới hạn riêng cho từng tính năng:
  - Giải bài tập: 10/ngày
  - AI Learning: 5/ngày  
  - Quiz: 10/ngày
  - Flashcard: 10/ngày
- [x] **Build verification** - Frontend build thành công không lỗi
- [x] **Backend API verification** - Tất cả imports và config hoạt động
- [x] **Chi phí beta test:** ~172K VNĐ cho 200 học sinh trong 30 ngày

---

## 🚧 4. ĐANG LÀM / CẦN LÀM (TODO / WIP)

### Ưu tiên cao (B2C — Cần hoàn thiện để tạo Case Study)
- [ ] Fix các trang Teacher features placeholder (Dashboard Lớp Học, Giao Bài Qua Zalo → đang `alert("Tính năng sắp ra mắt!")`)
- [ ] Hoàn thiện Bảng xếp hạng tuần (Ranking) — hiện là UI placeholder trong file-processing.tsx
- [ ] Hoàn thiện Nhóm học tập (Group Mode) — hiện là UI placeholder
- [ ] Tối ưu flow Gamification: Coin earn khi hoàn thành quiz/flashcard trên Mini App (hiện chỉ có backend API, chưa call từ frontend)
- [ ] Test và fix luồng Zalo Share Intent (nhận file share từ Zalo chat → tự upload)
- [ ] Cải thiện UX khi không có internet (offline state, cached data)

### Ưu tiên trung bình (B2B Prep)
- [ ] Cấu trúc lại Database hỗ trợ Multi-tenancy (Thêm `school_id`, `class_id`, `role` vào Supabase)
- [ ] Xây dựng Teacher Dashboard MVP (Vite + React riêng, hoặc module admin)
- [ ] API endpoints cho Teacher: Quản lý lớp, Assign quiz, Xem analytics lớp
- [ ] Import học sinh bằng Excel/CSV

### Ưu tiên thấp
- [ ] ZaloPay payment flow hoàn chỉnh trên Mini App (hiện đang `alert("Nạp xu qua ZaloPay...")`)
- [ ] Push notification nhắc ôn bài (đã có toggle UI, chưa có backend)
- [ ] Leaderboard API (backend chưa có)
- [ ] Export kết quả quiz ra PDF

---

## 🐛 5. BUGS / ISSUES ĐÃ BIẾT (KNOWN ISSUES)

- **`file-processing.tsx` quá lớn (1388 dòng, 63KB):** Cần refactor tách thành sub-components (SolvePanel, DocumentList, UploadArea...).
- **Có 3 phiên bản file-processing:** `file-processing.tsx` (active, 63KB), `file-processing-new.tsx` (36KB), `file-processing-final.tsx` (36KB) — cần cleanup bản cũ.
- **`zalo_webhook.py` quá lớn (3400+ dòng, 156KB):** Monolith, nên tách thành router modules.
- **Một số TypeScript `any` types:** `docs: any[]`, `reviewData: any`, `lastSolution: any` — cần type properly.
- **Quiz Page dùng cả `zmp-ui` Icon lẫn custom Icon:** Không nhất quán (import `Icon` from `zmp-ui` + custom icons).
- **`tailwindcss` vẫn nằm trong devDependencies** nhưng không nên dùng trong JSX (chỉ dùng cho compile nếu cần).

---

## 🏗️ 6. LƯU Ý KỸ THUẬT QUAN TRỌNG (TECH NOTES)

### ⛔ TUYỆT ĐỐI KHÔNG ĐƯỢC THAY ĐỔI:
1. **SPA Fallback Plugin** trong `vite.config.mts` — Plugin `spaFallback()` PHẢI là plugin đầu tiên. Nó fix lỗi màn hình trắng 404 trên Zalo wrapper.
2. **Script src** trong `src/index.html` — PHẢI là `<script type="module" src="/src/app.tsx">`. KHÔNG đổi sang `./app.tsx`.
3. **Catch-All Route** trong `layout.tsx` — `<Route path="*" element={<Navigate to="/" replace />} />` PHẢI ở cuối `<AnimationRoutes>`.
4. **BottomNavigation** — Hiện tại KHÔNG dùng bottom nav (Hub-based navigation). Nếu quay lại bottom nav, PHẢI có prop `fixed`.

### 📌 Quy tắc code:
- **KHÔNG dùng Tailwind CSS class trong JSX** (ví dụ: `className="flex mt-4"`). Dùng inline style hoặc class từ `app.scss`.
- **Dùng CSS variables** từ `:root` trong `app.scss` (ví dụ: `var(--color-primary)`, `var(--radius-xl)`).
- **Card layout** dùng class `ch-card` hoặc `ch-card ch-card-interactive`.
- **API base URL** được set từ `VITE_API_URL` trong `.env`. Hiện tại: `http://localhost:8000` (dev), production set khác.
- **Auth flow:** Zalo SDK → access_token → POST `/api/miniapp/auth` → nhận `user_id` → cache localStorage.
- **Backend AI routing:** Gemini cho vision/multimodal, DeepSeek cho text-only. Auto-fallback nếu 1 provider down.

### 📂 File nào là bản chính:
- **Frontend chính:** `chat-hay/mini-app/src/` ← CODE Ở ĐÂY
- **Frontend cũ (KHÔNG DÙNG):** `chat-hay/src/` ← ĐỪNG ĐỤNG VÀO
- **Backend chính:** `zalo-doc-bot/zalo_webhook.py` + `zalo-doc-bot/services/`

---

## 📊 7. SỐ LIỆU DỰ ÁN

| Metric | Giá trị |
|---|---|
| Tổng số file frontend (mini-app/src) | ~25 files |
| Tổng dòng code frontend | ~4,500+ dòng TSX/TS |
| Tổng dòng code backend | ~5,000+ dòng Python |
| File lớn nhất (FE) | file-processing.tsx (1,388 dòng) |
| File lớn nhất (BE) | zalo_webhook.py (3,410 dòng) |
| CSS design system | app.scss (22,586 bytes) |
| Số trang UI | 7 trang |
| Số API endpoints (Mini App) | ~20 endpoints |
| Dependencies (FE) | 7 production + 10 dev |
| Dependencies (BE) | 15 packages |

---

*💡 Hướng dẫn cho AI: Đọc file này TRƯỚC khi code. Khi hoàn thành tính năng, chuyển từ mục TODO lên mục COMPLETED. Khi phát hiện bug mới, thêm vào mục KNOWN ISSUES. KHÔNG BAO GIỜ tự ý sửa các mục trong phần "TUYỆT ĐỐI KHÔNG ĐƯỢC THAY ĐỔI".*
