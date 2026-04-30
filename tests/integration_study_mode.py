#!/usr/bin/env python3
"""
Integration test for Study Mode (Quiz + Flashcard) — Week 2 validation
Tests: mode detection → quiz/flashcard generation → session handling
"""

import asyncio
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Fix Unicode on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from services.mode_detector import detect_mode
from services.ai_summarizer import _call_with_smart_routing
from services.study_engine import QuizSession, FlashcardSession
from prompts.study_prompts import GENERATE_QUIZ_PROMPT, GENERATE_FLASHCARD_PROMPT


# Sample exam text (Vietnamese math)
EXAM_TEXT = """
ĐỀ THI THPT QUỐC GIA 2025
Môn: Toán
Thời gian: 90 phút

Câu 1: Giá trị của biểu thức √(16) + |-3| là:
A. 1
B. 7
C. -1
D. -7

Câu 2: Phương trình x² - 5x + 6 = 0 có nghiệm là:
A. x₁=1, x₂=6
B. x₁=2, x₂=3
C. x₁=-2, x₂=-3
D. x₁=3, x₂=2

Câu 3: Tính lim(x→2) (x²-4)/(x-2):
A. 0
B. 2
C. 4
D. vô cùng

Câu 4: Hàm số y = sin(x) có chu kỳ:
A. π
B. 2π
C. 90°
D. 180°

Câu 5: Tích phân ∫₀¹ x dx bằng:
A. 0
B. 0.5
C. 1
D. 2
""".strip()


async def test_full_quiz_flow():
    """Test: Exam → Mode Detection → Quiz Generation → QuizSession"""
    print("=" * 70)
    print("INTEGRATION TEST: FULL QUIZ FLOW")
    print("=" * 70)
    print()

    # 1. Mode detection
    print("1. Mode detection...")
    mode_result = await detect_mode(EXAM_TEXT)
    print(f"   Mode: {mode_result['mode']} (conf: {mode_result['confidence']:.2f})")
    assert mode_result['mode'] == 'STUDY_MATERIAL', f"Expected STUDY_MATERIAL, got {mode_result['mode']}"
    print("   PASS")
    print()

    # 2. Quiz generation
    print("2. Quiz generation...")
    prompt = GENERATE_QUIZ_PROMPT.format(document_text=EXAM_TEXT)
    quiz_json = await _call_with_smart_routing(prompt, len(EXAM_TEXT), response_json=True)
    quiz_data = json.loads(quiz_json)
    questions = quiz_data.get('questions', [])
    print(f"   Generated {len(questions)} questions")
    assert len(questions) >= 5, f"Expected at least 5 questions, got {len(questions)}"
    print("   PASS")
    print()

    # 3. QuizSession lifecycle
    print("3. QuizSession lifecycle...")
    session = QuizSession(questions, "test_doc", "test_quiz_001")
    session.start()

    # Format first question
    q1_text = session.format_question()
    assert "Câu 1/" in q1_text
    assert "A." in q1_text and "B." in q1_text
    print("   Formatted question OK")

    # Process all answers
    # Generate answers for all 10 questions (cycle through sample answers)
    sample_answers = ["B", "B", "C", "B", "A"]
    answers = (sample_answers * ((len(questions) // len(sample_answers)) + 1))[:len(questions)]
    for ans in answers:
        result = session.process_answer(ans)

    assert session.current_idx == len(questions)
    assert session.answers[-1]['selected'] == answers[-1]
    print(f"   Processed {len(answers)} answers, score: {session.score}")
    print("   PASS")
    print()

    # 4. Final score
    print("4. Final score calculation...")
    final = session.get_final_score()
    assert 'correct' in final
    assert 'total' in final
    assert final['total'] == len(questions)
    assert 'percentage' in final
    assert 'grade' in final
    assert 'streak' in final
    print(f"   Score: {final['correct']}/{final['total']} ({final['percentage']:.1f}%)")
    print(f"   Grade: {final['grade']}")
    print("   PASS")
    print()

    # 5. Serialization
    print("5. Serialization/Deserialization...")
    data = session.to_dict()
    restored = QuizSession.from_dict(data)
    assert restored.quiz_id == session.quiz_id
    assert restored.score == session.score
    assert len(restored.answers) == len(session.answers)
    print("   PASS")
    print()

    print("=" * 70)
    print("QUIZ INTEGRATION: ALL TESTS PASSED")
    print("=" * 70)
    print()


async def test_full_flashcard_flow():
    """Test: Exam → Flashcard Generation → FlashcardSession"""
    print("=" * 70)
    print("INTEGRATION TEST: FLASHCARD FLOW")
    print("=" * 70)
    print()

    # 1. Flashcard generation
    print("1. Flashcard generation...")
    prompt = GENERATE_FLASHCARD_PROMPT.format(document_text=EXAM_TEXT)
    fc_json = await _call_with_smart_routing(prompt, len(EXAM_TEXT), response_json=True)
    fc_data = json.loads(fc_json)
    flashcards = fc_data.get('flashcards', [])
    print(f"   Generated {len(flashcards)} flashcards")
    assert len(flashcards) >= 10, f"Expected at least 10 flashcards, got {len(flashcards)}"
    print("   ✅ PASS")
    print()

    # 2. FlashcardSession lifecycle
    print("2. FlashcardSession lifecycle...")
    session = FlashcardSession(flashcards, "test_doc", "test_fc_001")

    # Format first card
    front = session.format_card_front()
    assert flashcards[0]['front'] in front
    print("   Formatted front OK")

    back = session.format_card_back()
    assert flashcards[0]['back'] in back
    print("   Formatted back OK")
    print("   ✅ PASS")
    print()

    # 3. Review actions (Remember/Forgot)
    print("3. Review actions (SM-2)...")
    session.current_idx = 0
    review1 = session.record_review(remembered=True)
    assert review1['next_review_in_days'] == 1

    review2 = session.record_review(remembered=True)
    assert review2['next_review_in_days'] == 3

    review3 = session.record_review(remembered=False)
    assert review3['next_review_in_days'] == 1  # Reset
    print(f"   SM-2 intervals: 1 → 3 → 1 (after forgot)")
    print("   ✅ PASS")
    print()

    # 4. Navigation
    print("4. Card navigation...")
    assert session.next_card() is True
    assert session.current_idx == 1
    assert session.next_card() is True
    assert session.current_idx == 2
    # Skip to end
    session.current_idx = len(flashcards) - 1
    assert session.next_card() is False
    print(f"   Navigation OK (total {len(flashcards)} cards)")
    print("   ✅ PASS")
    print()

    # 5. Summary
    print("5. Session summary...")
    summary = session.get_summary()
    assert summary['total_cards'] == len(flashcards)
    assert summary['reviewed'] == 3
    assert summary['remembered'] == 2
    assert summary['forgotten'] == 1
    print(f"   Summary: {summary}")
    print("   ✅ PASS")
    print()

    print("=" * 70)
    print("✅ FLASHCARD INTEGRATION: ALL TESTS PASSED")
    print("=" * 70)
    print()


async def main():
    print()
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║   STUDY MODE INTEGRATION TEST — Week 2 Validation            ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print()

    try:
        await test_full_quiz_flow()
        await test_full_flashcard_flow()

        print("╔═══════════════════════════════════════════════════════════════╗")
        print("║   🎉 ALL INTEGRATION TESTS PASSED                           ║")
        print("║                                                               ║")
        print("║   Study Mode is ready for webhook integration!               ║")
        print("╚═══════════════════════════════════════════════════════════════╝")
        return 0

    except Exception as e:
        print()
        print("❌ TEST FAILED:")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
