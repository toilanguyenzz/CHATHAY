import { describe, it, expect, vi, beforeEach } from 'vitest';
import { studyService } from '../studyService';
import { apiClient } from '../api';
import {
  mockQuizSession,
  mockQuizResult,
  mockStreak,
  mockFlashcards,
  mockQuizQuestions,
} from '../../test/mockData';

vi.mock('../api');

describe('StudyService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Quiz', () => {
    it('should start quiz session', async () => {
      (apiClient.post as any).mockResolvedValueOnce(mockQuizSession);

      const result = await studyService.startQuiz('doc_123');

      expect(apiClient.post).toHaveBeenCalledWith('/api/miniapp/quiz/start', {
        doc_id: 'doc_123',
      });
      expect(result).toEqual(mockQuizSession);
    });

    it('should get quiz questions', async () => {
      (apiClient.get as any).mockResolvedValueOnce(mockQuizQuestions);

      const result = await studyService.getQuizQuestions('doc_123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/miniapp/documents/doc_123/quiz');
      expect(result).toEqual(mockQuizQuestions);
    });

    it('should answer quiz question', async () => {
      const answerResponse = {
        is_correct: true,
        correct_answer: 'A',
        explanation: 'Explanation text',
        is_last: false,
        next_action: 'continue',
        feedback_text: 'Đúng rồi!',
        next_question: { id: 2, question: 'Q2?', options: [], correct: 0, explanation: '', difficulty: 'medium' },
      };
      (apiClient.post as any).mockResolvedValueOnce(answerResponse);

      const result = await studyService.answerQuiz('session_123', 'A');

      expect(apiClient.post).toHaveBeenCalledWith('/api/miniapp/quiz/answer', {
        session_id: 'session_123',
        answer: 'A',
      });
      expect(result).toEqual(answerResponse);
    });

    it('should get quiz result', async () => {
      (apiClient.get as any).mockResolvedValueOnce(mockQuizResult);

      const result = await studyService.getQuizResult('session_123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/miniapp/quiz/session_123/result');
      expect(result).toEqual(mockQuizResult);
    });

    it('should get quiz review', async () => {
      const reviewData = {
        total: 5,
        correct: 3,
        wrong: 2,
        questions: [
          {
            question: 'Q?',
            options: ['A', 'B'],
            correct: 0,
            your_answer: 'A',
            explanation: 'Explanation',
            is_correct: true,
          },
        ],
      };
      (apiClient.get as any).mockResolvedValueOnce(reviewData);

      const result = await studyService.getQuizReview('session_123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/miniapp/quiz/session_123/review');
      expect(result).toEqual(reviewData);
    });
  });

  describe('Flashcard', () => {
    it('should start flashcard session', async () => {
      const sessionData = {
        session_id: 'fc_session_123',
        doc_id: 'doc_123',
        current_idx: 0,
        total: 10,
        card: { id: 'fc1', front: 'Q1', back: 'A1' },
      };
      (apiClient.post as any).mockResolvedValueOnce(sessionData);

      const result = await studyService.startFlashcard('doc_123');

      expect(apiClient.post).toHaveBeenCalledWith('/api/miniapp/flashcard/start', {
        doc_id: 'doc_123',
      });
      expect(result).toEqual(sessionData);
    });

    it('should review flashcard with rating again', async () => {
      const reviewResponse = {
        next_card: { id: 'fc2', front: 'Q2', back: 'A2' },
        is_done: false,
        summary: { reviewed: 1, remembered: 0, forgotten: 1 },
        next_review_in: '1 minute',
        next_review_label: 'Again (1m)',
      };
      (apiClient.post as any).mockResolvedValueOnce(reviewResponse);

      const result = await studyService.reviewFlashcard('session_123', 'again');

      expect(apiClient.post).toHaveBeenCalledWith('/api/miniapp/flashcard/review', {
        session_id: 'session_123',
        rating: 'again',
      });
      expect(result).toEqual(reviewResponse);
    });

    it('should review flashcard with rating easy', async () => {
      const reviewResponse = {
        next_card: null,
        is_done: true,
        summary: { reviewed: 10, remembered: 9, forgotten: 1 },
        next_review_in: '4 days',
        next_review_label: 'Easy (4d)',
      };
      (apiClient.post as any).mockResolvedValueOnce(reviewResponse);

      const result = await studyService.reviewFlashcard('session_123', 'easy');

      expect(apiClient.post).toHaveBeenCalledWith('/api/miniapp/flashcard/review', {
        session_id: 'session_123',
        rating: 'easy',
      });
      expect(result.is_done).toBe(true);
    });
  });

  describe('Streak', () => {
    it('should get user streak', async () => {
      (apiClient.get as any).mockResolvedValueOnce(mockStreak);

      const result = await studyService.getStreak();

      expect(apiClient.get).toHaveBeenCalledWith('/api/miniapp/streak');
      expect(result).toEqual(mockStreak);
    });
  });

  describe('Progress', () => {
    it('should get document progress', async () => {
      const progress = {
        summary_done: true,
        flashcard_done: 5,
        flashcard_total: 10,
        quiz_done: 2,
        quiz_total: 5,
        overall_percent: 50,
      };
      (apiClient.get as any).mockResolvedValueOnce(progress);

      const result = await studyService.getProgress('doc_123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/miniapp/documents/doc_123/progress');
      expect(result).toEqual(progress);
    });
  });

  describe('Share Text Generation', () => {
    it('should generate quiz share text with high score', () => {
      const result = { correct: 9, total: 10, percentage: 90, grade: 'Xuất sắc' };
      const shareText = studyService.generateQuizShareText(result, ' Toán 10');

      expect(shareText).toContain('🏆');
      expect(shareText).toContain('9/10');
      expect(shareText).toContain('90%');
      expect(shareText).toContain('chathay.vn');
    });

    it('should generate quiz share text with low score', () => {
      const result = { correct: 3, total: 10, percentage: 30, grade: 'Cần cố gắng' };
      const shareText = studyService.generateQuizShareText(result);

      expect(shareText).toContain('💪');
      expect(shareText).toContain('3/10');
    });

    it('should generate flashcard share text', () => {
      const summary = { reviewed: 20, remembered: 18, forgotten: 2 };
      const shareText = studyService.generateFlashcardShareText(summary, 'Văn học');

      expect(shareText).toContain('🗂️');
      expect(shareText).toContain('20');
      expect(shareText).toContain('18');
      expect(shareText).toContain('90%'); // 18/20 = 90%
    });
  });
});
