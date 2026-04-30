# 📚 AI Learning (Study Mode) — Technical Overview

## 🎯 What It Does

Converts exam documents (PDF/DOCX/Images) into **interactive quizzes** and **spaced repetition flashcards** directly inside Zalo. Zero friction: students send document → AI generates questions → study immediately.

**Key Features:**
- Automatic mode detection (`STUDY_MATERIAL` vs business docs)
- Quiz generation with multiple choice, explanations, difficulty
- Flashcard with SM-2 spaced repetition algorithm
- Session persistence (24h TTL)
- Premium gating (3 free sessions/day)
- Study analytics tracking

## 🏗️ Architecture

```
Zalo Message → Webhook → handle_zalo_text()
                         ↓
                Document upload? → handle_zalo_file()
                         ↓
                summarize_text_structured()
                → mode_detector.detect_mode()
                → document_type = "education"
                         ↓
                build_summary_buttons()
                → Quiz / Flashcard buttons
                         ↓
                User taps button
                         ↓
                start_quiz_session() / start_flashcard_session()
                → AI generates questions/flashcards
                → save_study_session()
                → Interactive Q&A flow
```

### Core Modules

| Module | Responsibility |
|--------|----------------|
| `services/mode_detector.py` | Classify document type (education vs business vs general) |
| `services/ai_summarizer.py` | Hybrid AI routing (DeepSeek for text, Gemini for vision), includes `summarize_text_structured()` |
| `services/study_engine.py` | `QuizSession` and `FlashcardSession` state machines |
| `services/db_service.py` | Session storage (persistent in Supabase + memory fallback), Q&A counter, premium limit tracking |
| `services/study_analytics.py` | Completion tracking, score metrics |
| `zalo_webhook.py` | Main routing, webhook handlers, premium gating |

## 🧪 Testing

```bash
# Unit tests
python tests/test_study_engine.py        # 23 tests
python tests/test_db_service.py          # 3 tests

# Integration tests
python tests/integration_study_mode.py  # Full flow: mode detect → AI → session

# Edge cases
python tests/test_edge_cases.py          # 11 tests (empty, malformed, cleanup)

# Document type detection
python tests/test_ai_summarizer_document_type.py

# Performance benchmark
python tests/benchmark_performance.py   # Latency & cost comparison
```

**All tests pass:** ✅ 40/40

## 🔧 Configuration

```python
# config.py
FREE_STUDY_SESSIONS_PER_DAY = 3   # Premium gating
FREE_DAILY_LIMIT = 5              # Q&A limit (not used for study mode)
DEEPSEEK_MODEL = "deepseek-v4-flash"
```

## 🗄️ Database Schema (Supabase)

Study mode tables (created via `migrations/002_add_study_tables.sql`):

**study_sessions** – Active study sessions with 24h TTL
```sql
user_id TEXT NOT NULL,
doc_id TEXT NOT NULL,
mode TEXT NOT NULL CHECK (mode IN ('quiz', 'flashcard')),
state JSONB NOT NULL,
created_at TIMESTAMPTZ DEFAULT NOW(),
expires_at TIMESTAMPTZ,
updated_at TIMESTAMPTZ DEFAULT NOW()
-- Primary key: (user_id) via upsert
-- Indexes: user_id+doc_id, user_id+mode, expires_at
```

**quiz_scores** – Quiz completion history
```sql
user_id TEXT NOT NULL,
doc_id TEXT NOT NULL,
quiz_id TEXT NOT NULL,  -- Hash of questions
score INTEGER NOT NULL,
total_questions INTEGER NOT NULL,
percentage REAL GENERATED AS (score * 100.0 / total_questions) STORED,
time_seconds INTEGER,
completed_at TIMESTAMPTZ DEFAULT NOW()
```

**flashcard_progress** – Spaced repetition tracking (SM-2)
```sql
user_id TEXT NOT NULL,
doc_id TEXT NOT NULL,
card_index INTEGER NOT NULL,
card_content_hash TEXT NOT NULL,
reviewed_at TIMESTAMPTZ DEFAULT NOW(),
remembered BOOLEAN NOT NULL,
next_review_at TIMESTAMPTZ NOT NULL,
ease_factor REAL DEFAULT 2.5,
interval_days INTEGER DEFAULT 1,
review_count INTEGER DEFAULT 1
```

**Note:** `study_sessions` is the only table actively used in Week 5. `quiz_scores` and `flashcard_progress` are planned for future persistent analytics.

## 📊 Analytics

In-memory store (`services/study_analytics.py`):
- Sessions started/completed
- Quiz scores distribution
- Flashcard retention rate
- Logged via `logger.info()`

Future: Persist to Supabase `study_analytics` table.

## 🚀 Deployment

See `DEPLOYMENT_CHECKLIST.md` for full guide.

**Quick start:**
```bash
pip install -r requirements.txt
cp .env.example .env  # Fill in API keys
uvicorn zalo_webhook:app --host 0.0.0.0 --port 8000
```

## 🐛 Known Issues

- **Single active session per user** – Last write wins if user starts multiple sessions (intentional for MVP)
- No payment integration yet (PREMIUM message stub)
- PDF OCR limited to 10 pages

## 📈 Roadmap

- **Week 5:** Persist sessions to Supabase
- **Week 6:** Payment gateway (MoMo/ZaloPay)
- **Week 7:** Mobile app wrapper (React Native)
- **Week 8:** Soft launch with 100 students

---

**Status:** Production Ready ✅  
**Last Updated:** 2025-04-30
