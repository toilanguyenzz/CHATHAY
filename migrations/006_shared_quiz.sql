-- Migration 006: Shared Quiz System + User Profiles + Quiz Bookmarks
-- Mục tiêu: Cho phép GV tạo quiz công khai → HS vào làm qua link + Lấy tên Zalo thật

-- =====================================================
-- TABLE: user_profiles (Lưu thông tin Zalo thật)
-- =====================================================
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id TEXT PRIMARY KEY,
    display_name TEXT,              -- Tên thật từ Zalo
    avatar_url TEXT,                -- Avatar từ Zalo
    role TEXT DEFAULT 'student',    -- 'student' | 'teacher'
    zalo_phone TEXT,                -- Số điện thoại Zalo (nếu có)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_display_name ON user_profiles(display_name);

COMMENT ON TABLE user_profiles IS 'Thông tin người dùng từ Zalo API: tên thật, avatar, vai trò';
COMMENT ON COLUMN user_profiles.display_name IS 'Tên hiển thị từ Zalo (không cho phép fake)';
COMMENT ON COLUMN user_profiles.role IS 'Phân loại: học sinh hoặc giáo viên';

-- =====================================================
-- TABLE: shared_quizzes (Quiz công khai do GV tạo)
-- =====================================================
CREATE TABLE IF NOT EXISTS shared_quizzes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creator_id TEXT NOT NULL REFERENCES user_profiles(user_id),
    doc_id TEXT,                    -- Document gốc (nếu có)
    title TEXT NOT NULL,            -- "Sinh học - Chương 5: Tiến hóa"
    subject TEXT,                   -- sinh_hoc, lich_su, toan, ly, hoa, ...
    chapter TEXT,                   -- "Chương 5"
    share_code TEXT UNIQUE NOT NULL, -- Mã ngắn để share: "abc123"
    questions JSONB NOT NULL,       -- Mảng câu hỏi (copy từ documents.quiz_questions)
    is_active BOOLEAN DEFAULT TRUE,
    max_attempts INTEGER DEFAULT 1, -- Số lần làm tối đa per user (0 = không giới hạn)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ          -- Hết hạn (NULL = không hết hạn)
);

CREATE INDEX IF NOT EXISTS idx_shared_quizzes_creator ON shared_quizzes(creator_id);
CREATE INDEX IF NOT EXISTS idx_shared_quizzes_subject ON shared_quizzes(subject);
CREATE INDEX IF NOT EXISTS idx_shared_quizzes_share_code ON shared_quizzes(share_code);
CREATE INDEX IF NOT EXISTS idx_shared_quizzes_active ON shared_quizzes(is_active) WHERE is_active = TRUE;

COMMENT ON TABLE shared_quizzes IS 'Quiz công khai do GV tạo → HS share link để làm';
COMMENT ON COLUMN shared_quizzes.share_code IS 'Mã ngắn 6 ký tự để tạo link: chathay.vn/quiz/abc123';

-- =====================================================
-- TABLE: quiz_attempts (Kết quả làm bài của HS)
-- =====================================================
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id UUID REFERENCES shared_quizzes(id),
    user_id TEXT NOT NULL REFERENCES user_profiles(user_id),
    display_name TEXT NOT NULL,     -- TÊN ZALO THẬT (snapshot khi làm bài)
    avatar_url TEXT,                -- Avatar Zalo (snapshot)
    score INTEGER NOT NULL,
    total_questions INTEGER NOT NULL,
    percentage NUMERIC(5,2),        -- (score/total)*100
    time_seconds INTEGER,           -- Thời gian làm bài
    answers JSONB,                  -- Chi tiết từng câu: [{question_id, selected, correct, time_spent}]
    attempt_number INTEGER DEFAULT 1, -- Lần làm thứ mấy (nếu max_attempts > 1)
    completed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quiz_attempts_quiz ON quiz_attempts(quiz_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user ON quiz_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_completed ON quiz_attempts(completed_at DESC);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_score ON quiz_attempts(quiz_id, score DESC);

COMMENT ON TABLE quiz_attempts IS 'Kết quả làm bài quiz của HS (bao gồm quiz công khai)';
COMMENT ON COLUMN quiz_attempts.display_name IS 'Tên thật từ Zalo - không cho phép fake';

-- =====================================================
-- TABLE: user_quiz_bookmarks (Đánh dấu câu khó)
-- =====================================================
CREATE TABLE IF NOT EXISTS user_quiz_bookmarks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES user_profiles(user_id),
    quiz_id UUID REFERENCES shared_quizzes(id),
    doc_id TEXT,                    -- Hoặc document ID nếu là quiz riêng
    question_index INTEGER NOT NULL, -- Chỉ số câu hỏi (0-indexed)
    question_text TEXT NOT NULL,    -- Snapshot câu hỏi
    reason TEXT,                    -- "Không hiểu", "Hay lắm", "Thi thường xuyên"
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_quiz_bookmarks_unique ON user_quiz_bookmarks(user_id, quiz_id, question_index);
CREATE INDEX IF NOT EXISTS idx_quiz_bookmarks_user ON user_quiz_bookmarks(user_id);

COMMENT ON TABLE user_quiz_bookmarks IS 'Câu hỏi đã đánh dấu sao của HS';

-- =====================================================
-- TABLE: user_flashcard_notes (Highlight, gạch chân, ghi chú)
-- =====================================================
CREATE TABLE IF NOT EXISTS user_flashcard_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES user_profiles(user_id),
    doc_id TEXT NOT NULL,
    card_hash TEXT NOT NULL,        -- Hash của front+back để tránh duplicate
    front TEXT NOT NULL,            -- Snapshot front
    back TEXT NOT NULL,             -- Snapshot back
    highlighted_keywords TEXT[],    -- Array từ khóa được highlight
    personal_note TEXT,             -- Ghi chú cá nhân
    is_hard BOOLEAN DEFAULT FALSE,  -- Đánh dấu là card khó
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_flashcard_notes_unique ON user_flashcard_notes(user_id, card_hash);
CREATE INDEX IF NOT EXISTS idx_flashcard_notes_user ON user_flashcard_notes(user_id);
CREATE INDEX IF NOT EXISTS idx_flashcard_notes_doc ON user_flashcard_notes(doc_id);

COMMENT ON TABLE user_flashcard_notes IS 'Highlight, ghi chú, đánh dấu card khó của HS';

-- =====================================================
-- UPDATE: quiz_scores - Thêm shared_quiz_id để hỗ trợ quiz công khai
-- =====================================================
-- Check nếu column đã tồn tại thì không thêm
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'quiz_scores' AND column_name = 'shared_quiz_id'
    ) THEN
        ALTER TABLE quiz_scores ADD COLUMN shared_quiz_id UUID REFERENCES shared_quizzes(id);
        COMMENT ON COLUMN quiz_scores.shared_quiz_id IS 'Link đến shared_quiz nếu đây là quiz công khai';
    END IF;
END $$;

-- =====================================================
-- UPDATE: flashcard_progress - Persist SM-2 vào DB
-- =====================================================
-- Check nếu bảng đã tồn tại thì không tạo lại
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'flashcard_progress') THEN
        CREATE TABLE flashcard_progress (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id TEXT NOT NULL REFERENCES user_profiles(user_id),
            doc_id TEXT NOT NULL,
            card_hash TEXT NOT NULL,
            front TEXT NOT NULL,
            back TEXT NOT NULL,
            ease_factor FLOAT DEFAULT 2.5,  -- SM-2 ease factor
            interval INTEGER DEFAULT 0,      -- Khoảng cách lặp (ngày)
            repetitions INTEGER DEFAULT 0,   -- Số lần lặp thành công
            last_reviewed_at TIMESTAMPTZ,
            next_review_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_flashcard_progress_unique ON flashcard_progress(user_id, card_hash);
        CREATE INDEX IF NOT EXISTS idx_flashcard_progress_user ON flashcard_progress(user_id);
        CREATE INDEX IF NOT EXISTS idx_flashcard_progress_next_review ON flashcard_progress(next_review_at);

        COMMENT ON TABLE flashcard_progress IS 'SM-2 spaced repetition progress - PERSIST TO DB';
    END IF;
END $$;

-- =====================================================
-- FUNCTIONS: Helper functions
-- =====================================================

-- Function: Tạo share_code ngắn từ UUID
CREATE OR REPLACE FUNCTION generate_share_code()
RETURNS TEXT AS $$
BEGIN
    RETURN (
        SELECT substring(md5(random()::text || now()::text) from 1 for 8)
    );
END;
$$ LANGUAGE plpgsql;

-- Function: Cập nhật updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attach triggers cho user_profiles
DROP TRIGGER IF EXISTS trigger_update_user_profiles ON user_profiles;
CREATE TRIGGER trigger_update_user_profiles
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Attach triggers cho user_flashcard_notes
DROP TRIGGER IF EXISTS trigger_update_flashcard_notes ON user_flashcard_notes;
CREATE TRIGGER trigger_update_flashcard_notes
    BEFORE UPDATE ON user_flashcard_notes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- SAMPLE DATA: Test shared quiz (optional)
-- =====================================================
-- Uncomment để test nhanh:
-- INSERT INTO shared_quizzes (creator_id, title, subject, chapter, share_code, questions)
-- VALUES (
--     'test_teacher_id',
--     'Sinh học - Chương 5: Tiến hóa',
--     'sinh_hoc',
--     'Chương 5',
--     'sinh5test',
--     '[
--         {
--             "question": "Thuyết tiến hóa trung tính do ai đề xuất?",
--             "options": ["A. Darwin", "B. Kimura", "C. Mendel", "D. Lamarck"],
--             "correct": 1,
--             "explanation": "Kimura đề xuất thuyết tiến hóa trung tính năm 1968",
--             "difficulty": "medium"
--         }
--     ]'::jsonb
-- );