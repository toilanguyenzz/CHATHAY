import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useAnimatedNumber } from '../useAnimatedNumber';

describe('useAnimatedNumber', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should start at initial value', () => {
    const { result } = renderHook(() => useAnimatedNumber(100));

    expect(result.current).toBe(100);
  });

  it('should animate from 0 to target value', async () => {
    const { result, rerender } = renderHook(
      ({ target }) => useAnimatedNumber(0, 1000, target),
      { initialProps: { target: 100 } }
    );

    expect(result.current).toBe(0);

    // Fast-forward animation
    act(() => {
      vi.advanceTimersByTime(500);
    });

    // Should be somewhere between 0 and 100
    expect(result.current).toBeGreaterThan(0);
    expect(result.current).toBeLessThan(100);

    // Complete animation
    act(() => {
      vi.advanceTimersByTime(600);
    });

    expect(result.current).toBe(100);
  });

  it('should handle duration parameter', async () => {
    const { result } = renderHook(() => useAnimatedNumber(0, 500, 100));

    act(() => {
      vi.advanceTimersByTime(250);
    });

    // Half duration, should be around 50 (depending on easing)
    expect(result.current).toBeGreaterThan(25);
    expect(result.current).toBeLessThan(75);
  });

  it('should animate when target changes', async () => {
    const { result, rerender } = renderHook(
      ({ target }) => useAnimatedNumber(0, 1000, target),
      { initialProps: { target: 50 } }
    );

    await act(async () => {
      vi.advanceTimersByTime(1100);
    });

    expect(result.current).toBe(50);

    // Change target
    rerender({ target: 100 });

    act(() => {
      vi.advanceTimersByTime(1100);
    });

    expect(result.current).toBe(100);
  });

  it('should handle zero duration (instant)', () => {
    const { result, rerender } = renderHook(
      ({ target }) => useAnimatedNumber(0, 0, target),
      { initialProps: { target: 100 } }
    );

    // With zero duration, should jump immediately
    expect(result.current).toBe(100);
  });

  it('should format with locale string when formatting enabled', () => {
    const { result } = renderHook(() =>
      useAnimatedNumber(1000, 1000, 1500, true)
    );

    act(() => {
      vi.advanceTimersByTime(1000);
    });

    // Should be formatted with commas
    expect(result.current).toBe(1500);
  });
});
