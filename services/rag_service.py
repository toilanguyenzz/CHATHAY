"""RAG Service — Retrieval Augmented Generation cho Q&A tài liệu.

Logic:
1. Chunk document text (512-1000 chars, theo sentence boundaries)
2. Tạo embeddings cho từng chunk (Gemini Embedding API — FREE, không tốn RAM)
3. Tính embedding cho question
4. Tìm top-K chunks có cosine similarity cao
5. Gọi LLM (DeepSeek) để trả lời dựa trên context
"""

import logging
import math
import re
import time
from typing import Any

import httpx
import numpy as np

from config import config
from services.db_service import get_supabase_client, get_document_text_temp

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# MEMORY CACHE FOR EMBEDDINGS (tránh recompute)
# ═══════════════════════════════════════════════════════════════
_embedding_cache: dict[str, list[float]] = {}
_embedding_cache_ttl: dict[str, float] = {}
EMBEDDING_CACHE_TTL = 3600  # 1 hour

# ═══════════════════════════════════════════════════════════════
# IN-MEMORY FALLBACK FOR RAG CONTENT
# ═══════════════════════════════════════════════════════════════
# Khi Supabase không khả dụng, lưu RAG content vào memory
# Key: "user_id:doc_id" -> {"chunks": [...], "embeddings": [...], "expires_at": float}
_memory_rag_content: dict[str, dict] = {}
RAG_CONTENT_TTL = 24 * 3600  # 24h (match với Q&A TTL)

# ═══════════════════════════════════════════════════════════════
# GEMINI EMBEDDING API (FREE tier — 0 RAM, 768 dimensions)
# Thay thế sentence-transformers để tiết kiệm ~400MB RAM
# Free tier: 1500 RPM — thừa sức cho startup giai đoạn đầu
# ═══════════════════════════════════════════════════════════════

# Gemini API key rotation (dùng chung pool keys với AI summarizer)
_gemini_key_index = 0

def _get_gemini_api_key() -> str:
    """Lấy Gemini API key với rotation để tránh rate limit."""
    global _gemini_key_index
    keys = [k for k in [config.GEMINI_API_KEY, config.GEMINI_API_KEY_2, config.GEMINI_API_KEY_3] if k]
    if not keys:
        raise ValueError("No GEMINI_API_KEY configured")
    key = keys[_gemini_key_index % len(keys)]
    _gemini_key_index += 1
    return key


def compute_embedding(text: str, use_cache: bool = True) -> list[float]:
    """
    Tính embedding vector cho text bằng Gemini Embedding API (miễn phí).

    Args:
        text: Input text
        use_cache: Có dùng cache không

    Returns:
        Embedding vector as list (768 dimensions)
    """
    # Normalize text for cache key
    text_norm = re.sub(r'\s+', ' ', text.strip())[:500]  # First 500 chars for cache key

    if use_cache:
        cache_key = str(hash(text_norm))
        now = time.time()
        if cache_key in _embedding_cache:
            # Check TTL
            if _embedding_cache_ttl.get(cache_key, 0) > now:
                logger.debug("Embedding cache hit for text len=%s", len(text))
                return _embedding_cache[cache_key]
            else:
                # Expired, remove
                _embedding_cache.pop(cache_key, None)
                _embedding_cache_ttl.pop(cache_key, None)

    # Gọi Gemini Embedding API (đồng bộ, dùng httpx)
    api_key = _get_gemini_api_key()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={api_key}"

    # Truncate text nếu quá dài (Gemini embedding giới hạn ~2048 tokens)
    text_for_embed = text.strip()[:8000]

    payload = {
        "model": "models/text-embedding-004",
        "content": {
            "parts": [{"text": text_for_embed}]
        }
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        result = data["embedding"]["values"]
        logger.debug("Gemini embedding computed: %s dims for text len=%s", len(result), len(text))

    except Exception as e:
        logger.error("Gemini Embedding API error: %s", e)
        raise

    # Save to cache
    if use_cache:
        cache_key = str(hash(text_norm))
        _embedding_cache[cache_key] = result
        _embedding_cache_ttl[cache_key] = time.time() + EMBEDDING_CACHE_TTL

    return result


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Tính cosine similarity giữa 2 vectors."""
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ═══════════════════════════════════════════════════════════════
# CHUNKING
# ═══════════════════════════════════════════════════════════════

def split_into_chunks(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """
    Split text thành chunks theo sentence boundaries.

    Args:
        text: Nội dung document
        chunk_size: Target chars mỗi chunk (512-1000)
        overlap: Số chars overlap giữa các chunks

    Returns:
        List của text chunks
    """
    if not text or not text.strip():
        return []

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text.strip())

    # Split by sentences (., !, ?, newline)
    # Regex: sentence endings followed by space or end
    sentences = re.split(r'(?<=[.!?])\s+|\n+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return []

    chunks = []
    current_chunk = []
    current_len = 0

    for sentence in sentences:
        sentence_len = len(sentence)

        # Nếu sentence đơn lẻ lớn hơn chunk_size, split nó
        if sentence_len > chunk_size:
            # Flush current chunk first
            if current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_len = 0

            # Split long sentence
            words = sentence.split()
            temp_chunk = []
            temp_len = 0
            for word in words:
                word_len = len(word) + 1  # +1 for space
                if temp_len + word_len > chunk_size and temp_chunk:
                    chunks.append(' '.join(temp_chunk))
                    temp_chunk = [word]
                    temp_len = word_len
                else:
                    temp_chunk.append(word)
                    temp_len += word_len
            if temp_chunk:
                current_chunk = temp_chunk
                current_len = temp_len
            continue

        # Check if adding this sentence exceeds chunk_size
        if current_len + sentence_len > chunk_size and current_chunk:
            # Save current chunk
            chunks.append(' '.join(current_chunk))
            # Start new chunk with overlap from previous
            if overlap > 0 and current_chunk:
                # Keep last few sentences for overlap
                overlap_text = []
                overlap_len = 0
                for s in reversed(current_chunk):
                    if overlap_len + len(s) <= overlap:
                        overlap_text.insert(0, s)
                        overlap_len += len(s)
                    else:
                        break
                current_chunk = overlap_text + [sentence]
                current_len = sum(len(s) for s in current_chunk) + len(current_chunk) - 1
            else:
                current_chunk = [sentence]
                current_len = sentence_len
        else:
            current_chunk.append(sentence)
            current_len += sentence_len + (1 if current_chunk else 0)

    # Flush last chunk
    if current_chunk:
        chunks.append(' '.join(current_chunk))

    logger.info("Split %s chars into %s chunks (target ~%s chars)", len(text), len(chunks), chunk_size)
    return chunks


# ═══════════════════════════════════════════════════════════════
# IN-MEMORY FALLBACK HELPERS
# ═══════════════════════════════════════════════════════════════

def _get_memory_rag_content(user_id: str, doc_id: str) -> dict[str, Any] | None:
    """Lấy RAG content từ memory (nếu còn TTL)."""
    key = f"{user_id}:{doc_id}"
    entry = _memory_rag_content.get(key)
    if not entry:
        return None
    if time.time() > entry.get("expires_at", 0):
        _memory_rag_content.pop(key, None)
        logger.info("RAG content expired for user=%s, doc=%s", user_id, doc_id)
        return None
    return entry


def _save_memory_rag_content(user_id: str, doc_id: str, chunks: list[str], embeddings: list[list[float]]) -> None:
    """Lưu RAG content vào memory với TTL 24h."""
    key = f"{user_id}:{doc_id}"
    _memory_rag_content[key] = {
        "chunks": chunks,
        "embeddings": embeddings,
        "expires_at": time.time() + RAG_CONTENT_TTL,
    }
    logger.info("Saved RAG content to memory: user=%s, doc=%s, chunks=%s", user_id[:8], doc_id[:8], len(chunks))
    # Lazy cleanup
    _cleanup_expired_memory_rag()


def _cleanup_expired_memory_rag():
    """Dọn RAG content hết hạn khỏi memory."""
    now = time.time()
    expired_keys = [k for k, v in _memory_rag_content.items() if now > v.get("expires_at", 0)]
    for k in expired_keys:
        del _memory_rag_content[k]
    if expired_keys:
        logger.info("Cleaned up %s expired RAG content entries", len(expired_keys))


# ═══════════════════════════════════════════════════════════════
# DOCUMENT PROCESSING
# ═══════════════════════════════════════════════════════════════

def get_document_content(user_id: str, doc_id: str) -> dict[str, Any] | None:
    """
    Lấy document content từ DB (text tạm hoặc từ documents table).

    Returns:
        Dict với keys: text, chunks, embeddings (optional)
    """
    # First try to get raw text from temp storage
    raw_text = get_document_text_temp(user_id, doc_id)
    if not raw_text:
        logger.warning("No temp text found for user=%s, doc=%s", user_id, doc_id)
        return None

    supabase = get_supabase_client()

    # Lấy document từ DB để có cached chunks/embeddings
    if supabase:
        try:
            result = supabase.table("documents").select("content").eq("id", doc_id).eq("user_id", user_id).execute()
            if result.data:
                db_content = result.data[0].get("content", {})
                # Nếu DB đã có chunks và embeddings, dùng luôn
                if db_content.get("chunks") and db_content.get("embeddings"):
                    return {
                        "text": raw_text,
                        "chunks": db_content["chunks"],
                        "embeddings": db_content["embeddings"],
                    }
        except Exception as e:
            logger.error(f"Error fetching document content from DB: {e}")

    # Check memory fallback
    mem_content = _get_memory_rag_content(user_id, doc_id)
    if mem_content:
        logger.info("Using memory fallback RAG content for user=%s, doc=%s", user_id[:8], doc_id[:8])
        return {
            "text": raw_text,
            "chunks": mem_content["chunks"],
            "embeddings": mem_content["embeddings"],
        }

    # Return raw text only (chunks will be generated on-the-fly)
    return {"text": raw_text, "chunks": None, "embeddings": None}


def save_document_rag_content(user_id: str, doc_id: str, chunks: list[str], embeddings: list[list[float]]) -> bool:
    """Lưu chunks và embeddings vào document.content trong DB (và memory fallback)."""
    supabase = get_supabase_client()

    # Always save to memory fallback
    _save_memory_rag_content(user_id, doc_id, chunks, embeddings)

    if not supabase:
        logger.warning("Supabase not available, using memory-only RAG storage")
        return True

    try:
        content = {
            "chunks": chunks,
            "embeddings": embeddings,
            "updated_at": __import__('time').time(),
        }
        supabase.table("documents").update({"content": content}).eq("id", doc_id).eq("user_id", user_id).execute()
        logger.info("Saved RAG content to DB: %s chunks, %s embeddings", len(chunks), len(embeddings))
        return True
    except Exception as e:
        logger.error(f"Error saving RAG content to DB: {e}")
        return False


def ensure_document_embeddings(user_id: str, doc_id: str, text: str) -> tuple[list[str], list[list[float]]] | None:
    """
    Đảm bảo document có chunks và embeddings.
    Nếu chưa có trong DB thì tạo ngay và lưu.

    Returns:
        (chunks, embeddings) hoặc None nếu lỗi
    """
    # Check memory fallback first (faster)
    mem_content = _get_memory_rag_content(user_id, doc_id)
    if mem_content:
        logger.info("Using memory cached RAG content for doc %s", doc_id[:8])
        return mem_content["chunks"], mem_content["embeddings"]

    # Check if already exists in DB
    supabase = get_supabase_client()
    if supabase:
        try:
            result = supabase.table("documents").select("content").eq("id", doc_id).eq("user_id", user_id).execute()
            if result.data:
                db_content = result.data[0].get("content", {})
                if db_content.get("chunks") and db_content.get("embeddings"):
                    logger.info("Using DB cached RAG content for doc %s", doc_id[:8])
                    # Also save to memory for faster next access
                    _save_memory_rag_content(user_id, doc_id, db_content["chunks"], db_content["embeddings"])
                    return db_content["chunks"], db_content["embeddings"]
        except Exception as e:
            logger.error(f"Error checking document content: {e}")

    # Need to generate embeddings
    logger.info("Generating RAG content for doc %s", doc_id[:8])

    # Chunk the text
    chunks = split_into_chunks(text, chunk_size=512, overlap=50)
    if not chunks:
        logger.error("No chunks generated from text")
        return None

    # Compute embeddings for all chunks (with individual caching)
    try:
        embeddings = []
        for chunk in chunks:
            emb = compute_embedding(chunk, use_cache=True)
            embeddings.append(emb)
    except Exception as e:
        logger.error(f"Error computing embeddings: {e}")
        return None

    # Save to DB and memory
    save_document_rag_content(user_id, doc_id, chunks, embeddings)

    return chunks, embeddings


def find_top_chunks(
    question_embedding: list[float],
    chunk_embeddings: list[list[float]],
    chunks: list[str],
    top_k: int = 5
) -> list[dict[str, Any]]:
    """
    Tìm top-K chunks có cosine similarity cao nhất.

    Returns:
        List của {chunk_index, text, score}
    """
    if not chunk_embeddings or not chunks:
        return []

    similarities = []
    for i, emb in enumerate(chunk_embeddings):
        score = cosine_similarity(question_embedding, emb)
        similarities.append((i, score))

    # Sort by score descending
    similarities.sort(key=lambda x: x[1], reverse=True)

    top_results = []
    for i in range(min(top_k, len(similarities))):
        idx, score = similarities[i]
        top_results.append({
            "chunk_index": idx,
            "text": chunks[idx],
            "score": round(score, 4),
        })

    return top_results


# ═══════════════════════════════════════════════════════════════
# LLM ANSWER GENERATION
# ═══════════════════════════════════════════════════════════════

async def generate_answer_with_rag(
    question: str,
    top_chunks: list[dict[str, Any]],
    user_id: str | None = None
) -> str:
    """
    Gọi LLM (DeepSeek) để trả lời câu hỏi dựa trên context.

    Args:
        question: Câu hỏi của user
        top_chunks: List của top chunks từ find_top_chunks
        user_id: Optional user ID cho logging

    Returns:
        Answer string
    """
    if not top_chunks:
        return "Tôi không tìm thấy thông tin trong tài liệu."

    # Build context
    context_parts = []
    for i, chunk in enumerate(top_chunks, 1):
        context_parts.append(f"[Đoạn {i}]\n{chunk['text']}")
    context = "\n\n".join(context_parts)

    # Build prompt
    prompt = f"""Bạn là trợ lý AI giúp trả lời câu hỏi dựa trên context từ tài liệu.

Context từ tài liệu:
{context}

Câu hỏi: {question}

Yêu cầu:
- Trả lời ngắn gọn, rõ ràng
- Chỉ dựa vào context được cung cấp
- Nếu context không chứa thông tin để trả lời, hãy nói "Tôi không tìm thấy thông tin trong tài liệu"
- Không thêm thông tin bên ngoài
- Trả lời bằng tiếng Việt

Trả lời:"""

    logger.info("Calling DeepSeek for RAG answer, user=%s, context_chunks=%s", user_id, len(top_chunks))

    try:
        import openai
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
        )

        response = await client.chat.completions.create(
            model=config.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "Bạn là trợ lý học tập thông minh."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            temperature=0.3,
        )

        answer = response.choices[0].message.content.strip()
        logger.info("DeepSeek answer generated: %s chars", len(answer))
        return answer

    except Exception as e:
        logger.error(f"Error calling DeepSeek: {e}")
        return "Xin lỗi, đã có lỗi khi tạo câu trả lời. Vui lòng thử lại sau."


# ═══════════════════════════════════════════════════════════════
# MAIN RAG PIPELINE
# ═══════════════════════════════════════════════════════════════

async def rag_qa_pipeline(
    user_id: str,
    doc_id: str,
    question: str,
    top_k: int = 5
) -> dict[str, Any]:
    """
    Full RAG pipeline: get doc → ensure embeddings → search → generate answer.

    Args:
        user_id: User ID
        doc_id: Document ID
        question: Question string
        top_k: Number of top chunks to retrieve

    Returns:
        Dict với keys: answer, sources, error (optional)
    """
    try:
        # 1. Get document text
        doc_data = get_document_content(user_id, doc_id)
        if not doc_data:
            return {"error": "Document not found or expired"}

        text = doc_data["text"]
        chunks = doc_data.get("chunks")
        embeddings = doc_data.get("embeddings")

        # 2. Ensure embeddings exist
        if not chunks or not embeddings:
            result = ensure_document_embeddings(user_id, doc_id, text)
            if not result:
                return {"error": "Failed to generate embeddings"}
            chunks, embeddings = result

        # 3. Compute question embedding
        question_embedding = compute_embedding(question)

        # 4. Find top chunks
        top_chunks = find_top_chunks(question_embedding, embeddings, chunks, top_k=top_k)

        if not top_chunks:
            return {
                "answer": "Tôi không tìm thấy thông tin liên quan trong tài liệu.",
                "sources": []
            }

        # 5. Generate answer
        answer = await generate_answer_with_rag(question, top_chunks, user_id)

        # 6. Format sources
        sources = [
            {
                "chunk_index": c["chunk_index"],
                "text": c["text"][:200] + "..." if len(c["text"]) > 200 else c["text"],
                "score": c["score"]
            }
            for c in top_chunks
        ]

        return {
            "answer": answer,
            "sources": sources
        }

    except Exception as e:
        logger.error(f"RAG pipeline error: {e}", exc_info=True)
        return {"error": "Internal server error"}
