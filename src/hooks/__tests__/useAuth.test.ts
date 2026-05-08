import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useAuth } from '../useAuth';
import * as zmpSdk from 'zmp-sdk';

vi.mock('zmp-sdk', () => ({
  default: {
    getAccessToken: vi.fn(),
  },
}));

describe('useAuth', () => {
  const mockLocalStorage = (() => {
    let store: Record<string, string> = {};
    return {
      getItem: (key: string) => store[key] || null,
      setItem: (key: string, value: string) => { store[key] = value; },
      removeItem: (key: string) => { delete store[key]; },
      clear: () => { store = {}; },
    };
  })();

  beforeEach(() => {
    vi.clearAllMocks();
    mockLocalStorage.clear();
    // Mock localStorage
    Object.defineProperty(window, 'localStorage', {
      value: mockLocalStorage,
      writable: true,
    });
    // Mock fetch
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should initialize with loading state', () => {
    const { result } = renderHook(() => useAuth());

    expect(result.current.loading).toBe(true);
    expect(result.current.user_id).toBeNull();
    expect(result.current.access_token).toBeNull();
  });

  it('should load cached auth from localStorage', async () => {
    const cachedAuth = {
      user_id: 'cached_user_123',
      access_token: 'cached_token_abc',
    };
    mockLocalStorage.setItem('chathay_auth', JSON.stringify(cachedAuth));

    const { result } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.user_id).toBe(cachedAuth.user_id);
    expect(result.current.access_token).toBe(cachedAuth.access_token);
  });

  it('should authenticate via Zalo SDK when no cache', async () => {
    const zaloResponse = { accessToken: 'zalo_token_xyz' };
    (zmpSdk.default.getAccessToken as any).mockResolvedValue(zaloResponse);

    const backendResponse = { user_id: 'zalo_user_456' };
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => backendResponse,
    });

    const { result } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(zmpSdk.default.getAccessToken).toHaveBeenCalled();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/miniapp/auth'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ access_token: 'zalo_token_xyz' }),
      })
    );
    expect(result.current.user_id).toBe('zalo_user_456');
  });

  it('should fallback to dev mode when Zalo SDK fails', async () => {
    (zmpSdk.default.getAccessToken as any).mockRejectedValue(new Error('Zalo not available'));

    const { result } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.user_id).toBe('local_dev_user_001');
    expect(result.current.access_token).toBe('dev_token');
  });

  it('should save auth to localStorage after successful auth', async () => {
    const backendResponse = { user_id: 'new_user_789' };
    (zmpSdk.default.getAccessToken as any).mockResolvedValue({ accessToken: 'token_123' });
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => backendResponse,
    });

    const { result } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    const savedAuth = JSON.parse(mockLocalStorage.getItem('chathay_auth') || '{}');
    expect(savedAuth.user_id).toBe('new_user_789');
  });

  it('should logout correctly', async () => {
    // Setup: login first
    mockLocalStorage.setItem('chathay_auth', JSON.stringify({
      user_id: 'user_123',
      access_token: 'token_123',
    }));

    const { result, rerender } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Act: logout
    act(() => {
      result.current.logout();
    });

    // Verify
    expect(result.current.user_id).toBeNull();
    expect(result.current.access_token).toBeNull();
    expect(mockLocalStorage.getItem('chathay_auth')).toBeNull();
  });

  it('should handle backend auth error', async () => {
    (zmpSdk.default.getAccessToken as any).mockResolvedValue({ accessToken: 'token' });
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      json: async () => ({ error: 'Invalid token' }),
    });

    const { result } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.user_id).toBeNull();
  });

  it('should handle Zalo SDK timeout', async () => {
    // Mock Promise.race behavior: Zalo hangs, dev mode fallback
    const originalPromise = Promise;
    let resolvePromise: (value: any) => void;

    // Create a promise that never resolves
    const hangingPromise = new Promise((resolve) => {
      resolvePromise = resolve;
    });

    (zmpSdk.default.getAccessToken as any).mockReturnValue(hangingPromise);

    // Use setTimeout to trigger fallback after delay
    setTimeout(() => {
      resolvePromise({ accessToken: 'token' });
    }, 100);

    const { result } = renderHook(() => useAuth());

    // Should fallback to dev mode after timeout
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    }, { timeout: 5000 });

    // Dev mode should activate
    expect(result.current.user_id).toBe('local_dev_user_001');
  });

  it('should not re-init if already initialized', async () => {
    mockLocalStorage.setItem('chathay_auth', JSON.stringify({
      user_id: 'cached_user',
      access_token: 'token',
    }));

    const { result, rerender } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    const initialUserId = result.current.user_id;

    // Rerender should not reset state
    rerender();

    expect(result.current.user_id).toBe(initialUserId);
    expect(zmpSdk.default.getAccessToken).not.toHaveBeenCalled();
  });
});
