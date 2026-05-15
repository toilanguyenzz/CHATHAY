-- Migration 005: Add Solved Problems storage
-- Created: 2025-05-07
-- Purpose: Store AI-generated step-by-step solutions for student problems

-- =====================================================
-- TABLE: solved_problems
-- Store history of problems solved by AI
-- =====================================================
CREATE TABLE IF NOT EXISTS solved_problems (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    question TEXT NOT NULL,
    steps JSONB NOT NULL, -- array of step strings
    answer TEXT NOT NULL,
    subject TEXT, -- e.g., 'toan', 'ly', 'hoa', 'anh', 'van'
    difficulty TEXT, -- 'easy', 'medium', 'hard'
    image_url TEXT, -- optional: URL of uploaded image
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_solved_problems_user_id ON solved_problems(user_id);
CREATE INDEX IF NOT EXISTS idx_solved_problems_created_at ON solved_problems(created_at DESC);

-- Comments
COMMENT ON TABLE solved_problems IS 'History of AI-generated step-by-step problem solutions';
COMMENT ON COLUMN solved_problems.question IS 'Original problem question (OCR extracted)';
COMMENT ON COLUMN solved_problems.steps IS 'Array of solution steps (each step is a string)';
COMMENT ON COLUMN solved_problems.answer IS 'Final answer';
COMMENT ON COLUMN solved_problems.subject IS 'Detected subject (toan/ly/hoa/...)';
COMMENT ON COLUMN solved_problems.difficulty IS 'Problem difficulty level';
COMMENT ON COLUMN solved_problems.image_url IS 'Optional: S3 URL of original problem image';
