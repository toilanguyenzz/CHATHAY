-- Migration 002: Add Study Mode Tables
-- Created: 2025-04-30

-- Enable UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- TABLE: study_sessions
-- Track active study sessions (quiz or flashcard)
-- =====================================================
CREATE TABLE IF NOT EXISTS study_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('quiz', 'flashcard')),
    state JSONB NOT NULL,  -- Serialized QuizSession/FlashcardSession state
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for study_sessions
CREATE INDEX IF NOT EXISTS idx_study_sessions_user_doc ON study_sessions(user_id, doc_id);
CREATE INDEX IF NOT EXISTS idx_study_sessions_user_mode ON study_sessions(user_id, mode);
CREATE INDEX IF NOT EXISTS idx_study_sessions_expires ON study_sessions(expires_at) WHERE expires_at IS NOT NULL;

-- Comment
COMMENT ON TABLE study_sessions IS 'Active study sessions for quiz and flashcard modes';
COMMENT ON COLUMN study_sessions.state IS 'Serialized session state (JSON)';

-- =====================================================
-- TABLE: quiz_scores
-- Store quiz completion records for progress tracking
-- =====================================================
CREATE TABLE IF NOT EXISTS quiz_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    quiz_id TEXT NOT NULL,  -- Hash of questions to identify same quiz
    score INTEGER NOT NULL CHECK (score >= 0),
    total_questions INTEGER NOT NULL CHECK (total_questions > 0),
    percentage REAL GENERATED ALWAYS AS (score * 100.0 / total_questions) STORED,
    time_seconds INTEGER,  -- Time taken to complete (null if abandoned)
    completed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for quiz_scores
CREATE INDEX IF NOT EXISTS idx_quiz_scores_user_doc ON quiz_scores(user_id, doc_id);
CREATE INDEX IF NOT EXISTS idx_quiz_scores_user_completed ON quiz_scores(user_id, completed_at DESC);
CREATE INDEX IF NOT EXISTS idx_quiz_scores_doc_user ON quiz_scores(doc_id, user_id);

-- Comments
COMMENT ON TABLE quiz_scores IS 'Quiz completion history for tracking user progress';
COMMENT ON COLUMN quiz_scores.quiz_id IS 'Hash of questions to group same quiz attempts';
COMMENT ON COLUMN quiz_scores.percentage IS 'Computed column: (score/total)*100';

-- =====================================================
-- TABLE: flashcard_progress
-- Track spaced repetition reviews (SM-2 algorithm)
-- =====================================================
CREATE TABLE IF NOT EXISTS flashcard_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    card_index INTEGER NOT NULL,  -- Position in flashcard set (1-based)
    card_content_hash TEXT NOT NULL,  -- Hash of front+back to identify card across sessions
    reviewed_at TIMESTAMPTZ DEFAULT NOW(),
    remembered BOOLEAN NOT NULL,  -- User marked "Nhớ rồi" or "Chưa nhớ"
    next_review_at TIMESTAMPTZ NOT NULL,  -- When to review next (spaced repetition)
    ease_factor REAL DEFAULT 2.5,  -- SM-2 ease factor (1.3-2.5)
    interval_days INTEGER DEFAULT 1,  -- Current interval in days
    review_count INTEGER DEFAULT 1  -- Number of times reviewed
);

-- Indexes for flashcard_progress
CREATE INDEX IF NOT EXISTS idx_flashcard_progress_user_card ON flashcard_progress(user_id, card_content_hash);
CREATE INDEX IF NOT EXISTS idx_flashcard_progress_next_review ON flashcard_progress(user_id, next_review_at) WHERE next_review_at <= NOW();
CREATE INDEX IF NOT EXISTS idx_flashcard_progress_doc ON flashcard_progress(doc_id);

-- Comments
COMMENT ON TABLE flashcard_progress IS 'Flashcard review history for spaced repetition algorithm';
COMMENT ON COLUMN flashcard_progress.card_content_hash IS 'Hash of front+back content to identify same card across sessions';
COMMENT ON COLUMN flashcard_progress.next_review_at IS 'Next scheduled review date (SM-2 algorithm)';

-- =====================================================
-- ROW LEVEL SECURITY (RLS) - Optional for multi-tenant
-- =====================================================
-- ALTER TABLE study_sessions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE quiz_scores ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE flashcard_progress ENABLE ROW LEVEL SECURITY;

-- Create policies (if using RLS)
-- CREATE POLICY "Users can view own study sessions" ON study_sessions FOR SELECT USING (auth.uid()::text = user_id);
-- CREATE POLICY "Users can insert own study sessions" ON study_sessions FOR INSERT WITH CHECK (auth.uid()::text = user_id);

-- =====================================================
-- FUNCTIONS: Cleanup expired sessions (cron job)
-- =====================================================
CREATE OR REPLACE FUNCTION cleanup_expired_study_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM study_sessions
    WHERE expires_at IS NOT NULL
      AND expires_at < NOW();

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_expired_study_sessions() IS 'Delete expired study sessions (run daily via cron)';

-- =====================================================
-- TRIGGER: Update updated_at timestamp
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_study_sessions_updated_at
    BEFORE UPDATE ON study_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- SAMPLE DATA (for testing only - remove in production)
-- =====================================================
-- INSERT INTO study_sessions (user_id, doc_id, mode, state, expires_at)
-- VALUES ('test_user', 'doc_test', 'quiz', '{"questions": []}'::jsonb, NOW() + INTERVAL '1 day');

-- INSERT INTO quiz_scores (user_id, doc_id, quiz_id, score, total_questions, time_seconds)
-- VALUES ('test_user', 'doc_test', 'quiz_abc123', 8, 10, 300);

-- INSERT INTO flashcard_progress (user_id, doc_id, card_index, card_content_hash, remembered, next_review_at)
-- VALUES ('test_user', 'doc_test', 1, 'hash123', true, NOW() + INTERVAL '3 days');
