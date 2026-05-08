const API_BASE = import.meta.env.VITE_API_URL || "https://chathaychathay-service.onrender.com";

export interface ApiResponse<T> {
  data?: T;
  message?: string;
  error?: string;
}

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;
  private userId: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  setToken(token: string | null) {
    this.token = token;
  }

  setUserId(userId: string | null) {
    this.userId = userId;
  }

  setBaseUrl(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  getToken(): string | null {
    return this.token;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }
    if (this.userId) {
      headers["X-User-Id"] = this.userId;
    }

    const resp = await fetch(url, { ...options, headers });

    if (!resp.ok) {
      const error = await resp.json().catch(() => ({ error: `HTTP ${resp.status}` }));
      throw new Error(error.error || `Request failed: ${resp.status}`);
    }

    return resp.json();
  }

  async get<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: "GET" });
  }

  async post<T>(path: string, body?: any): Promise<T> {
    return this.request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async postForm<T>(path: string, formData: FormData): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const headers: Record<string, string> = {};
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }
    if (this.userId) {
      headers["X-User-Id"] = this.userId;
    }
    const resp = await fetch(url, {
      method: "POST",
      headers,
      body: formData,
    });
    if (!resp.ok) {
      const error = await resp.json().catch(() => ({ error: `HTTP ${resp.status}` }));
      throw new Error(error.error || `Request failed: ${resp.status}`);
    }
    return resp.json();
  }

  async put<T>(path: string, body?: any): Promise<T> {
    return this.request<T>(path, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async del<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: "DELETE" });
  }
}

export const apiClient = new ApiClient(API_BASE);
export { API_BASE };
