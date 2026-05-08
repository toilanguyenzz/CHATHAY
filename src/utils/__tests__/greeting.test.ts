import { describe, it, expect } from 'vitest';
import { getGreeting } from '../greeting';

describe('getGreeting', () => {
  it('should return morning greeting before 12pm', () => {
    // Mock Date to 10 AM
    const mockDate = new Date();
    mockDate.setHours(10, 0, 0, 0);
    vi.setSystemTime(mockDate);

    const result = getGreeting();

    expect(result.period).toBe('sáng');
    expect(result.emoji).toBe('☀️');
    expect(result.text).toBe('Chào buổi sáng');
  });

  it('should return afternoon greeting between 12pm and 6pm', () => {
    const mockDate = new Date();
    mockDate.setHours(14, 0, 0, 0);
    vi.setSystemTime(mockDate);

    const result = getGreeting();

    expect(result.period).toBe('chiều');
    expect(result.emoji).toBe('🌤️');
    expect(result.text).toBe('Chào buổi chiều');
  });

  it('should return evening greeting after 6pm', () => {
    const mockDate = new Date();
    mockDate.setHours(20, 0, 0, 0);
    vi.setSystemTime(mockDate);

    const result = getGreeting();

    expect(result.period).toBe('tối');
    expect(result.emoji).toBe('🌙');
    expect(result.text).toBe('Chào buổi tối');
  });

  it('should handle boundary at exactly 12pm', () => {
    const mockDate = new Date();
    mockDate.setHours(12, 0, 0, 0);
    vi.setSystemTime(mockDate);

    const result = getGreeting();

    expect(result.period).toBe('chiều'); // 12pm is afternoon
    expect(result.text).toBe('Chào buổi chiều');
  });

  it('should handle boundary at exactly 6pm', () => {
    const mockDate = new Date();
    mockDate.setHours(18, 0, 0, 0);
    vi.setSystemTime(mockDate);

    const result = getGreeting();

    expect(result.period).toBe('tối'); // 6pm is evening
    expect(result.text).toBe('Chào buổi tối');
  });

  afterEach(() => {
    vi.useRealTime();
  });
});
