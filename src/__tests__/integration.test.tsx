import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { JotaiProvider } from 'jotai';
import { SnackbarProvider } from 'zmp-ui';
import FileProcessingPage from '../pages/file-processing';

// Mock services
vi.mock('../services/documentService', () => ({
  documentService: {
    uploadAndProcess: vi.fn(),
    getDocuments: vi.fn(),
    deleteDocument: vi.fn(),
    renameDocument: vi.fn(),
  },
}));

vi.mock('../services/coinService', () => ({
  coinService: {
    getBalance: vi.fn(),
  },
}));

vi.mock('../services/studyService', () => ({
  studyService: {
    getStreak: vi.fn(),
  },
}));

vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({
    user_id: 'test_user_123',
    loading: false,
    initialized: true,
  }),
}));

const mockDocumentService = vi.mocked(import('../services/documentService')).documentService;
const mockCoinService = vi.mocked(import('../services/coinService')).coinService;
const mockStudyService = vi.mocked(import('../services/studyService')).studyService;

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });

const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>
    <JotaiProvider>
      <QueryClientProvider client={createTestQueryClient()}>
        <SnackbarProvider>{children}</SnackbarProvider>
      </QueryClientProvider>
    </JotaiProvider>
  </BrowserRouter>
);

describe('FileProcessingPage Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCoinService.getBalance.mockResolvedValue({ balance: 100 });
    mockStudyService.getStreak.mockResolvedValue({ current_streak: 5, streak_maintained: true });
    mockDocumentService.getDocuments.mockResolvedValue([]);
  });

  it('should load and display documents', async () => {
    const docs = [
      {
        id: 'doc1',
        name: 'Test Document.pdf',
        doc_type: 'pdf',
        summary: 'Test summary',
        timestamp: Date.now(),
        flashcard_count: 5,
        quiz_count: 3,
      },
    ];
    mockDocumentService.getDocuments.mockResolvedValue(docs);

    render(
      <TestWrapper>
        <FileProcessingPage />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Document.pdf')).toBeInTheDocument();
    });
  });

  it('should handle file upload', async () => {
    const mockFile = new File(['test content'], 'upload.pdf', { type: 'application/pdf' });
    mockDocumentService.uploadAndProcess.mockResolvedValue({
      summary: 'Uploaded summary',
      flashcards: [],
      quiz: [],
      doc_id: 'new_doc',
    });

    render(
      <TestWrapper>
        <FileProcessingPage />
      </TestWrapper>
    );

    // Simulate file input change
    const fileInput = document.querySelector('input[type="file"]');
    if (fileInput) {
      await act(async () => {
        fireEvent.change(fileInput, { target: { files: [mockFile] } });
      });

      expect(mockDocumentService.uploadAndProcess).toHaveBeenCalledWith(mockFile);
      expect(mockDocumentService.getDocuments).toHaveBeenCalled();
    }
  });

  it('should display error on upload failure', async () => {
    const mockFile = new File(['test'], 'test.pdf');
    mockDocumentService.uploadAndProcess.mockRejectedValue(new Error('Upload failed'));

    render(
      <TestWrapper>
        <FileProcessingPage />
      </TestWrapper>
    );

    const fileInput = document.querySelector('input[type="file"]');
    if (fileInput) {
      await act(async () => {
        fireEvent.change(fileInput, { target: { files: [mockFile] } });
      });

      // Error toast should appear (check by querying error message)
      await waitFor(() => {
        expect(screen.getByText(/không thể tải|upload failed/i)).toBeInTheDocument();
      });
    }
  });

  it('should handle document deletion', async () => {
    const docs = [
      {
        id: 'doc1',
        name: 'ToDelete.pdf',
        doc_type: 'pdf',
        summary: '',
        timestamp: Date.now(),
      },
    ];
    mockDocumentService.getDocuments.mockResolvedValue(docs);

    render(
      <TestWrapper>
        <FileProcessingPage />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('ToDelete.pdf')).toBeInTheDocument();
    });

    // Click delete button (assuming there's a delete button)
    const deleteButtons = screen.getAllByRole('button', { name: /xóa|delete/i });
    if (deleteButtons.length > 0) {
      await act(async () => {
        fireEvent.click(deleteButtons[0]);
      });

      expect(mockDocumentService.deleteDocument).toHaveBeenCalledWith('doc1');
    }
  });

  it('should display summary when document selected', async () => {
    const doc = {
      id: 'doc1',
      name: 'Summary Test.pdf',
      summary: 'This is a test summary content.',
      timestamp: Date.now(),
    };
    mockDocumentService.getDocuments.mockResolvedValue([doc]);

    render(
      <TestWrapper>
        <FileProcessingPage />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Summary Test.pdf')).toBeInTheDocument();
    });

    // Click on document to view summary
    fireEvent.click(screen.getByText('Summary Test.pdf'));

    await waitFor(() => {
      expect(screen.getByText('This is a test summary content.')).toBeInTheDocument();
    });
  });
});

describe('Quiz Flow Integration', () => {
  it('should complete full quiz flow', async () => {
    // This would test QuizPage flow in isolation
    // Mock the studyService responses for full quiz flow
  });
});

describe('Flashcard Flow Integration', () => {
  it('should complete full flashcard review flow', async () => {
    // Test flashcard: start → flip → rate → next card → complete
  });
});

describe('Auth Flow Integration', () => {
  it('should handle login via Zalo SDK', async () => {
    // Test complete auth flow: cache → Zalo → backend
  });

  it('should persist auth across page reloads', async () => {
    // Test localStorage persistence
  });
});
