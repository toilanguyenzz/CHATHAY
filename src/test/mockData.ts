// Mock data for tests
export const mockUser = {
  user_id: 'test_user_123',
  access_token: 'mock_token_abc123',
};

export const mockDocument = {
  id: 'doc_123',
  name: 'Bai_Giang_Toan_10.pdf',
  doc_type: 'pdf',
  summary: 'Đây là tóm tắt bài giảng về Phương trình bậc hai...',
  timestamp: Date.now(),
  flashcard_count: 10,
  quiz_count: 5,
};

export const mockDocuments = [
  mockDocument,
  {
    id: 'doc_456',
    name: 'Lý thuyết Vật Lý 11.docx',
    doc_type: 'docx',
    summary: 'Tóm tắt Động lực học...',
    timestamp: Date.now() - 86400000,
    flashcard_count: 8,
    quiz_count: 4,
  },
];

export const mockFlashcard = {
  id: 'fc_1',
  front: 'Phương trình bậc 2 có dạng?',
  back: 'ax² + bx + c = 0 (a ≠ 0)',
};

export const mockFlashcards = [
  mockFlashcard,
  {
    id: 'fc_2',
    front: 'Công thức bậc 2?',
    back: 'x = (-b ± √Δ) / 2a',
  },
];

export const mockQuizQuestion = {
  id: 1,
  question: 'Phương trình x² - 5x + 6 = 0 có nghiệm là?',
  options: [
    { label: 'A', text: 'x₁=2, x₂=3', isCorrect: true },
    { label: 'B', text: 'x₁=1, x₂=6', isCorrect: false },
    { label: 'C', text: 'x₁=-2, x₂=-3', isCorrect: false },
    { label: 'D', text: 'x₁=3, x₂=-2', isCorrect: false },
  ],
  explanation: 'Áp dụng công thức bậc 2: Δ = 25-24 = 1, x = (5±1)/2',
  category: 'Toán',
  difficulty: 'medium',
};

export const mockQuizQuestions = [mockQuizQuestion];

export const mockQuizSession = {
  session_id: 'session_123',
  doc_id: 'doc_123',
  current_idx: 0,
  score: 0,
  total: 1,
  question: mockQuizQuestion,
};

export const mockQuizResult = {
  correct: 3,
  total: 5,
  percentage: 60,
  grade: 'Đạt',
};

export const mockCoinInfo = {
  balance: 150,
  today_usage: 5,
  study_sessions_today: 3,
  free_daily_limit: 10,
  free_study_limit: 20,
};

export const mockStreak = {
  current_streak: 7,
  longest_streak: 15,
  streak_maintained: true,
};

export const mockApiResponse = <T>(data: T) => ({
  data,
  message: 'Success',
});
