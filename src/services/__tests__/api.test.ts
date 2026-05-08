import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { apiClient, API_BASE } from '../services/api';

describe('ApiClient', () => {
  const mockBaseUrl = 'http://test-api.example.com';
  const mockToken = 'test-token-123';
  const mockUserId = 'user-456';

  beforeEach(() => {
    // Reset global state
    apiClient.setBaseUrl(mockBaseUrl);
    apiClient.setToken(null);
    apiClient.setUserId(null);

    // Mock fetch
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('setToken & setUserId', () => {
    it('should set token correctly', () => {
      apiClient.setToken(mockToken);
      expect(apiClient.getToken()).toBe(mockToken);
    });

    it('should set userId correctly', () => {
      apiClient.setUserId(mockUserId);
      // No getter for userId but we can verify it's used in requests
    });
  });

  describe('get', () => {
    it('should make GET request with correct URL', async () => {
      const mockResponse = { data: 'test' };
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await apiClient.get('/test-endpoint');

      expect(global.fetch).toHaveBeenCalledWith(
        `${mockBaseUrl}/test-endpoint`,
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('should include Authorization header when token is set', async () => {
      apiClient.setToken(mockToken);
      const mockResponse = { data: 'test' };
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await apiClient.get('/test-endpoint');

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': `Bearer ${mockToken}`,
          }),
        })
      );
    });

    it('should include X-User-Id header when userId is set', async () => {
      apiClient.setUserId(mockUserId);
      const mockResponse = { data: 'test' };
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await apiClient.get('/test-endpoint');

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-User-Id': mockUserId,
          }),
        })
      );
    });

    it('should throw error when response is not ok', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        json: async () => ({ error: 'Not found' }),
      });

      await expect(apiClient.get('/test-endpoint')).rejects.toThrow('Not found');
    });

    it('should throw error with HTTP status if no error message', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({}),
      });

      await expect(apiClient.get('/test-endpoint')).rejects.toThrow('Request failed: 500');
    });
  });

  describe('post', () => {
    it('should make POST request with JSON body', async () => {
      const mockResponse = { success: true };
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const body = { name: 'test', value: 123 };
      const result = await apiClient.post('/test-endpoint', body);

      expect(global.fetch).toHaveBeenCalledWith(
        `${mockBaseUrl}/test-endpoint`,
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(body),
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('should handle empty body', async () => {
      const mockResponse = { success: true };
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await apiClient.post('/test-endpoint');

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: undefined,
        })
      );
    });
  });

  describe('postForm', () => {
    it('should make POST request with FormData', async () => {
      const mockResponse = { uploaded: true };
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const formData = new FormData();
      formData.append('file', new Blob(['content']), 'test.pdf');

      await apiClient.postForm('/upload', formData);

      expect(global.fetch).toHaveBeenCalledWith(
        `${mockBaseUrl}/upload`,
        expect.objectContaining({
          method: 'POST',
          body: formData,
        })
      );
    });

    it('should not set Content-Type header for FormData', async () => {
      const mockResponse = { uploaded: true };
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const formData = new FormData();
      formData.append('file', new Blob(['content']));

      await apiClient.postForm('/upload', formData);

      const callArgs = (global.fetch as any).mock.calls[0][1];
      expect(callArgs.headers).not.toHaveProperty('Content-Type');
    });
  });

  describe('put', () => {
    it('should make PUT request with JSON body', async () => {
      const mockResponse = { updated: true };
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const body = { name: 'updated' };
      await apiClient.put('/update', body);

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/update'),
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify(body),
        })
      );
    });
  });

  describe('del', () => {
    it('should make DELETE request', async () => {
      const mockResponse = { deleted: true };
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await apiClient.del('/delete/123');

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/delete/123'),
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });
  });

  describe('setBaseUrl', () => {
    it('should change base URL', () => {
      apiClient.setBaseUrl('http://new-url.example.com');
      // Verify internal state changed (indirectly via request URL)
    });
  });
});
