import { apiClient } from "./api";

export interface Document {
  id: string;
  name: string;
  doc_type: string;
  summary: string;
  timestamp: number;
  flashcard_count?: number;
  quiz_count?: number;
}

export interface SummaryResult {
  summary: string;
  flashcards?: Flashcard[];
  quiz?: QuizQuestion[];
  doc_id: string;
}

export interface Flashcard {
  id: string;
  front: string;
  back: string;
}

export interface QuizQuestion {
  id: number;
  question: string;
  options: string[];
  correct: number;
  explanation: string;
  difficulty: string;
}

export const documentService = {
  async uploadAndProcess(file: File): Promise<SummaryResult> {
    const formData = new FormData();
    formData.append("file", file);
    return apiClient.postForm<SummaryResult>("/api/miniapp/documents", formData);
  },

  async autoGenerate(file: File): Promise<SummaryResult> {
    const formData = new FormData();
    formData.append("file", file);
    return apiClient.postForm<SummaryResult>("/api/miniapp/auto-generate", formData);
  },

  async getDocuments(): Promise<Document[]> {
    return apiClient.get<Document[]>("/api/miniapp/documents");
  },

  async getDocument(docId: string): Promise<Document> {
    return apiClient.get<Document>(`/api/miniapp/documents/${docId}`);
  },

  async deleteDocument(docId: string): Promise<void> {
    return apiClient.del<void>(`/api/miniapp/documents/${docId}`);
  },

  async renameDocument(docId: string, newName: string): Promise<void> {
    return apiClient.post<void>(`/api/miniapp/documents/${docId}/rename`, { name: newName });
  },

  async getFlashcards(docId: string): Promise<Flashcard[]> {
    return apiClient.get<Flashcard[]>(`/api/miniapp/documents/${docId}/flashcards`);
  },

  async getQuiz(docId: string): Promise<QuizQuestion[]> {
    return apiClient.get<QuizQuestion[]>(`/api/miniapp/documents/${docId}/quiz`);
  },

  async solveProblem(file: File): Promise<{
    question: string;
    steps: string[];
    answer: string;
  }> {
    const formData = new FormData();
    formData.append("file", file);
    return apiClient.postForm<{
      question: string;
      steps: string[];
      answer: string;
    }>("/api/miniapp/solve-problem", formData);
  },

  async generateQuizFromSolution(solution: {
    question: string;
    steps: string[];
    answer: string;
  }): Promise<QuizQuestion[]> {
    return apiClient.post<QuizQuestion[]>("/api/miniapp/generate-quiz-from-solution", solution);
  },
};
