-- =========================================================================
-- 🚀 CHAT HAY - FULL DATABASE SETUP SCRIPT
-- Copy và Run toàn bộ đoạn code này trong Supabase SQL Editor
-- =========================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==========================================
-- 1. BẢNG CƠ SỞ (BASE TABLES)
-- ==========================================

-- Bảng user_usage: Quản lý giới hạn lượt dùng và số dư coin
CREATE TABLE IF NOT EXISTS user_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    date TEXT NOT NULL, -- Định dạng YYYY-MM-DD
    action_type TEXT DEFAULT 'general',
    count INTEGER DEFAULT 0,
    study_count INTEGER DEFAULT 0,
    coin_balance INTEGER DEFAULT 0,
    UNIQUE(user_id, date, action_type)
);

-- Bảng user_state: Nhớ tài liệu user đang mở
CREATE TABLE IF NOT EXISTS user_state (
    user_id TEXT PRIMARY KEY,
    active_doc_id TEXT
);

-- Bảng documents: Lưu tài liệu, flashcards, quiz
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    text TEXT,
    summary TEXT,
    doc_type TEXT,
    timestamp DOUBLE PRECISION,
    flashcards JSONB DEFAULT '[]',
    quiz_questions JSONB DEFAULT '[]',
    content JSONB
);

-- ==========================================
-- 2. BẢNG HỌC TẬP (STUDY TABLES)
-- ==========================================

-- Bảng study_sessions: Phiên học đang diễn ra (Quiz/Flashcard)
CREATE TABLE IF NOT EXISTS study_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('quiz', 'flashcard')),
    state JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_study_sessions_user_doc ON study_sessions(user_id, doc_id);

-- Bảng quiz_scores: Điểm số Quiz
CREATE TABLE IF NOT EXISTS quiz_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    quiz_id TEXT NOT NULL,
    score INTEGER NOT NULL CHECK (score >= 0),
    total_questions INTEGER NOT NULL CHECK (total_questions > 0),
    percentage REAL GENERATED ALWAYS AS (score * 100.0 / total_questions) STORED,
    time_seconds INTEGER,
    completed_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_quiz_scores_user_doc ON quiz_scores(user_id, doc_id);

-- Bảng flashcard_progress: Thuật toán nhắc lại (Spaced Repetition)
CREATE TABLE IF NOT EXISTS flashcard_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
);

-- Bảng solved_problems: Lịch sử giải bài tập (Snap & Solve)
CREATE TABLE IF NOT EXISTS solved_problems (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    question TEXT NOT NULL,
    steps JSONB NOT NULL,
    answer TEXT NOT NULL,
    subject TEXT,
    difficulty TEXT,
    image_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==========================================
-- 3. BẢNG COIN (GAMIFICATION)
-- ==========================================

-- Bảng user_coin_balance: Số dư Coin riêng biệt
CREATE TABLE IF NOT EXISTS user_coin_balance (
    user_id TEXT PRIMARY KEY,
    balance INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bảng coin_transactions: Lịch sử nhận/tiêu Coin
CREATE TABLE IF NOT EXISTS coin_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    amount INTEGER NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('credit', 'debit')),
    reason TEXT NOT NULL,
    balance_after INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==========================================
-- 4. TRIGGERS & FUNCTIONS
-- ==========================================

-- Function cập nhật updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Gắn trigger cho bảng cần thiết
DROP TRIGGER IF EXISTS update_study_sessions_updated_at ON study_sessions;
CREATE TRIGGER update_study_sessions_updated_at
    BEFORE UPDATE ON study_sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_coin_balance_updated_at ON user_coin_balance;
CREATE TRIGGER update_user_coin_balance_updated_at
    BEFORE UPDATE ON user_coin_balance FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function dọn dẹp phiên học hết hạn
CREATE OR REPLACE FUNCTION cleanup_expired_study_sessions()
RETURNS INTEGER AS $$
DECLARE deleted_count INTEGER;
BEGIN
    DELETE FROM study_sessions WHERE expires_at IS NOT NULL AND expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
