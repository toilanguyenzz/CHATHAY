#!/usr/bin/env python3
"""
End-to-end Quiz Generation Test (Week 2 Task 2.3)
Flow: Exam PDF text → Mode Detection → Quiz Generation → QuizSession
"""

import asyncio
import json
import sys
import os

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Fix Unicode on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from services.mode_detector import detect_mode
from services.ai_summarizer import _call_with_smart_routing
from services.study_engine import QuizSession
from prompts.study_prompts import GENERATE_QUIZ_PROMPT

# Sample exam text (from test_mode_detection.py)
DE_THI_TOAN = """
ĐỀ THI THPT QUỐC GIA 2025
Môn: Toán
Thời gian: 90 phút

Câu 1: Giá trị của biểu thức √(4) là:
A. 2
B. -2
C. ±2
D. 0

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


async def test_quiz_generation():
    """Test full pipeline: exam → quiz"""
    print("=" * 70)
    print("END-TO-END QUIZ GENERATION TEST")
    print("=" * 70)
    print()

    # Step 1: Mode detection
    print("Step 1: Detecting document mode...")
    mode_result = await detect_mode(DE_THI_TOAN)
    print(f"  Mode: {mode_result['mode']} (confidence: {mode_result['confidence']:.2f})")
    print(f"  Reason: {mode_result['reason']}")
    print()

    if mode_result["mode"] != "STUDY_MATERIAL":
        print(f"❌ ERROR: Expected STUDY_MATERIAL, got {mode_result['mode']}")
        return 1

    # Step 2: Quiz generation
    print("Step 2: Generating quiz via Gemini...")
    try:
        # Build prompt with exam text
        prompt = GENERATE_QUIZ_PROMPT.format(document_text=DE_THI_TOAN)

        # Call AI with smart routing (text → DeepSeek if available)
        quiz_json_str = await _call_with_smart_routing(
            prompt,
            text_length=len(DE_THI_TOAN),
            max_tokens=8192,
            response_json=True,
            force_gemini=False
        )
        print("  Raw Gemini output (first 500 chars):")
        print(f"  {quiz_json_str[:500]}...")
        print()
    except Exception as e:
        print(f"❌ ERROR during quiz generation: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Step 3: Parse quiz JSON
    print("Step 3: Parsing quiz structure...")
    try:
        quiz_data = json.loads(quiz_json_str)

        # Verify required fields
        if "questions" not in quiz_data:
            print("❌ Missing 'questions' array")
            return 1

        questions = quiz_data["questions"]
        quiz_title = quiz_data.get("quiz_title", "(Không có tiêu đề)")
        print(f"  Quiz title: {quiz_title}")
        print(f"  Questions count: {len(questions)}")
        print()

        # Verify question structure
        for i, q in enumerate(questions):
            required = ["question", "options", "correct", "explanation"]
            missing = [f for f in required if f not in q]
            if missing:
                print(f"❌ Question {i+1} missing fields: {missing}")
                return 1

            # Validate options count
            if len(q["options"]) != 4:
                print(f"❌ Question {i+1} should have 4 options, got {len(q['options'])}")
                return 1

            # Validate correct index
            if not (0 <= q["correct"] <= 3):
                print(f"❌ Question {i+1} correct index out of range: {q['correct']}")
                return 1

        print("  ✅ All questions have valid structure")
        print()

    except json.JSONDecodeError as e:
        print(f"❌ JSON parse error: {e}")
        print(f"Raw output:\n{quiz_json_str}")
        return 1

    # Step 4: Create QuizSession
    print("Step 4: Creating QuizSession...")
    try:
        session = QuizSession(
            questions=questions,
            doc_id="test_doc_001",
            quiz_id="test_quiz_e2e"
        )
        session.start()

        # Show first question
        formatted = session.format_question()
        print("  Sample formatted question:")
        print("  " + "\n  ".join(formatted.split("\n")[:8]))
        print()

        # Test answer processing
        print("  Testing answer processing...")
        result = session.process_answer("B")  # Intentionally wrong for variety
        print(f"    Feedback: {result['feedback_text']}")
        print(f"    Correct: {result['correct_answer']}")
        print(f"    Is last: {result['is_last']}")
        print()

        # Verify state update
        print(f"  Session state:")
        print(f"    Current idx: {session.current_idx}")
        print(f"    Score: {session.score}")
        print(f"    Streak: {session.streak}")
        print(f"    Answers recorded: {len(session.answers)}")
        print()

        # Test serialization
        session_dict = session.to_dict()
        restored = QuizSession.from_dict(session_dict)
        print(f"  ✅ Serialization/deserialization works")
        print()

    except Exception as e:
        print(f"❌ ERROR creating QuizSession: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Summary
    print("=" * 70)
    print("✅ ALL TESTS PASSED")
    print("=" * 70)
    print()
    print("Pipeline validated:")
    print("  [Exam Text] → [Mode Detection] → [Quiz Generation] → [QuizSession]")
    print()
    print("Next step: Integrate into zalo_webhook.py")

    return 0


if __name__ == "__main__":
    # Check env
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  Warning: GEMINI_API_KEY not set. Test may fail.")
        print("Set it with: set GEMINI_API_KEY=your_key_here")
        print()

    exit_code = asyncio.run(test_quiz_generation())
    sys.exit(exit_code)
