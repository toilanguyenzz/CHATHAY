-- Migration 003: Add Flashcards & Quiz storage + Coin System
-- Created: 2025-05-03
-- Purpose: Store generated flashcards/quiz AND coin balance/transactions

-- =====================================================
-- ALTER documents table: Add JSONB columns for cached AI content
-- =====================================================

-- Add flashcards column (stores array of flashcard objects)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS flashcards JSONB DEFAULT '[]';

-- Add quiz_questions column (stores array of quiz question objects)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS quiz_questions JSONB DEFAULT '[]';

-- Index for quick access (optional, JSONB GIN index for containment queries)
-- CREATE INDEX IF NOT EXISTS idx_documents_flashcards ON documents USING GIN (flashcards);
-- CREATE INDEX IF NOT EXISTS idx_documents_quiz ON documents USING GIN (quiz_questions);

-- Comments
COMMENT ON COLUMN documents.flashcards IS 'Cached flashcards generated from this document (JSON array)';
COMMENT ON COLUMN documents.quiz_questions IS 'Cached quiz questions generated from this document (JSON array)';


-- =====================================================
-- TABLE: user_coin_balance
-- Track user's current coin balance (separate from daily usage)
-- =====================================================
CREATE TABLE IF NOT EXISTS user_coin_balance (
    user_id TEXT PRIMARY KEY,
    balance INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index
CREATE INDEX IF NOT EXISTS idx_user_coin_balance_user ON user_coin_balance(user_id);

-- Comment
COMMENT ON TABLE user_coin_balance IS 'Current coin balance for each user';
COMMENT ON COLUMN user_coin_balance.balance IS 'Current coin balance (>= 0)';

-- Trigger to update updated_at
CREATE TRIGGER update_user_coin_balance_updated_at
    BEFORE UPDATE ON user_coin_balance
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- =====================================================
-- TABLE: coin_transactions
-- Audit log for all coin credits/debits
-- =====================================================
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_coin_transactions_user ON coin_transactions(user_id, created_at DESC);

-- Comment
COMMENT ON TABLE coin_transactions IS 'Audit log for all coin transactions';
COMMENT ON COLUMN coin_transactions.metadata IS 'Additional context (e.g., doc_id, quiz_score)';


-- =====================================================
-- FUNCTIONS: Get/Update coin balance with transaction logging
-- =====================================================

CREATE OR REPLACE FUNCTION get_or_create_coin_balance(p_user_id TEXT)
RETURNS INTEGER AS $$
DECLARE
    v_balance INTEGER;
BEGIN
    SELECT balance INTO v_balance
    FROM user_coin_balance
    WHERE user_id = p_user_id;

    IF v_balance IS NULL THEN
        INSERT INTO user_coin_balance (user_id, balance) VALUES (p_user_id, 0);
        v_balance := 0;
    END IF;

    RETURN v_balance;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_or_create_coin_balance IS 'Get coin balance, creating record if not exists';

CREATE OR REPLACE FUNCTION add_coins_transaction(
    p_user_id TEXT,
    p_amount INTEGER,
    p_reason TEXT,
    p_metadata JSONB DEFAULT '{}'
) RETURNS INTEGER AS $$
DECLARE
    v_new_balance INTEGER;
BEGIN
    -- Get or create balance
    v_new_balance := get_or_create_coin_balance(p_user_id);

    -- Add coins
    v_new_balance := v_new_balance + p_amount;

    UPDATE user_coin_balance
    SET balance = v_new_balance
    WHERE user_id = p_user_id;

    -- Log transaction
    INSERT INTO coin_transactions (user_id, amount, type, reason, balance_after, metadata)
    VALUES (p_user_id, p_amount, 'credit', p_reason, v_new_balance, p_metadata);

    RETURN v_new_balance;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION add_coins_transaction IS 'Add coins to user and log transaction';

CREATE OR REPLACE FUNCTION spend_coins_transaction(
    p_user_id TEXT,
    p_amount INTEGER,
    p_reason TEXT,
    p_metadata JSONB DEFAULT '{}'
) RETURNS BOOLEAN AS $$
DECLARE
    v_balance INTEGER;
BEGIN
    -- Get balance
    v_balance := get_or_create_coin_balance(p_user_id);

    -- Check sufficient funds
    IF v_balance < p_amount THEN
        RETURN FALSE;
    END IF;

    -- Deduct coins
    v_balance := v_balance - p_amount;

    UPDATE user_coin_balance
    SET balance = v_balance
    WHERE user_id = p_user_id;

    -- Log transaction
    INSERT INTO coin_transactions (user_id, amount, type, reason, balance_after, metadata)
    VALUES (p_user_id, -p_amount, 'debit', p_reason, v_balance, p_metadata);

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION spend_coins_transaction IS 'Spend coins and log transaction (returns FALSE if insufficient)';


-- =====================================================
-- Functions: Get flashcards and quiz for a document
-- =====================================================

CREATE OR REPLACE FUNCTION get_document_flashcards(doc_id_param TEXT)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT flashcards INTO result
    FROM documents
    WHERE id = doc_id_param
    AND flashcards IS NOT NULL
    AND jsonb_array_length(flashcards) > 0;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_document_quiz(doc_id_param TEXT)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT quiz_questions INTO result
    FROM documents
    WHERE id = doc_id_param
    AND quiz_questions IS NOT NULL
    AND jsonb_array_length(quiz_questions) > 0;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_document_flashcards IS 'Get cached flashcards for a document';
COMMENT ON FUNCTION get_document_quiz IS 'Get cached quiz questions for a document';

