import { apiClient } from "./api";

export interface QuizSessionData {
  session_id: string;
  doc_id: string;
  current_idx: number;
  score: number;
  total: number;
  question: QuizQuestion;
  buttons?: any[];
}

export interface QuizQuestion {
  id: number;
  question: string;
  options: string[];
  correct: number;
  explanation: string;
  difficulty: string;
}

export interface Question {
  id: number;
  question: string;
  options: { label: string; text: string; isCorrect: boolean }[];
  explanation: string;
  category: string;
}

export interface QuizResult {
  correct: number;
  total: number;
  percentage: number;
  grade: string;
  time_seconds?: number;
}

export interface FlashcardData {
  id: string;
  front: string;
  back: string;
}

export interface FlashcardSessionData {
  session_id: string;
  doc_id: string;
  current_idx: number;
  total: number;
  card: FlashcardData;
}

export const studyService = {
  // Quiz
  async startQuiz(docId: string): Promise<QuizSessionData> {
    return apiClient.post<QuizSessionData>("/api/miniapp/quiz/start", { doc_id: docId });
  },

  async getQuizQuestions(docId: string): Promise<Question[]> {
    return apiClient.get<Question[]>(`/api/miniapp/documents/${docId}/quiz`);
  },

  async answerQuiz(sessionId: string, answer: string): Promise<{
    is_correct: boolean;
    correct_answer: string;
    explanation: string;
    is_last: boolean;
    next_action: string;
    feedback_text: string;
    next_question?: QuizQuestion;
  }> {
    return apiClient.post("/api/miniapp/quiz/answer", {
      session_id: sessionId,
      answer,
    });
  },

  async getQuizResult(sessionId: string): Promise<QuizResult> {
    return apiClient.get<QuizResult>(`/api/miniapp/quiz/${sessionId}/result`);
  },

  async getQuizReview(sessionId: string): Promise<{
    total: number;
    correct: number;
    wrong: number;
    questions: Array<{
      question: string;
      options: string[];
      correct: number;
      your_answer: string;
      explanation: string;
      is_correct: boolean;
    }>;
  }> {
    return apiClient.get(`/api/miniapp/quiz/${sessionId}/review`);
  },

  // Flashcard
  async startFlashcard(docId: string): Promise<FlashcardSessionData> {
    return apiClient.post<FlashcardSessionData>("/api/miniapp/flashcard/start", { doc_id: docId });
  },

  // Flashcard - SM-2 Rating
  async reviewFlashcard(sessionId: string, rating: 'again' | 'hard' | 'good' | 'easy'): Promise<{
    next_card?: FlashcardData;
    is_done: boolean;
    summary?: any;
    next_review_in?: string; // e.g., "1 day", "3 days"
    next_review_label?: string; // e.g., "Again (1m)", "Hard (10m)", "Good (1d)", "Easy (4d)"
  }> {
    return apiClient.post("/api/miniapp/flashcard/review", {
      session_id: sessionId,
      rating, // SM-2 rating: again/hard/good/easy
    });
  },

  // Get user streak
  async getStreak(): Promise<{
    current_streak: number;
    longest_streak: number;
    streak_maintained: boolean; // true if streak maintained today
  }> {
    return apiClient.get(`/api/miniapp/streak`);
  },

  // Learning path progress
  async getProgress(docId: string): Promise<{
    summary_done: boolean;
    flashcard_done: number;
    flashcard_total: number;
    quiz_done: number;
    quiz_total: number;
    overall_percent: number;
  }> {
    return apiClient.get(`/api/miniapp/documents/${docId}/progress`);
  },

  // Generate share text for Quiz result
  generateQuizShareText(result: QuizResult, docName?: string): string {
    const emoji = result.percentage >= 80 ? "🏆" : result.percentage >= 50 ? "👍" : "💪";
    const doc = docName ? `📚 Tài liệu: ${docName}` : "";
    return `${emoji} Tôi vừa đạt ${result.correct}/${result.total} điểm Quiz!\n${doc}\n📊 Tỷ lệ: ${result.percentage}%\n🎯 Xếp loại: ${result.grade}\n\n👉 Tham gia ngay: chathay.vn`;
  },

  // Generate share text for Flashcard result
  generateFlashcardShareText(summary: { reviewed: number; remembered: number; forgotten: number }, docName?: string): string {
    const doc = docName ? `📚 Tài liệu: ${docName}` : "";
    return `🗂️ Tôi vừa ôn tập ${summary.reviewed} flashcard!\n${doc}\n✅ Đã thuộc: ${summary.remembered}\n❌ Chưa nhớ: ${summary.forgotten}\n📈 Tỷ lệ nhớ: ${Math.round((summary.remembered / summary.reviewed) * 100)}%\n\n👉 Học cùng tôi: chathay.vn`;
  },
};
