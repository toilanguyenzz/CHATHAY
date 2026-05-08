import { describe, it, expect, vi, beforeEach } from 'vitest';
import { documentService } from '../documentService';
import { apiClient } from '../api';
import { mockDocuments, mockDocument } from '../../test/mockData';

vi.mock('../api');

describe('DocumentService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('uploadAndProcess', () => {
    it('should upload file and return summary result', async () => {
      const mockFile = new File(['content'], 'test.pdf', { type: 'application/pdf' });
      const mockResponse = {
        summary: 'Tóm tắt nội dung...',
        flashcards: [{ id: '1', front: 'Q', back: 'A' }],
        quiz: [{ id: 1, question: 'Q?', options: [], correct: 0, explanation: '', difficulty: 'medium' }],
        doc_id: 'doc_123',
      };

      (apiClient.postForm as any).mockResolvedValueOnce(mockResponse);

      const result = await documentService.uploadAndProcess(mockFile);

      expect(apiClient.postForm).toHaveBeenCalledWith(
        '/api/miniapp/documents',
        expect.any(FormData)
      );
      expect(result).toEqual(mockResponse);
    });

    it('should append file to FormData', async () => {
      const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });
      (apiClient.postForm as any).mockResolvedValueOnce({});

      await documentService.uploadAndProcess(mockFile);

      const formData = (apiClient.postForm as any).mock.calls[0][1];
      expect(formData.get('file')).toBe(mockFile);
    });
  });

  describe('autoGenerate', () => {
    it('should call auto-generate endpoint', async () => {
      const mockFile = new File(['content'], 'test.pdf');
      const mockResponse = { summary: 'Auto generated summary' };
      (apiClient.postForm as any).mockResolvedValueOnce(mockResponse);

      const result = await documentService.autoGenerate(mockFile);

      expect(apiClient.postForm).toHaveBeenCalledWith(
        '/api/miniapp/auto-generate',
        expect.any(FormData)
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('getDocuments', () => {
    it('should fetch document list', async () => {
      (apiClient.get as any).mockResolvedValueOnce(mockDocuments);

      const result = await documentService.getDocuments();

      expect(apiClient.get).toHaveBeenCalledWith('/api/miniapp/documents');
      expect(result).toEqual(mockDocuments);
    });

    it('should return empty array on error', async () => {
      (apiClient.get as any).mockRejectedValueOnce(new Error('Network error'));

      const result = await documentService.getDocuments();

      expect(result).toEqual([]);
    });
  });

  describe('getDocument', () => {
    it('should fetch single document by ID', async () => {
      (apiClient.get as any).mockResolvedValueOnce(mockDocument);

      const result = await documentService.getDocument('doc_123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/miniapp/documents/doc_123');
      expect(result).toEqual(mockDocument);
    });
  });

  describe('deleteDocument', () => {
    it('should delete document by ID', async () => {
      (apiClient.del as any).mockResolvedValueOnce({});

      await documentService.deleteDocument('doc_123');

      expect(apiClient.del).toHaveBeenCalledWith('/api/miniapp/documents/doc_123');
    });
  });

  describe('renameDocument', () => {
    it('should rename document', async () => {
      (apiClient.post as any).mockResolvedValueOnce({});

      await documentService.renameDocument('doc_123', 'New Name');

      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/miniapp/documents/doc_123/rename',
        { name: 'New Name' }
      );
    });
  });

  describe('getFlashcards', () => {
    it('should fetch flashcards for document', async () => {
      const flashcards = [{ id: 'fc1', front: 'Q1', back: 'A1' }];
      (apiClient.get as any).mockResolvedValueOnce(flashcards);

      const result = await documentService.getFlashcards('doc_123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/miniapp/documents/doc_123/flashcards');
      expect(result).toEqual(flashcards);
    });
  });

  describe('getQuiz', () => {
    it('should fetch quiz questions for document', async () => {
      const questions = [{ id: 1, question: 'Q?', options: [], correct: 0, explanation: '', difficulty: 'medium' }];
      (apiClient.get as any).mockResolvedValueOnce(questions);

      const result = await documentService.getQuiz('doc_123');

      expect(apiClient.get).toHaveBeenCalledWith('/api/miniapp/documents/doc_123/quiz');
      expect(result).toEqual(questions);
    });
  });

  describe('solveProblem', () => {
    it('should solve problem from image', async () => {
      const mockFile = new File(['image'], 'problem.jpg', { type: 'image/jpeg' });
      const mockSolution = {
        question: 'Tính giá trị x',
        steps: ['B1', 'B2', 'B3'],
        answer: 'x = 5',
      };
      (apiClient.postForm as any).mockResolvedValueOnce(mockSolution);

      const result = await documentService.solveProblem(mockFile);

      expect(apiClient.postForm).toHaveBeenCalledWith(
        '/api/miniapp/solve-problem',
        expect.any(FormData)
      );
      expect(result).toEqual(mockSolution);
    });
  });

  describe('generateQuizFromSolution', () => {
    it('should generate quiz from solution', async () => {
      const solution = {
        question: 'Tính x',
        steps: ['B1'],
        answer: '5',
      };
      const quizQuestions = [{ id: 1, question: 'Q?', options: [], correct: 0, explanation: '', difficulty: 'medium' }];
      (apiClient.post as any).mockResolvedValueOnce(quizQuestions);

      const result = await documentService.generateQuizFromSolution(solution);

      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/miniapp/generate-quiz-from-solution',
        solution
      );
      expect(result).toEqual(quizQuestions);
    });
  });
});
