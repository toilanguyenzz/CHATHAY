import { describe, it, expect, vi, beforeEach } from 'vitest';
import { coinService } from '../coinService';
import { apiClient } from '../api';
import { mockCoinInfo, mockStreak } from '../../test/mockData';

vi.mock('../api');

describe('CoinService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getBalance', () => {
    it('should fetch coin balance', async () => {
      (apiClient.get as any).mockResolvedValueOnce(mockCoinInfo);

      const result = await coinService.getBalance();

      expect(apiClient.get).toHaveBeenCalledWith('/api/miniapp/coin/balance');
      expect(result).toEqual(mockCoinInfo);
    });
  });

  describe('getTransactions', () => {
    it('should fetch transaction history', async () => {
      const transactions = [
        { id: 't1', amount: 50, type: 'earn', description: 'Upload file', timestamp: Date.now() },
      ];
      (apiClient.get as any).mockResolvedValueOnce(transactions);

      const result = await coinService.getTransactions();

      expect(apiClient.get).toHaveBeenCalledWith('/api/miniapp/coin/transactions');
      expect(result).toEqual(transactions);
    });
  });

  describe('earnCoins', () => {
    it('should earn coins with description', async () => {
      (apiClient.post as any).mockResolvedValueOnce(mockCoinInfo);

      const result = await coinService.earnCoins(50, 'Upload file');

      expect(apiClient.post).toHaveBeenCalledWith('/api/miniapp/coin/earn', {
        amount: 50,
        description: 'Upload file',
      });
      expect(result).toEqual(mockCoinInfo);
    });
  });

  describe('inviteFriend', () => {
    it('should handle invite with bonus', async () => {
      const response = { bonus: 50, message: 'Invite successful' };
      (apiClient.post as any).mockResolvedValueOnce(response);

      const result = await coinService.inviteFriend('INVITE123');

      expect(apiClient.post).toHaveBeenCalledWith('/api/miniapp/coin/invite', {
        invite_code: 'INVITE123',
      });
      expect(result).toEqual(response);
    });
  });
});
