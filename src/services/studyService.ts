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

  // Flashcard
  async startFlashcard(docId: string): Promise<FlashcardSessionData> {
    return apiClient.post<FlashcardSessionData>("/api/miniapp/flashcard/start", { doc_id: docId });
  },

  async reviewFlashcard(sessionId: string, remembered: boolean): Promise<{
    next_card?: FlashcardData;
    is_done: boolean;
    summary?: any;
  }> {
    return apiClient.post("/api/miniapp/flashcard/review", {
      session_id: sessionId,
      remembered,
    });
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
};
