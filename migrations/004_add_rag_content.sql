-- Migration 004: Add RAG content (chunks + embeddings) to documents
-- Created: 2025-05-04
-- Purpose: Store document chunks and embeddings for RAG Q&A

-- =====================================================
-- ALTER documents table: Add JSONB column for RAG content
-- =====================================================

-- Add content column for storing chunks and embeddings
ALTER TABLE documents ADD COLUMN IF NOT EXISTS content JSONB DEFAULT '{}';

-- Comment
COMMENT ON COLUMN documents.content IS 'RAG content: chunks array and embeddings array for question answering';

-- Index for fast access (optional, JSONB GIN index)
-- CREATE INDEX IF NOT EXISTS idx_documents_content ON documents USING GIN (content);
