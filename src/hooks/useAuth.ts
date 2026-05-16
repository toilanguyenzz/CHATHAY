import { atom, useAtom } from "jotai";
import { useEffect, useState } from "react";

export interface AuthState {
  user_id: string | null;
  access_token: string | null;
  display_name: string | null;
  loading: boolean;
  error: string | null;
}

const authAtom = atom<AuthState>({
  user_id: null,
  access_token: null,
  display_name: null,
  loading: true,
  error: null,
});

/** Helper: race a promise against a timeout */
function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) =>
      setTimeout(() => reject(new Error("Timeout")), ms)
    ),
  ]);
}

export const useAuth = () => {
  const [auth, setAuth] = useAtom(authAtom);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    // Prevent re-init if already done
    if (initialized) return;

    const initAuth = async () => {
      try {
        // Try to get from localStorage first (cached)
        const cached = localStorage.getItem("chathay_auth");
        if (cached) {
          const parsed = JSON.parse(cached);
          if (parsed.user_id) {
            setAuth({
              user_id: parsed.user_id,
              access_token: parsed.access_token,
              display_name: parsed.display_name || null,
              loading: false,
              error: null,
            });
            setInitialized(true);
            return;
          }
        }

        // Try Zalo SDK with 3s timeout (hangs forever outside Zalo app)
        try {
          const zmp = await import("zmp-sdk");
          const result = await withTimeout(zmp.default.getAccessToken(), 3000);
          if (result?.accessToken) {
            // Exchange token for user info via backend
            const backendUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
            const resp = await fetch(`${backendUrl}/api/miniapp/auth`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ access_token: result.accessToken }),
            });
            const data = await resp.json();
            if (data.user_id) {
              // Get display_name from Zalo or create/update user profile
              let displayName = data.display_name || data.user_id;
              try {
                // First try to get existing profile
                const profileResp = await fetch(`${backendUrl}/api/user-profile/${data.user_id}`, {
                  method: "GET",
                  headers: {
                    "X-User-Id": data.user_id,
                  },
                });
                if (profileResp.ok) {
                  const profileData = await profileResp.json();
                  if (profileData?.display_name) {
                    displayName = profileData.display_name;
                  }
                } else {
                  // Profile doesn't exist, create it with default name
                  await fetch(`${backendUrl}/api/user-profile`, {
                    method: "POST",
                    headers: {
                      "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                      user_id: data.user_id,
                      display_name: displayName,
                      role: "student",
                    }),
                  });
                }
              } catch (e) {
                console.warn("Failed to fetch user profile:", e);
              }

              const authData = {
                user_id: data.user_id,
                access_token: result.accessToken,
                display_name: displayName,
                loading: false,
                error: null,
              };
              setAuth(authData);
              localStorage.setItem("chathay_auth", JSON.stringify(authData));
              setInitialized(true);
              return;
            }
          }
        } catch (sdkErr) {
          console.warn("Zalo SDK unavailable or timed out, using local dev mode");
        }

        // Fallback: Local dev mode — create a test user so the app works in browser
        const devUser = {
          user_id: "local_dev_user_001",
          access_token: "dev_token",
          display_name: "Local Dev User",
          loading: false,
          error: null,
        };
        setAuth(devUser);
        localStorage.setItem("chathay_auth", JSON.stringify(devUser));
        console.info("🧪 Running in LOCAL DEV mode with mock user:", devUser.user_id);
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
    setAuth({ user_id: null, access_token: null, display_name: null, loading: false, error: null });
  };

  return { ...auth, initialized, logout };
};

// Will be set by api.ts after config load
let API_BASE = "";
export const setApiBase = (base: string) => { API_BASE = base; };
export const getApiBase = () => API_BASE;

