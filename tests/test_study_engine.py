#!/usr/bin/env python3
"""Unit tests for study_engine — QuizSession & FlashcardSession"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.study_engine import QuizSession, FlashcardSession


# =====================================================
# QUIZ SESSION TESTS
# =====================================================

def test_quiz_session_initialization():
    questions = [
        {
            "question": "1+1=?",
            "options": ["A. 1", "B. 2", "C. 3", "D. 4"],
            "correct": 1,
            "explanation": "Basic math",
            "difficulty": "easy"
        }
    ]
    session = QuizSession(questions, "doc123", "quiz001")
    assert session.quiz_id == "quiz001"
    assert session.doc_id == "doc123"
    assert session.current_idx == 0
    assert session.score == 0
    assert session.streak == 0
    assert len(session.answers) == 0


def test_quiz_session_start():
    questions = [{"question": "Test?", "options": ["A", "B", "C", "D"], "correct": 0, "explanation": "", "difficulty": "easy"}]
    session = QuizSession(questions, "doc1")
    session.start()
    assert session.start_time is not None


def test_quiz_format_question_no_prefix():
    """Test formatting when options have NO letter prefixes"""
    questions = [
        {
            "question": "What is 2+2?",
            "options": ["3", "4", "5", "6"],
            "correct": 1,
            "explanation": "Math",
            "difficulty": "easy"
        }
    ]
    session = QuizSession(questions, "doc1")
    formatted = session.format_question()
    assert "A. 3" in formatted
    assert "B. 4" in formatted
    assert "C. 5" in formatted
    assert "D. 6" in formatted


def test_quiz_format_question_with_prefix():
    """Test formatting when options already have letter prefixes (from Gemini)"""
    questions = [
        {
            "question": "√4 = ?",
            "options": ["A. 2", "B. -2", "C. ±2", "D. 0"],
            "correct": 0,
            "explanation": "√4 = 2",
            "difficulty": "easy"
        }
    ]
    session = QuizSession(questions, "doc1")
    formatted = session.format_question()
    # Should NOT double the prefix
    assert "A. 2" in formatted
    assert "A. A. 2" not in formatted


def test_quiz_process_correct_answer():
    questions = [
        {
            "question": "Q1?",
            "options": ["A", "B", "C", "D"],
            "correct": 0,
            "explanation": "",
            "difficulty": "easy"
        },
        {
            "question": "Q2?",
            "options": ["A", "B", "C", "D"],
            "correct": 1,
            "explanation": "",
            "difficulty": "easy"
        }
    ]
    session = QuizSession(questions, "doc1")
    session.start()

    result = session.process_answer("A")
    assert result["is_correct"] is True
    assert result["correct_answer"] == "A"
    assert session.score == 1
    assert session.streak == 1
    assert result["is_last"] is False
    assert session.current_idx == 1

    # Second answer wrong
    result2 = session.process_answer("C")
    assert result2["is_correct"] is False
    assert result2["correct_answer"] == "B"
    assert session.score == 1  # No change
    assert session.streak == 0  # Reset


def test_quiz_process_invalid_answer():
    questions = [{"question": "Q?", "options": ["A", "B", "C", "D"], "correct": 0, "explanation": "", "difficulty": "easy"}]
    session = QuizSession(questions, "doc1")
    session.start()
    try:
        session.process_answer("E")  # Invalid
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        pass  # Expected


def test_quiz_final_score():
    questions = [
        {"question": "Q1", "options": ["A", "B", "C", "D"], "correct": 0, "explanation": "", "difficulty": "easy"},
        {"question": "Q2", "options": ["A", "B", "C", "D"], "correct": 1, "explanation": "", "difficulty": "easy"},
        {"question": "Q3", "options": ["A", "B", "C", "D"], "correct": 0, "explanation": "", "difficulty": "easy"},
    ]
    session = QuizSession(questions, "doc1")
    session.start()

    session.process_answer("A")  # correct
    session.process_answer("B")  # correct
    session.process_answer("A")  # correct

    final = session.get_final_score()
    assert final["correct"] == 3
    assert final["total"] == 3
    assert final["percentage"] == 100.0
    assert "Xuất sắc" in final["grade"]
    assert final["streak"] == 3
    assert "time_seconds" in final


def test_quiz_serialization():
    questions = [
        {
            "question": "Q?",
            "options": ["A", "B", "C", "D"],
            "correct": 2,
            "explanation": "Because C",
            "difficulty": "medium"
        }
    ]
    session = QuizSession(questions, "doc1", "quiz123")
    session.start()
    session.process_answer("C")

    data = session.to_dict()
    restored = QuizSession.from_dict(data)

    assert restored.quiz_id == "quiz123"
    assert restored.doc_id == "doc1"
    assert restored.current_idx == 1
    assert restored.score == 1
    assert len(restored.answers) == 1
    assert restored.answers[0]["selected"] == "C"


def test_quiz_buttons():
    questions = [{"question": "Q?", "options": ["A", "B", "C", "D"], "correct": 0, "explanation": "", "difficulty": "easy"}]
    session = QuizSession(questions, "doc1")
    buttons = session.get_buttons()
    assert len(buttons) == 4
    assert buttons[0]["title"] == "A"
    assert buttons[0]["payload"] == "QUIZ_ANSWER_A"
    assert all(b["type"] == "oa.query.show" for b in buttons)


def test_quiz_abort_buttons():
    questions = [{"question": "Q?", "options": ["A", "B", "C", "D"], "correct": 0, "explanation": "", "difficulty": "easy"}]
    session = QuizSession(questions, "doc1")
    buttons = session.get_abort_buttons()
    assert len(buttons) == 2
    payloads = [b["payload"] for b in buttons]
    assert "QUIZ_EXIT" in payloads
    assert "QUIZ_SCORE" in payloads


# =====================================================
# FLASHCARD SESSION TESTS
# =====================================================

def test_flashcard_session_initialization():
    cards = [{"front": "Q", "back": "A"}]
    session = FlashcardSession(cards, "doc1", "fc001")
    assert session.session_id == "fc001"
    assert session.doc_id == "doc1"
    assert session.current_idx == 0
    assert len(session.reviews) == 0


def test_flashcard_current_card():
    cards = [
        {"front": "Front 1", "back": "Back 1"},
        {"front": "Front 2", "back": "Back 2"}
    ]
    session = FlashcardSession(cards, "doc1")
    card = session.current_card()
    assert card["front"] == "Front 1"
    assert session.current_idx == 0


def test_flashcard_format_front():
    cards = [{"front": "Khái niệm", "back": "Giải thích"}]
    session = FlashcardSession(cards, "doc1")
    formatted = session.format_card_front()
    assert "Khái niệm" in formatted
    assert "Lật" in formatted or "lật" in formatted.lower()


def test_flashcard_format_back():
    cards = [{"front": "Q", "back": "A"}]
    session = FlashcardSession(cards, "doc1")
    formatted = session.format_card_back()
    assert "A" in formatted
    assert "nhớ" in formatted.lower() or "chưa nhớ" in formatted.lower()


def test_flashcard_get_front_buttons():
    cards = [{"front": "Q", "back": "A"}]
    session = FlashcardSession(cards, "doc1")
    buttons = session.get_front_buttons()
    assert len(buttons) == 3
    payloads = [b["payload"] for b in buttons]
    assert "FC_FLIP" in payloads
    assert "FC_SKIP" in payloads
    assert "FC_EXIT" in payloads


def test_flashcard_get_back_buttons():
    cards = [{"front": "Q", "back": "A"}]
    session = FlashcardSession(cards, "doc1")
    buttons = session.get_back_buttons()
    assert len(buttons) == 3
    payloads = [b["payload"] for b in buttons]
    assert "FC_REMEMBER" in payloads
    assert "FC_FORGOT" in payloads
    assert "FC_NEXT" in payloads


def test_flashcard_record_review_remembered():
    cards = [{"front": "Q1", "back": "A1"}, {"front": "Q2", "back": "A2"}]
    session = FlashcardSession(cards, "doc1")
    session.current_idx = 0

    review = session.record_review(remembered=True)
    assert review["remembered"] is True
    assert review["card_hash"] is not None
    assert review["next_review_in_days"] >= 1
    assert len(session.reviews) == 1

    # Streak: first review → interval 1 day
    assert review["next_review_in_days"] == 1


def test_flashcard_record_review_forgotten():
    cards = [{"front": "Q", "back": "A"}]
    session = FlashcardSession(cards, "doc1")
    session.current_idx = 0

    review = session.record_review(remembered=False)
    assert review["remembered"] is False
    assert review["next_review_in_days"] == 1  # Reset to 1 day
    assert review["ease_factor"] < 2.5  # Decreased


def test_flashcard_sm2_intervals():
    """Test SM-2 interval progression"""
    cards = [{"front": "Q", "back": "A"}]
    session = FlashcardSession(cards, "doc1")
    session.current_idx = 0

    # Review 1: remembered → 1 day
    r1 = session.record_review(True)
    assert r1["next_review_in_days"] == 1

    # Review 2: same card, remembered → 3 days
    r2 = session.record_review(True)
    assert r2["next_review_in_days"] == 3

    # Review 3: remembered → 7 days
    r3 = session.record_review(True)
    assert r3["next_review_in_days"] == 7

    # Review 4: remembered → 14 days
    r4 = session.record_review(True)
    assert r4["next_review_in_days"] == 14

    # Review 5: remembered → 30 days
    r5 = session.record_review(True)
    assert r5["next_review_in_days"] == 30


def test_flashcard_next_card():
    cards = [
        {"front": "Q1", "back": "A1"},
        {"front": "Q2", "back": "A2"},
        {"front": "Q3", "back": "A3"}
    ]
    session = FlashcardSession(cards, "doc1")

    assert session.next_card() is True  # More cards
    assert session.current_idx == 1
    assert session.next_card() is True
    assert session.current_idx == 2
    assert session.next_card() is False  # End
    assert session.current_idx == 3


def test_flashcard_summary():
    cards = [
        {"front": "Q1", "back": "A1"},
        {"front": "Q2", "back": "A2"},
        {"front": "Q3", "back": "A3"}
    ]
    session = FlashcardSession(cards, "doc1")
    session.current_idx = 0

    session.record_review(True)
    session.record_review(False)
    session.record_review(True)

    summary = session.get_summary()
    assert summary["total_cards"] == 3
    assert summary["reviewed"] == 3
    assert summary["remembered"] == 2
    assert summary["forgotten"] == 1
    assert summary["completion_rate"] == 100.0


def test_flashcard_serialization():
    cards = [{"front": "Q1", "back": "A1"}, {"front": "Q2", "back": "A2"}]
    session = FlashcardSession(cards, "doc1", "fc123")
    session.current_idx = 1
    session.record_review(True)

    data = session.to_dict()
    restored = FlashcardSession.from_dict(data)

    assert restored.session_id == "fc123"
    assert restored.doc_id == "doc1"
    assert restored.current_idx == 1
    assert len(restored.reviews) == 1


def test_flashcard_hash_consistency():
    """Test that same card gets same hash"""
    cards = [{"front": "Test", "back": "Answer"}]
    session = FlashcardSession(cards, "doc1")
    hash1 = session._hash_card(cards[0])
    hash2 = session._hash_card(cards[0])
    assert hash1 == hash2
    assert len(hash1) == 8  # MD5[:8]


# =====================================================
# RUN TESTS
# =====================================================

if __name__ == "__main__":
    # Simple test runner
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')

    test_functions = [
        (name, obj) for name, obj in globals().items()
        if name.startswith("test_") and callable(obj)
    ]
    passed = 0
    failed = 0
    for name, func in test_functions:
        try:
            func()
            print(f"[PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    print(f"\n{passed}/{len(test_functions)} passed")
    sys.exit(0 if failed == 0 else 1)
