"""Study Engine — Quiz & Flashcard Session Management"""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =====================================================
# QUIZ SESSION
# =====================================================

class QuizSession:
    """
    State machine for interactive quiz on Zalo.

    Flow:
    - User selects quiz → Bot sends question 1 with A/B/C/D buttons
    - User clicks button OR replies text → Bot shows result, sends next question
    - After last question → Bot shows score + options to retry/share
    """

    def __init__(
        self,
        questions: List[Dict[str, Any]],
        doc_id: str,
        quiz_id: Optional[str] = None
    ):
        """
        Args:
            questions: List of question dicts:
                {
                    "question": "string",
                    "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
                    "correct": 0,  # index 0-3
                    "explanation": "string",
                    "difficulty": "easy|medium|hard"
                }
            doc_id: Document ID this quiz is based on
            quiz_id: Optional unique ID for this quiz instance (auto-gen if None)
        """
        self.questions = questions
        self.doc_id = doc_id
        self.quiz_id = quiz_id or f"quiz_{uuid.uuid4().hex[:8]}"

        # State
        self.current_idx = 0
        self.score = 0
        self.streak = 0
        self.answers: List[Dict[str, Any]] = []  # History of answers
        self.start_time = None
        self.end_time = None

    def start(self):
        """Mark quiz start time"""
        import time
        self.start_time = time.time()

    def current_question(self) -> Dict[str, Any]:
        """Get current question (0-indexed)"""
        if 0 <= self.current_idx < len(self.questions):
            return self.questions[self.current_idx]
        raise IndexError("No more questions")

    def format_question(self) -> str:
        """
        Format current question for Zalo message.
        Returns:
            Text with question and options (A/B/C/D)
        """
        q = self.current_question()
        total = len(self.questions)
        opts = q['options']

        # Determine if options already have letter prefixes (e.g., "A. ...")
        # Check first option: if it starts with "A." or "A. " we assume all have prefixes
        has_prefixes = opts[0].strip().upper().startswith('A.') if opts else False

        if has_prefixes:
            # Use options as-is (already formatted)
            option_lines = opts
        else:
            # Add prefixes A/B/C/D
            option_lines = [f"{chr(ord('A')+i)}. {opt}" for i, opt in enumerate(opts)]

        text = f"""❓ Câu {self.current_idx + 1}/{total}:

{q['question']}

{chr(10).join(option_lines)}

Reply A/B/C/D hoặc bấm nút bên dưới 👇"""
        return text

    def get_buttons(self) -> List[Dict[str, str]]:
        """
        Return 4 buttons for A/B/C/D answers.
        Zalo button format: {"title": "...", "type": "oa.query.show", "payload": "..."}
        """
        return [
            {"title": "A", "type": "oa.query.show", "payload": "QUIZ_ANSWER_A"},
            {"title": "B", "type": "oa.query.show", "payload": "QUIZ_ANSWER_B"},
            {"title": "C", "type": "oa.query.show", "payload": "QUIZ_ANSWER_C"},
            {"title": "D", "type": "oa.query.show", "payload": "QUIZ_ANSWER_D"},
        ]

    def get_abort_buttons(self) -> List[Dict[str, str]]:
        """Buttons for abort/exit during quiz"""
        return [
            {"title": "⏹️ Thoát", "type": "oa.query.show", "payload": "QUIZ_EXIT"},
            {"title": "📊 Xem điểm", "type": "oa.query.show", "payload": "QUIZ_SCORE"},
        ]

    def process_answer(self, user_choice: str) -> Dict[str, Any]:
        """
        Process user's answer (A/B/C/D).

        Args:
            user_choice: "A", "B", "C", or "D" (case-insensitive)

        Returns:
            {
                "is_correct": bool,
                "correct_answer": "A",
                "explanation": "string",
                "is_last": bool,
                "next_action": "next" | "finish",
                "feedback_text": "✅ Chính xác!" or "❌ Sai rồi. Đáp án đúng: B"
            }
        """
        choice_idx = ord(user_choice.upper()) - ord('A')
        if not (0 <= choice_idx < 4):
            raise ValueError(f"Invalid choice: {user_choice}")

        correct_idx = self.questions[self.current_idx]['correct']
        is_correct = (choice_idx == correct_idx)

        if is_correct:
            self.score += 1
            self.streak += 1
            feedback = "✅ Chính xác!"
        else:
            self.streak = 0
            correct_letter = chr(ord('A') + correct_idx)
            feedback = f"❌ Sai rồi. Đáp án đúng: {correct_letter}"

        # Record answer
        self.answers.append({
            "question_idx": self.current_idx,
            "selected": user_choice.upper(),
            "correct": chr(ord('A') + correct_idx),
            "is_correct": is_correct
        })

        self.current_idx += 1
        is_last = (self.current_idx >= len(self.questions))

        if is_last:
            self.end_time = time.time() if self.start_time else None

        return {
            "is_correct": is_correct,
            "correct_answer": chr(ord('A') + correct_idx),
            "explanation": self.questions[self.current_idx - 1].get("explanation", ""),
            "is_last": is_last,
            "next_action": "finish" if is_last else "next",
            "feedback_text": feedback
        }

    def get_final_score(self) -> Dict[str, Any]:
        """
        Get final score after quiz completed.

        Returns:
            {
                "correct": 8,
                "total": 10,
                "percentage": 80.0,
                "grade": "Khá! 🌟",
                "streak": 5,
                "time_seconds": 300  # optional
            }
        """
        total = len(self.questions)
        correct = self.score
        percentage = (correct / total) * 100 if total > 0 else 0

        # Grade
        if percentage >= 90:
            grade = "Xuất sắc! 🏆"
        elif percentage >= 80:
            grade = "Giỏi! 🌟"
        elif percentage >= 70:
            grade = "Khá! 👍"
        elif percentage >= 50:
            grade = "Trung bình 💪"
        else:
            grade = "Cần ôn thêm 📚"

        result = {
            "correct": correct,
            "total": total,
            "percentage": round(percentage, 1),
            "grade": grade,
            "streak": self.streak
        }

        if self.start_time and self.end_time:
            result["time_seconds"] = int(self.end_time - self.start_time)

        return result

    def to_dict(self) -> Dict[str, Any]:
        """Serialize session state for storage"""
        return {
            "quiz_id": self.quiz_id,
            "doc_id": self.doc_id,
            "questions": self.questions,
            "current_idx": self.current_idx,
            "score": self.score,
            "streak": self.streak,
            "answers": self.answers,
            "start_time": self.start_time,
            "end_time": self.end_time
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QuizSession':
        """Deserialize session state from storage"""
        session = cls(
            questions=data["questions"],
            doc_id=data["doc_id"],
            quiz_id=data["quiz_id"]
        )
        session.current_idx = data["current_idx"]
        session.score = data["score"]
        session.streak = data["streak"]
        session.answers = data["answers"]
        session.start_time = data.get("start_time")
        session.end_time = data.get("end_time")
        return session


# =====================================================
# FLASHCARD SESSION
# =====================================================

class FlashcardSession:
    """
    State machine for flashcard review (spaced repetition).

    Flow:
    - User selects flashcard set → Bot sends card 1 (front)
    - User clicks "Lật" → Bot shows back + buttons: "Nhớ rồi ✅" / "Chưa nhớ ❌"
    - User selects → Record in DB, schedule next review → Next card
    - After all cards → Summary + next review date
    """

    def __init__(
        self,
        flashcards: List[Dict[str, str]],
        doc_id: str,
        session_id: Optional[str] = None
    ):
        """
        Args:
            flashcards: List of card dicts:
                {"front": "Khái niệm", "back": "Giải thích"}
            doc_id: Document ID
            session_id: Optional unique session ID
        """
        self.flashcards = flashcards
        self.doc_id = doc_id
        self.session_id = session_id or f"fc_{uuid.uuid4().hex[:8]}"

        # State
        self.current_idx = 0
        self.reviews: List[Dict[str, Any]] = []  # Track this session's reviews

    def current_card(self) -> Dict[str, str]:
        """Get current flashcard"""
        if 0 <= self.current_idx < len(self.flashcards):
            return self.flashcards[self.current_idx]
        raise IndexError("No more cards")

    def format_card_front(self) -> str:
        """
        Format card front (question side).
        Returns message text for Zalo.
        """
        card = self.current_card()

        return f"""🗂️ Flashcard {self.current_idx + 1}/{len(self.flashcards)}

📖 **{card['front']}**

👇 Bấm [Lật] để xem đáp án"""

    def format_card_back(self) -> str:
        """
        Format card back (answer side) with review buttons.
        """
        card = self.current_card()

        return f"""📝 **Đáp án:**

{card['back']}

──────────────────

Bạn nhớ câu này chứ?"""

    def get_front_buttons(self) -> List[Dict[str, str]]:
        """Buttons when showing front (just flip)"""
        return [
            {"title": "🔄 Lật", "type": "oa.query.show", "payload": "FC_FLIP"},
            {"title": "⏭️ Bỏ qua", "type": "oa.query.show", "payload": "FC_SKIP"},
            {"title": "🔙 Thoát", "type": "oa.query.show", "payload": "FC_EXIT"},
        ]

    def get_back_buttons(self) -> List[Dict[str, str]]:
        """Buttons when showing back (remember/didn't remember)"""
        return [
            {"title": "✅ Nhớ rồi", "type": "oa.query.show", "payload": "FC_REMEMBER"},
            {"title": "❌ Chưa nhớ", "type": "oa.query.show", "payload": "FC_FORGOT"},
            {"title": "⏭️ Tiếp", "type": "oa.query.show", "payload": "FC_NEXT"},
        ]

    def record_review(self, remembered: bool) -> Dict[str, Any]:
        """
        Record user's review (remembered=True/False).
        Returns SM-2 spaced repetition parameters.
        """
        card = self.current_card()
        card_hash = self._hash_card(card)

        review = {
            "card_index": self.current_idx,
            "card_hash": card_hash,
            "front": card["front"],
            "back": card["back"],
            "remembered": remembered,
            "reviewed_at": time.time() if 'time' not in locals() else time.time()
        }
        self.reviews.append(review)

        # Calculate next review (simple version)
        next_review = self._calculate_next_review(
            review_count=len([r for r in self.reviews if r["card_hash"] == card_hash]),
            remembered=remembered
        )

        return {
            "card_hash": card_hash,
            "remembered": remembered,
            "next_review_in_days": next_review["interval_days"],
            "ease_factor": next_review["ease_factor"]
        }

    def _hash_card(self, card: Dict[str, str]) -> str:
        """Simple hash of front+back to identify card across sessions"""
        import hashlib
        content = f"{card['front']}|{card['back']}"
        return hashlib.md5(content.encode()).hexdigest()[:8]

    def _calculate_next_review(
        self,
        review_count: int,
        remembered: bool,
        ease_factor: float = 2.5,
        interval_days: int = 1
    ) -> Dict[str, Any]:
        """
        Calculate next review interval using SM-2 algorithm (simplified).

        Args:
            review_count: How many times this card has been reviewed
            remembered: Whether user remembered this card
            ease_factor: Current ease factor (2.5 is default)
            interval_days: Current interval in days

        Returns:
            {"interval_days": int, "ease_factor": float}
        """
        if not remembered:
            # Reset: start over tomorrow
            return {
                "interval_days": 1,
                "ease_factor": max(1.3, ease_factor - 0.2)
            }

        if review_count == 1:
            interval = 1  # Day 1 → Day 2
        elif review_count == 2:
            interval = 3  # Day 2 → Day 5
        elif review_count == 3:
            interval = 7  # Day 5 → Day 12
        elif review_count == 4:
            interval = 14  # Day 12 → Day 26
        elif review_count == 5:
            interval = 30  # Day 26 → Day 56
        else:
            # After 5 reviews, use ease factor
            interval = max(1, int(interval_days * ease_factor))

        # Update ease factor (increase if remembered)
        if review_count > 0:
            ease_factor = min(2.5, ease_factor + 0.1)

        return {
            "interval_days": interval,
            "ease_factor": round(ease_factor, 2)
        }

    def next_card(self) -> bool:
        """
        Advance to next card.
        Returns True if there are more cards, False if finished.
        """
        self.current_idx += 1
        return self.current_idx < len(self.flashcards)

    def get_summary(self) -> Dict[str, Any]:
        """Get session summary"""
        total = len(self.flashcards)
        reviewed = len(self.reviews)
        remembered = sum(1 for r in self.reviews if r["remembered"])

        return {
            "total_cards": total,
            "reviewed": reviewed,
            "remembered": remembered,
            "forgotten": reviewed - remembered,
            "completion_rate": (reviewed / total * 100) if total > 0 else 0
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize session state"""
        return {
            "session_id": self.session_id,
            "doc_id": self.doc_id,
            "flashcards": self.flashcards,
            "current_idx": self.current_idx,
            "reviews": self.reviews
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FlashcardSession':
        """Deserialize from storage"""
        session = cls(
            flashcards=data["flashcards"],
            doc_id=data["doc_id"],
            session_id=data["session_id"]
        )
        session.current_idx = data["current_idx"]
        session.reviews = data["reviews"]
        return session


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def generate_quiz_buttons_for_message() -> List[Dict[str, str]]:
    """Generate initial quiz buttons for summary message"""
    return [
        {"title": "🎮 Làm quiz ngay", "type": "oa.query.show", "payload": "STUDY_START_QUIZ"},
        {"title": "🗂️ Tạo flashcard", "type": "oa.query.show", "payload": "STUDY_START_FLASHCARD"},
        {"title": "📖 Xem tóm tắt", "type": "oa.query.show", "payload": "SUMMARY_DETAIL"},
        {"title": "📊 Tiến độ", "type": "oa.query.show", "payload": "STUDY_PROGRESS"},
        {"title": "🔙 Menu", "type": "oa.query.show", "payload": "MENU"},
    ]


def generate_quiz_completion_buttons() -> List[Dict[str, str]]:
    """Generate buttons after quiz completion"""
    return [
        {"title": "🔄 Làm lại", "type": "oa.query.show", "payload": "STUDY_START_QUIZ"},
        {"title": "🗂️ Xem flashcard", "type": "oa.query.show", "payload": "STUDY_START_FLASHCARD"},
        {"title": "📊 Tiến độ", "type": "oa.query.show", "payload": "STUDY_PROGRESS"},
        {"title": "📤 Chia sẻ", "type": "oa.query.show", "payload": "STUDY_SHARE_SCORE"},
    ]


def generate_flashcard_buttons_for_message() -> List[Dict[str, str]]:
    """Generate initial flashcard buttons"""
    return [
        {"title": "🗂️ Ôn tập ngay", "type": "oa.query.show", "payload": "STUDY_START_FLASHCARD"},
        {"title": "📊 Tiến độ", "type": "oa.query.show", "payload": "STUDY_PROGRESS"},
        {"title": "📖 Xem tóm tắt", "type": "oa.query.show", "payload": "SUMMARY_DETAIL"},
        {"title": "🔙 Menu", "type": "oa.query.show", "payload": "MENU"},
    ]


def time_to_readable(seconds: float) -> str:
    """Convert seconds to human readable (e.g., '5 phút 30 giây')"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    parts = []
    if mins > 0:
        parts.append(f"{mins} phút")
    if secs > 0:
        parts.append(f"{secs} giây")
    return " ".join(parts) if parts else "0 giây"
