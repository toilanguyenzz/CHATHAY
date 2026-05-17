-- Migration 007: Add student_name and student_phone to quiz_attempts
-- Purpose: Support no-login quiz for students (Supabase/PostgreSQL)

-- Add columns if not exist
DO $$
BEGIN
    -- Add student_name column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'quiz_attempts' AND column_name = 'student_name'
    ) THEN
        ALTER TABLE quiz_attempts ADD COLUMN student_name TEXT;
        COMMENT ON COLUMN quiz_attempts.student_name IS 'Tên học sinh (không cần login)';
    END IF;

    -- Add student_phone column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'quiz_attempts' AND column_name = 'student_phone'
    ) THEN
        ALTER TABLE quiz_attempts ADD COLUMN student_phone TEXT;
        COMMENT ON COLUMN quiz_attempts.student_phone IS 'Số điện thoại học sinh (dùng để identify)';
    END IF;
END $$;

-- Create index for phone lookup (PostgreSQL syntax)
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_phone ON quiz_attempts(student_phone);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_student_name ON quiz_attempts(student_name);