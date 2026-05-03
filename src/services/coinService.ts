import { apiClient } from "./api";

export interface CoinInfo {
  balance: number;
  today_usage: number;
  study_sessions_today: number;
  free_daily_limit: number;
  free_study_limit: number;
}

export interface CoinTransaction {
  id: string;
  amount: number;
  type: "earn" | "spend" | "bonus";
  description: string;
  timestamp: number;
}

export const coinService = {
  async getBalance(): Promise<CoinInfo> {
    return apiClient.get<CoinInfo>("/api/miniapp/coin/balance");
  },

  async getTransactions(): Promise<CoinTransaction[]> {
    return apiClient.get<CoinTransaction[]>("/api/miniapp/coin/transactions");
  },

  async earnCoins(amount: number, description: string): Promise<CoinInfo> {
    return apiClient.post<CoinInfo>("/api/miniapp/coin/earn", {
      amount,
      description,
    });
  },

  async inviteFriend(inviteCode: string): Promise<{ bonus: number; message: string }> {
    return apiClient.post("/api/miniapp/coin/invite", { invite_code: inviteCode });
  },
};
