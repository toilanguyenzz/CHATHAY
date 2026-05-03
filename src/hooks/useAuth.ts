import { atom, useAtom } from "jotai";
import { useEffect, useState } from "react";

export interface AuthState {
  user_id: string | null;
  access_token: string | null;
  loading: boolean;
  error: string | null;
}

const authAtom = atom<AuthState>({
  user_id: null,
  access_token: null,
  loading: true,
  error: null,
});

export const useAuth = () => {
  const [auth, setAuth] = useAtom(authAtom);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    const initAuth = async () => {
      try {
        // Try to get from localStorage first (cached)
        const cached = localStorage.getItem("chathay_auth");
        if (cached) {
          const parsed = JSON.parse(cached);
          setAuth({
            user_id: parsed.user_id,
            access_token: parsed.access_token,
            loading: false,
            error: null,
          });
          setInitialized(true);
          return;
        }

        // Get from Zalo SDK
        const zmp = await import("zmp-sdk");
        const result = await zmp.default.getAccessToken();
        if (result?.accessToken) {
          // Exchange token for user info via backend
          const resp = await fetch(`${API_BASE}/api/miniapp/auth`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ access_token: result.accessToken }),
          });
          const data = await resp.json();
          if (data.user_id) {
            const authData = {
              user_id: data.user_id,
              access_token: result.accessToken,
              loading: false,
              error: null,
            };
            setAuth(authData);
            localStorage.setItem("chathay_auth", JSON.stringify(authData));
          }
        }
      } catch (err: any) {
        setAuth((prev) => ({ ...prev, loading: false, error: err.message }));
      } finally {
        setInitialized(true);
      }
    };

    initAuth();
  }, []);

  const logout = () => {
    localStorage.removeItem("chathay_auth");
    setAuth({ user_id: null, access_token: null, loading: false, error: null });
  };

  return { ...auth, initialized, logout };
};

// Will be set by api.ts after config load
let API_BASE = "";
export const setApiBase = (base: string) => { API_BASE = base; };
export const getApiBase = () => API_BASE;
