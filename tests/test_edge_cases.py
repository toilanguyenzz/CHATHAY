#!/usr/bin/env python3
"""Edge case tests — malformed inputs, API failures, session cleanup"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.study_engine import QuizSession, FlashcardSession
from services.db_service import (
    clear_study_session, save_study_session, load_study_session,
    _cleanup_expired_doc_texts, _cleanup_expired_study_sessions
)
import time

def test_quiz_empty_questions():
    """Quiz with empty questions list should handle gracefully."""
    try:
        session = QuizSession([], "doc1", "quiz_empty")
        session.start()
        assert session.current_idx == 0
        assert session.score == 0
        print("[PASS] Empty quiz handled")
    except Exception as e:
        print(f"[FAIL] Empty quiz: {e}")
        raise

def test_quiz_malformed_question():
    """Quiz with missing fields should not crash format_question."""
    malformed = [{"question": "Only question", "options": ["A", "B"], "correct": 0}]  # Missing explanation, difficulty
    try:
        session = QuizSession(malformed, "doc1")
        session.start()
        formatted = session.format_question()
        assert "Only question" in formatted
        print("[PASS] Malformed question handled")
    except Exception as e:
        print(f"[FAIL] Malformed question: {e}")
        raise

def test_flashcard_empty():
    """Flashcard with empty list."""
    try:
        session = FlashcardSession([], "doc1")
        summary = session.get_summary()
        assert summary["total_cards"] == 0
        print("[PASS] Empty flashcard handled")
    except Exception as e:
        print(f"[FAIL] Empty flashcard: {e}")
        raise

def test_quiz_serialization_roundtrip():
    """Ensure session survives serialization with all fields."""
    questions = [
        {"question": "Q1?", "options": ["A", "B", "C", "D"], "correct": 2, "explanation": "Because C", "difficulty": "hard"},
        {"question": "Q2?", "options": ["A", "B", "C", "D"], "correct": 1, "explanation": "Because B", "difficulty": "medium"},
    ]
    session = QuizSession(questions, "doc_test", "quiz_roundtrip")
    session.start()
    session.process_answer("C")
    session.process_answer("B")
    data = session.to_dict()
    restored = QuizSession.from_dict(data)
    assert restored.questions == questions
    assert restored.answers[0]["selected"] == "C"
    assert restored.score == 2
    print("[PASS] Quiz serialization roundtrip")

def test_flashcard_serialization_roundtrip():
    cards = [{"front": "F1", "back": "B1"}, {"front": "F2", "back": "B2"}]
    session = FlashcardSession(cards, "doc_test")
    session.current_idx = 1
    session.record_review(True)
    data = session.to_dict()
    restored = FlashcardSession.from_dict(data)
    assert restored.flashcards == cards
    assert restored.current_idx == 1
    assert len(restored.reviews) == 1
    print("[PASS] Flashcard serialization roundtrip")

def test_session_cleanup():
    """Test that clear_study_session removes data."""
    user_id = "test_cleanup_user"
    doc_id = "test_doc_cleanup"
    session_data = {"quiz_id": "test_quiz123", "questions": []}
    save_study_session(user_id, doc_id, "quiz", session_data)
    loaded = load_study_session(user_id)
    assert loaded is not None
    assert loaded["doc_id"] == doc_id
    assert loaded["session_type"] == "quiz"
    assert loaded["data"] == session_data
    clear_study_session(user_id)
    loaded2 = load_study_session(user_id)
    assert loaded2 is None
    print("[PASS] Session cleanup works")

def test_qa_counter_cleanup():
    """Test Q&A counter resets properly."""
    user_id = 888
    doc_id = "test_doc_cleanup"
    from services.db_service import increment_qa_count, get_qa_count, reset_qa_count
    count1 = increment_qa_count(user_id, doc_id)
    assert count1 == 1
    reset_qa_count(user_id, doc_id)
    count2 = get_qa_count(user_id, doc_id)
    assert count2 == 0
    print("[PASS] Q&A counter cleanup works")

def test_expired_doc_text_cleanup():
    """Test that expired doc texts are cleaned up lazily."""
    # Directly manipulate memory to create expired entry
    key = "999:expired_doc"
    from services import db_service as dbs
    dbs._memory_doc_text_temp[key] = {
        "text": "old text",
        "expires_at": time.time() - 3600  # Expired 1h ago
    }
    _cleanup_expired_doc_texts()
    assert key not in dbs._memory_doc_text_temp
    print("[PASS] Expired doc text cleanup works")

def test_expired_session_cleanup():
    """Test old session cleanup (24h TTL)."""
    user_id = "old_session_user"
    doc_id = "old_doc"
    old_data = {"quiz_id": "old_quiz", "questions": []}
    from services import db_service as dbs
    # Create session with old timestamp
    key = f"study:{user_id}"
    dbs._memory_study_sessions[key] = {
        "doc_id": doc_id,
        "session_type": "quiz",
        "data": old_data,
        "created_at": time.time() - (25 * 3600),
        "expires_at": time.time() - (25 * 3600),  # Expired
        "updated_at": time.time() - (25 * 3600),
    }
    _cleanup_expired_study_sessions()
    assert key not in dbs._memory_study_sessions
    print("[PASS] Expired session cleanup works")

def test_quiz_options_no_double_prefix():
    """Regression: options with A. prefix should not become A. A."""
    questions = [
        {"question": "Test?", "options": ["A. Option1", "B. Option2"], "correct": 0, "explanation": "", "difficulty": "easy"}
    ]
    session = QuizSession(questions, "doc1")
    formatted = session.format_question()
    assert "A. A." not in formatted
    assert "A. Option1" in formatted
    print("[PASS] No double prefix")

def test_flashcard_sm2_progression():
    """SM-2 intervals: 1, 3, 7, 14, 30 days."""
    cards = [{"front": "Q", "back": "A"}]
    session = FlashcardSession(cards, "doc1")
    session.current_idx = 0
    intervals = []
    for _ in range(5):
        review = session.record_review(True)
        intervals.append(review["next_review_in_days"])
    expected = [1, 3, 7, 14, 30]
    assert intervals == expected, f"Expected {expected}, got {intervals}"
    print("[PASS] SM-2 progression correct")

def test_session_persistence_with_doc_id():
    """Test save/load preserves doc_id correctly."""
    user_id = "persist_test_user"
    doc_id = "persist_doc_123"
    session_data = {"quiz_id": "quiz456", "questions": [{"question": "Test?"}]}
    save_study_session(user_id, doc_id, "quiz", session_data)
    loaded = load_study_session(user_id)
    assert loaded is not None
    assert loaded["doc_id"] == doc_id
    assert loaded["session_type"] == "quiz"
    assert loaded["data"] == session_data
    clear_study_session(user_id)
    assert load_study_session(user_id) is None
    print("[PASS] Session persistence with doc_id")

if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')

    tests = [
        test_quiz_empty_questions,
        test_quiz_malformed_question,
        test_flashcard_empty,
        test_quiz_serialization_roundtrip,
        test_flashcard_serialization_roundtrip,
        test_session_cleanup,
        test_qa_counter_cleanup,
        test_expired_doc_text_cleanup,
        test_expired_session_cleanup,
        test_quiz_options_no_double_prefix,
        test_flashcard_sm2_progression,
        test_session_persistence_with_doc_id,
    ]

    passed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{passed}/{len(tests)} edge case tests passed")
    sys.exit(0 if passed == len(tests) else 1)
